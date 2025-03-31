from datetime import datetime
from django.utils.timezone import make_aware
from django.views.generic import TemplateView, CreateView, UpdateView
from django.shortcuts import render, redirect
from django.conf import settings
from django.db.models import F, When, Case, Value, Subquery, OuterRef
from django.db import transaction
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http.response import JsonResponse, Http404
from django.urls import reverse_lazy
from django.db import models, connection
from django.core.exceptions import BadRequest, PermissionDenied

import logging

from ..models.GenericEntity import GenericEntity
from ..models.Brand import Brand
from ..models.Organisation import Organisation, OrganisationMembership, OrganisationAuthority, OrganisationInvite
from ..forms.OrganisationForms import OrganisationCreateForm, OrganisationManageForm
from ..entity_utils import permission_utils, model_utils, gen_utils, constants, email_utils

logger = logging.getLogger(__name__)

''' Create Organisation '''

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

''' Manage Organisation '''

class OrganisationManageView(UpdateView):
  model = Organisation
  template_name = 'clinicalcode/organisation/manage.html'
  form_class = OrganisationManageForm
  fetch_methods = [
    'change_user_role', 'delete_member', 'invite_member', 
    'cancel_invite', 'get_reloaded_data'
  ]

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    user = request.user     
    slug = kwargs.get('slug')
    
    has_access = permission_utils.has_member_org_access(
      user, 
      slug, 
      constants.ORGANISATION_ROLES.ADMIN
    )
    if not has_access:
      raise PermissionDenied

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
  
  def get_page_data(self, request):
    user = request.user
    roles = [{ 'name': x.name, 'value': x.value } for x in constants.ORGANISATION_ROLES]

    members = self.object.members.through.objects \
      .filter(organisation_id=self.object.id) \
      .exclude(user_id=user.id) \
      .annotate(
        role_name=Case(
          *[When(role=v.value, then=Value(v.name)) for v in constants.ORGANISATION_ROLES],
          default=Value(constants.ORGANISATION_ROLES.MEMBER.name),
          output_field=models.CharField()
        ),
        username=Subquery(
          User.objects.filter(
              id=OuterRef('user_id')
          )
          .values('username')
        )
      ) \
      .distinct('user_id') \
      .values('id', 'user_id', 'organisation_id', 'username', 'role', 'role_name')
    members = list(members)

    invites = OrganisationInvite.objects.filter(
      organisation_id=self.object.id,
      outcome__in=[
        constants.ORGANISATION_INVITE_STATUS.ACTIVE, 
        constants.ORGANISATION_INVITE_STATUS.SEEN
      ]
    ) \
      .annotate(
        username=Subquery(
          User.objects.filter(
              id=OuterRef('user_id')
          )
          .values('username')
        )
      ) \
      .values('id', 'user_id', 'username')
    invites = list(invites)

    user_list = User.objects.all() \
      .exclude(
        id__in=[user.id, self.object.owner_id] + [member.get('user_id') for member in members]
      ) \
      .values('id', 'username')
    user_list = list(user_list)

    return {
      'roles': roles,
      'members': members,
      'invites': {
        'users': user_list,
        'active': invites,
        'oid': self.object.id
      }
    }

  def get_context_data(self, **kwargs):
    self.object = self.get_object()

    context = super(OrganisationManageView, self).get_context_data(**kwargs)
    context.update(instance=self.object)

    return context | self.get_page_data(self.request)

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

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def get(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.fetch_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)

    return super().get(request, *args, **kwargs)

  def get_reloaded_data(self, request, *args, **kwargs):
    self.object = self.get_object()

    ctx = self.get_page_data(request)
    return JsonResponse(ctx)

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def post(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.fetch_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)
  
    return super().post(request, *args, **kwargs)

  def change_user_role(self, request, *args, **kwargs):
    body = gen_utils.get_request_body(request)
    
    uid = body.get('uid')
    oid = body.get('oid')
    rid = body.get('rid')
    if not isinstance(uid, int) or not isinstance(oid, int) or not isinstance(rid, int):
      return gen_utils.jsonify_response(code=400)

    roles = [x.value for x in constants.ORGANISATION_ROLES]
    if rid not in roles:
      return gen_utils.jsonify_response(code=400)

    membership = OrganisationMembership.objects.filter(
      user_id=uid,
      organisation_id=oid
    )
    if not membership.exists():
      return gen_utils.jsonify_response(code=400)
    membership = membership.first()

    try:
      membership.role = rid
      membership.save()
    except IntegrityError as e:
      logger.warning(
        f'Integrity error when attempting to change organisation roles: {body}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200)
  
  def delete_member(self, request, *args, **kwargs):
    body = gen_utils.get_request_body(request)
    
    uid = body.get('uid')
    oid = body.get('oid')
    if not isinstance(uid, int) or not isinstance(oid, int):
      return gen_utils.jsonify_response(code=400)

    membership = OrganisationMembership.objects.filter(
      user_id=uid,
      organisation_id=oid
    )
    if not membership.exists():
      return gen_utils.jsonify_response(code=400)
    membership = membership.first()

    try:
      membership.delete()
    except Exception as e:
      logger.warning(
        f'Integrity error when attempting to remove user from organisation: {body}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200)

  def invite_member(self, request, *args, **kwargs):
    body = gen_utils.get_request_body(request)

    uid = body.get('id')
    oid = body.get('oid')
    if not isinstance(uid, int) or not isinstance(oid, int):
      return gen_utils.jsonify_response(code=400)
    
    membership = OrganisationMembership.objects.filter(
      user_id=uid,
      organisation_id=oid
    )
    if membership.exists():
      return gen_utils.jsonify_response(code=400)
    
    current_invite = OrganisationInvite.objects.filter(
      user_id=uid,
      organisation_id=oid
    ) \
      .exclude(
        outcome__in=[
          constants.ORGANISATION_INVITE_STATUS.EXPIRED, 
          constants.ORGANISATION_INVITE_STATUS.ACCEPTED,
          constants.ORGANISATION_INVITE_STATUS.REJECTED
        ]
      )
    if current_invite.exists():
      return gen_utils.jsonify_response(code=400)
    
    try:
      invite = OrganisationInvite.objects.create(
        user_id=uid,
        organisation_id=oid
      )

      has_sent = email_utils.send_invite_email(request, invite)
      if has_sent:
        invite.sent = True
        invite.save()
    except Exception as e:
      logger.warning(
        f'Integrity error when attempting to invite user to organisation: {body}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200)

  def cancel_invite(self, request, *args, **kwargs):
    body = gen_utils.get_request_body(request)

    uid = body.get('uid')
    oid = body.get('oid')
    if not isinstance(uid, int) or not isinstance(oid, int):
      return gen_utils.jsonify_response(code=400)
    
    current_invite = OrganisationInvite.objects.filter(
      user_id=uid,
      organisation_id=oid
    ) \
      .exclude(
        outcome__in=[
          constants.ORGANISATION_INVITE_STATUS.EXPIRED, 
          constants.ORGANISATION_INVITE_STATUS.REJECTED
        ]
      )
    if current_invite.exists():
      current_invite = current_invite.first()

      try:
        current_invite.outcome = constants.ORGANISATION_INVITE_STATUS.REJECTED
        current_invite.save()
      except IntegrityError as e:
        logger.warning(
          f'Integrity error when attempting to delete organisation invite: {body}> with err: {e}'
        )
        return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200)

''' View Organisation '''

class OrganisationView(TemplateView):
  template_name = 'clinicalcode/organisation/view.html'
  fetch_methods = [
    'leave_organisation'
  ]

  def dispatch(self, request, *args, **kwargs):
    return super(OrganisationView, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(OrganisationView, self).get_context_data(*args, **kwargs)
    request = self.request

    user = request.user if request.user and not request.user.is_anonymous else None

    current_brand = model_utils.try_get_brand(request)
    current_brand = current_brand if current_brand and current_brand.org_user_managed else None
        
    slug = kwargs.get('slug')
    if not gen_utils.is_empty_string(slug):
      organisation = Organisation.objects.filter(slug=slug)
      if organisation.exists():
        organisation = organisation.first()
        
        members = organisation.members.through.objects \
          .filter(organisation_id=organisation.id) \
          .annotate(
            role_name=Case(
              *[When(role=v.value, then=Value(v.name)) for v in constants.ORGANISATION_ROLES],
              default=Value(constants.ORGANISATION_ROLES.MEMBER.name),
              output_field=models.CharField()
            )
          ) \
          .distinct('user_id')
        print(members)
        
        is_owner = False
        is_member = False
        is_admin = False
        if user:
          is_owner = organisation.owner_id == user.id
          
          membership = organisation.organisationmembership_set.filter(user_id=user.id)
          if membership.exists():
            membership = membership.first()

            is_member = True
            is_admin = membership.role >= constants.ORGANISATION_ROLES.ADMIN

        entity_brand_clause = ''
        user_perms_sql = f'''
          select memb.user_id, memb.organisation_id, memb.role
          from public.auth_user as uau
          join public.clinicalcode_organisationmembership as memb
            on uau.id = memb.user_id
          join public.clinicalcode_organisation as org
            on memb.organisation_id = org.id
          where memb.organisation_id = {organisation.id}
            and memb.user_id = {user.id if user else 'null'}
        '''
        if current_brand is not None:
          entity_brand_clause = f'and ge.brands @> array[{current_brand.id}]'

          user_perms_sql = f'''
            select memb.user_id, memb.organisation_id, memb.role
            from public.auth_user as uau
            join public.clinicalcode_organisationmembership as memb
              on uau.id = memb.user_id
            join public.clinicalcode_organisation as org
              on memb.organisation_id = org.id
            join public.clinicalcode_organisationauthority as auth
              on auth.organisation_id = org.id
            where memb.organisation_id = {organisation.id}
              and memb.user_id = {user.id if user else 'null'}
              and auth.brand_id = {current_brand.id}
          '''
        
        sql = f'''
        with user_perms as (
          {user_perms_sql}
        ),
        entities as (
          select hge.id, hge.history_id, hge.name, hge.updated, 
                 hge.publish_status, ge.organisation_id,
                 row_number() over (partition by hge.id order by hge.history_id desc) as rn
          from public.clinicalcode_historicalgenericentity as hge
          join public.clinicalcode_genericentity as ge
            on hge.id = ge.id
          where ge.organisation_id = {organisation.id}
            {entity_brand_clause}
        ),
        published as (
          select id, history_id, name, updated, publish_status
          from entities
          where publish_status = {constants.APPROVAL_STATUS.APPROVED}
            and rn = 1
        ),
        draft as (
          select id, history_id, name, updated, publish_status
          from (
              select entities.*,
                     min(entities.rn) over (partition by entities.id) as min_rn
              from entities
            join user_perms
              on entities.organisation_id = user_perms.organisation_id
            left join published
              on entities.id = published.id
             and published.history_id > entities.history_id
            where entities.publish_status != {constants.APPROVAL_STATUS.APPROVED}
              and published.id is null
          )
          where rn = min_rn
        ),
        moderated as (
          select entities.id, entities.history_id, entities.name, 
              entities.updated, entities.publish_status
          from entities
          join user_perms
            on entities.organisation_id = user_perms.organisation_id
          where user_perms.role >= 2
            and entities.publish_status in (
              {constants.APPROVAL_STATUS.REQUESTED}, {constants.APPROVAL_STATUS.PENDING}
            )
        )
        select json_build_object(
          'published', (
            select json_agg(json_build_object(
              'id', id, 
              'history_id', history_id, 
              'name', name, 
              'updated', updated, 
              'publish_status', publish_status
            )) from published
          ),
          'draft', (
            select json_agg(json_build_object(
              'id', id, 
              'history_id', history_id, 
              'name', name, 
              'updated', updated, 
              'publish_status', publish_status
            )) from draft
          ),
          'moderated', (
            select json_agg(json_build_object(
              'id', id, 
              'history_id', history_id, 
              'name', name, 
              'updated', updated, 
              'publish_status', publish_status
            )) from moderated
          )
        ) as "data"
        '''
        entities = None
        with connection.cursor() as cursor:
          cursor.execute(sql)

          columns = [col[0] for col in cursor.description]
          entities = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
          entities = entities.get('data')

        return context | {
          'instance': organisation,
          'is_owner': is_owner,
          'is_member': is_member,
          'is_admin': is_admin,
          'members': members,
          'published': entities.get('published'),
          'draft': entities.get('draft'),
          'moderated': entities.get('moderated')
        }

    raise Http404('No organisation found')

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def post(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.fetch_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)
  
    return super().post(request, *args, **kwargs)

  def leave_organisation(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    user = request.user if request.user and not request.user.is_anonymous else None

    if context.get('is_owner') or context.get('is_member') == False:
      return gen_utils.jsonify_response(code=400)

    membership = OrganisationMembership.objects.filter(
      organisation__slug=context.get('slug'), user_id=user.id
    )
    if not membership.exists():
      return gen_utils.jsonify_response(code=404)
    membership = membership.first()

    try:
      membership.delete()
    except Exception as e:
      logger.warning(
        f'Integrity error when attempting to remove user from organisation: {body}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200, status='true')

''' View Invite '''

class OrganisationInviteView(TemplateView):
  template_name = 'clinicalcode/organisation/invite.html'
  fetch_methods = [
    'invitation_reponse'
  ]

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def dispatch(self, request, *args, **kwargs):
    uuid = kwargs.get('uuid')
    if gen_utils.is_empty_string(uuid):
      return BadRequest
    
    invite = OrganisationInvite.objects.all() \
      .filter(
        id=uuid
      )
    if not invite.exists():
      return BadRequest
    invite = invite.first()

    user = request.user
    if not user:
      return BadRequest
    
    if invite.user_id != user.id:
      return BadRequest

    if invite.is_expired():
      return BadRequest

    if invite.outcome not in [constants.ORGANISATION_INVITE_STATUS.ACTIVE, constants.ORGANISATION_INVITE_STATUS.SEEN]:
      return BadRequest

    return super(OrganisationInviteView, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(OrganisationInviteView, self).get_context_data(*args, **kwargs)
    request = self.request

    uuid = kwargs.get('uuid')
    if not gen_utils.is_empty_string(uuid):
      invite = OrganisationInvite.objects.all() \
        .filter(
          id=uuid
        )
      if invite.exists():
        invite = invite.first()

        return context | { 
          'instance': invite.organisation,
          'invite': invite
        }
    
    raise Http404('No organisation invite found')

  def get(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

  @method_decorator([login_required, permission_utils.redirect_readonly])
  def post(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.fetch_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)
  
    return super().post(request, *args, **kwargs)
  
  def invitation_reponse(self, request, *args, **kwargs):
    context = self.get_context_data(*args, **kwargs)
    user = request.user if request.user and not request.user.is_anonymous else None
    body = gen_utils.get_request_body(request)

    invitation_response = body.get('result')
    if invitation_response is None:
      return gen_utils.jsonify_response(code=400)

    invite = context.get('invite')
    if not invite or not isinstance(invite, OrganisationInvite):
      return gen_utils.jsonify_response(code=500)

    if user.id != invite.user_id:
      return gen_utils.jsonify_response(code=400)

    current_membership = OrganisationMembership.objects.filter(
      organisation_id=invite.organisation_id,
      user_id=invite.user_id
    )
    if current_membership.exists():
      return gen_utils.jsonify_response(code=400)

    try:
      if invitation_response:
        membership = OrganisationMembership.objects.create(
          user_id=invite.user_id,
          organisation_id=invite.organisation_id
        )

        invite.outcome = constants.ORGANISATION_INVITE_STATUS.ACCEPTED
        invite.save()
      else:
        invite.outcome = constants.ORGANISATION_INVITE_STATUS.REJECTED
        invite.save()
    except Exception as e:
      logger.warning(
        f'Integrity error when attempting to remove user from organisation: {body}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=400)

    return gen_utils.jsonify_response(code=200, status='true')