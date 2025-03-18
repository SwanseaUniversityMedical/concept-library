from datetime import datetime
from django.utils.timezone import make_aware
from django.views.generic import TemplateView, CreateView, UpdateView
from django.shortcuts import render
from django.conf import settings
from django.db.models import F, When, Case, Value
from django.db import transaction
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http.response import JsonResponse, Http404
from django.urls import reverse_lazy
from django.db import models

from ..models.GenericEntity import GenericEntity
from ..models.Brand import Brand
from ..models.Organisation import Organisation, OrganisationAuthority
from ..forms.OrganisationForms import OrganisationCreateForm, OrganisationManageForm
from ..entity_utils import permission_utils, model_utils, gen_utils, constants

class OrganisationCreateView(CreateView):
  model = Organisation
  template_name = 'clinicalcode/organisation/create.html'
  form_class = OrganisationCreateForm

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    return super(OrganisationCreateView, self).dispatch(request, *args, **kwargs)

  def get_form_kwargs(self):
    kwargs = super().get_form_kwargs()
    kwargs['label_suffix'] = ''
    return kwargs

  def get_context_data(self, **kwargs):
    context = super(OrganisationCreateView, self).get_context_data(**kwargs)
    return context
  
  def get_initial(self):
    self.initial.update({'owner': self.request.user})
    return self.initial
  
  def get_success_url(self):
    resolve_target = self.request.GET.get('resolve-target')
    if not gen_utils.is_empty_string(resolve_target):
      return reverse_lazy(resolve_target)
    return reverse_lazy('view_organisation', kwargs={ 'slug': self.object.slug })
  
  @transaction.atomic
  def form_valid(self, form):
    form.instance.owner = self.request.user
    obj = form.save()

    brand = self.request.BRAND_OBJECT
    if isinstance(brand, Brand):
      obj.brands.add(
        brand, 
        through_defaults={
          'can_post': False,
          'can_moderate': False
        }
      )

    return super(OrganisationCreateView, self).form_valid(form)

class OrganisationManageView(UpdateView):
  model = Organisation
  template_name = 'clinicalcode/organisation/manage.html'
  form_class = OrganisationManageForm

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    return super(OrganisationManageView, self).dispatch(request, *args, **kwargs)

  def get_form_kwargs(self):
    kwargs = super().get_form_kwargs()
    kwargs['label_suffix'] = ''
    return kwargs

  def get_object(self, queryset=None):
    if queryset is None:
      queryset = self.get_queryset()
    
    slug = self.kwargs.get('slug')
    try:
      obj = queryset.filter(slug=slug).get()
    except queryset.model.DoesNotExist:
      raise Http404('No organisation found')
    return obj

  def get_context_data(self, **kwargs):
    context = super(OrganisationManageView, self).get_context_data(**kwargs)
    
    members = self.object.members.through.objects.all() \
      .annotate(
        role_name=Case(
          *[When(role=v.value, then=Value(v.name)) for v in constants.ORGANISATION_ROLES],
          default=Value(constants.ORGANISATION_ROLES.MEMBER.name),
          output_field=models.CharField()
        )
      )

    return context | {
      'instance': self.object,
      'members': members
    }
  
  def get_success_url(self):
    resolve_target = self.request.GET.get('resolve-target')
    if not gen_utils.is_empty_string(resolve_target):
      return reverse_lazy(resolve_target)
    return reverse_lazy('view_organisation', kwargs={ 'slug': self.object.slug })
  
  @transaction.atomic
  def form_valid(self, form):
    obj = form.save()

    brand = self.request.BRAND_OBJECT
    if isinstance(brand, Brand):
      obj.brands.add(
        brand, 
        through_defaults={
          'can_post': False,
          'can_moderate': False
        }
      )

    return super(OrganisationManageView, self).form_valid(form)

class OrganisationView(TemplateView):
  template_name = 'clinicalcode/organisation/view.html'

  def dispatch(self, request, *args, **kwargs):
    return super(OrganisationView, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(OrganisationView, self).get_context_data(*args, **kwargs)
    request = self.request

    slug = kwargs.get('slug')
    if not gen_utils.is_empty_string(slug):
      organisation = Organisation.objects.filter(slug=slug)
      if organisation.exists():
        organisation = organisation.first()
        
        members = organisation.members.through.objects.all() \
          .annotate(
            role_name=Case(
              *[When(role=v.value, then=Value(v.name)) for v in constants.ORGANISATION_ROLES],
              default=Value(constants.ORGANISATION_ROLES.MEMBER.name),
              output_field=models.CharField()
            )
          )
        
        entities = GenericEntity.objects \
          .filter(organisation__id=organisation.id) \
          .all()

        return context | {
          'instance': organisation,
          'members': members,
          'entities': entities
        }

    raise Http404('No organisation found')

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)
