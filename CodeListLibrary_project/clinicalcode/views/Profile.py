from datetime import datetime
from django.utils.timezone import make_aware
from django.views.generic import TemplateView
from django.shortcuts import render
from django.conf import settings
from django.db.models import Subquery, OuterRef
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http.response import JsonResponse

from ..forms.ArchiveForm import ArchiveForm
from ..models.GenericEntity import GenericEntity
from ..entity_utils import permission_utils, model_utils, gen_utils

class MyProfile(TemplateView):
  template_name = 'clinicalcode/profile/index.html'

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    return super(MyProfile, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(MyProfile, self).get_context_data(*args, **kwargs)
    request = self.request

    return context | {}

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

class MyCollection(TemplateView):
  template_name = 'clinicalcode/profile/my_collection.html'
  template_fields = [
    'id', 'name', 'history_id', 'updated', 'owner_name', 
    'group_name', 'publish_status', 'is_deleted'
  ]
  
  def __annotate_fields(self, queryset):
    if not queryset:
      return list()
    
    annotated = queryset.annotate(
      group_name=Subquery(
        Group.objects.filter(id=OuterRef('group_id')).values('name')
      ),
      owner_name=Subquery(
        User.objects.filter(id=OuterRef('owner')).values('username')
      )
    )

    return list(annotated.values(*self.template_fields))

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    return super(MyCollection, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(MyCollection, self).get_context_data(*args, **kwargs)
    request = self.request

    content = self.__annotate_fields(
      permission_utils.get_editable_entities(request)
    )
    
    archived_content = self.__annotate_fields(
      permission_utils.get_editable_entities(request, only_deleted=True)
    )

    form = None
    if not settings.CLL_READ_ONLY:
      form = ArchiveForm(parent_request=request)

    return context | {
      'form': form,
      'content': content,
      'archived_content': archived_content
    }

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def post(self, request, *args, **kwargs):
    if settings.CLL_READ_ONLY:
      return JsonResponse({
        'success': False,
        'message': 'Cannot perform this action on Read Only site',
      })

    try:
      body = gen_utils.get_request_body(request)
      restoration_id = body.get('restoration_id')

      if restoration_id:
        return self.__try_restore_entity(request, restoration_id)
    except:
      pass
    
    return self.__try_archive_entity(request)

  def __try_restore_entity(self, request, entity_id):
    entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if entity is None:
      return JsonResponse({
        'success': False,
        'message': 'Phenotype ID is not valid',
      })
    
    if not permission_utils.can_user_edit_entity(request, entity_id):
      return JsonResponse({
        'success': False,
        'message': 'You do not have permission to perform this action',
      })
    
    try:
      entity.is_deleted = False
      entity.deleted = None
      entity.deleted_by = None
      entity.internal_comments = f'Restored by user: {request.user.id}'
      entity.save()
    except:
      return JsonResponse({
        'success': False,
        'message': 'Unknown error occurred, please try again',
      })
    else:
      return JsonResponse({
        'success': True,
        'message': f'Successfully restored {entity_id}',
      })

  def __try_archive_entity(self, request):
    form = ArchiveForm(request.POST or None, parent_request=request)
    if not form.is_valid():
      return JsonResponse({
        'success': False,
        'message': ''.join([f'{k}: {v}' for k, v in form.errors.items() if k != '__all__']),
      })
    
    try:
      instance = model_utils.try_get_instance(GenericEntity, id=form.cleaned_data.get('entity_id'))
      instance.is_deleted = True
      instance.internal_comments = form.cleaned_data.get('comments')
      instance.deleted = make_aware(datetime.now())
      instance.deleted_by = request.user
      instance.save()
    except:
      return JsonResponse({
        'success': False,
        'message': 'Unknown error occurred',
      })
    else:
      return JsonResponse({
        'success': True,
      })
