"""Organisation view controller(s)"""
from django.db import models, connection, transaction, IntegrityError
from django.urls import reverse_lazy
from django.shortcuts import render
from django.db.models import When, Case, Value, Subquery, OuterRef
from django.core.cache import cache
from django.utils.http import http_date
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView, CreateView, UpdateView
from django.http.response import JsonResponse, Http404
from django.core.exceptions import BadRequest, PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.contrib.auth.decorators import login_required

import logging
import datetime
import traceback

from ..models.Brand import Brand
from ..models.Organisation import Organisation, OrganisationMembership, OrganisationInvite
from ..forms.OrganisationForms import OrganisationCreateForm, OrganisationManageForm
from ..entity_utils import permission_utils, model_utils, gen_utils, constants, email_utils

logger = logging.getLogger(__name__)

''' Create Organisation '''

User = get_user_model()

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

    user_list = permission_utils.get_brand_related_users(request) \
      .exclude(
        id__in=(
          [user.id, self.object.owner_id] + 
          [member.get('user_id') for member in members] +
          [invite.get('user_id') for invite in invites]
        )
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
    
    if uid == request.user.id:
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

    if uid == request.user.id:
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
  # Specify how many items to return when computing popular entities
  MAX_POPULAR_ITEMS = 5

  template_name = 'clinicalcode/organisation/view.html'
  get_methods = ['get_metrics']
  post_methods = ['leave_organisation']

  def dispatch(self, request, *args, **kwargs):
    return super(OrganisationView, self).dispatch(request, *args, **kwargs)

  def get_context_data(self, *args, **kwargs):
    context = super(OrganisationView, self).get_context_data(*args, **kwargs)
    request = self.request

    slug = kwargs.get('slug')
    user = request.user if request.user and not request.user.is_anonymous else None

    current_brand = model_utils.try_get_brand(request)
    current_brand = current_brand if current_brand and current_brand.org_user_managed else None

    organisation = Organisation.objects.filter(slug=slug) if isinstance(slug, str) and not gen_utils.is_empty_string(slug) else None
    if organisation is None or not organisation.exists():
      raise Http404('No organisation found')

    organisation = organisation.first()

    org_data = self.__resolve_org_context(organisation, user, current_brand)

    # org_data.update({
    #   'org_stats': self.__resolve_org_metrics(organisation),
    # })

    return context | org_data

  @method_decorator(vary_on_headers(
    'Cookie', 'Accept-Encoding',
    'X-Target', 'X-Requested-With'
  ))
  def get(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.get_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)

    context = self.get_context_data(*args, **kwargs)
    return render(request, self.template_name, context)

  @method_decorator([
    login_required,
    permission_utils.redirect_readonly,
    vary_on_headers(
      'Cookie', 'Accept-Encoding',
      'X-Target', 'X-Requested-With'
    )
  ])
  def post(self, request, *args, **kwargs):
    if gen_utils.is_fetch_request(request):
      target = request.headers.get('X-Target', None)
      if target is not None and target in self.post_methods:
        target = getattr(self, target)
        return target(request, *args, **kwargs)
  
    return super().post(request, *args, **kwargs)

  def leave_organisation(self, request, *args, **kwargs):
    user = request.user if request.user and not request.user.is_anonymous else None
    if user is None:
      return gen_utils.jsonify_response(code=401)

    context = self.get_context_data(*args, **kwargs)
    if context.get('is_owner') or context.get('is_member') == False:
      return gen_utils.jsonify_response(code=403)

    slug = context.get('slug')
    membership = OrganisationMembership.objects.filter(
      organisation__slug=slug, user_id=user.id
    )
    if not membership.exists():
      return gen_utils.jsonify_response(code=404)
    membership = membership.first()

    try:
      membership.delete()
    except Exception as e:
      logger.warning(
        f'Integrity error when attempting to remove user from organisation: {slug}> with err: {e}'
      )
      return gen_utils.jsonify_response(code=500)

    return gen_utils.jsonify_response(code=200, status='true')

  def get_metrics(self, request, *args, **kwargs):
    user = request.user if request.user and not request.user.is_anonymous else None
    if user is None:
      return gen_utils.jsonify_response(code=401, message='Invalid credentials')

    context = self.get_context_data(*args, **kwargs)
    if not context.get('is_owner') and not context.get('is_member'):
      return gen_utils.jsonify_response(code=403, message='Insufficient permission')

    organisation = context.get('instance')
    if not isinstance(organisation, Organisation):
      return gen_utils.jsonify_response(code=500, message='Failed to resolve metrics')

    cachekey = 'metrics_org_%d' % (organisation.id)
    resultset = cache.get(cachekey)
    if not isinstance(resultset, dict):
      try:
        metrics = self.__resolve_org_metrics(organisation)
      except Exception as e:
        logger.error(
          '[Organisation<id: %d>::get_metrics] Failed to resolve metrics:\n\t- Caller: User<id: %d>\n\t- Trace:\n%s' % (
            organisation.id,
            user.id,
            ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
          )
        )
        return gen_utils.jsonify_response(code=500, message='Failed to resolve metrics')
      else:
        resultset = {
          'key': cachekey,
          'data': metrics,
          'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        cache.set(cachekey, resultset, 3600)

    timestamp = datetime.datetime.fromisoformat(resultset.get('timestamp'))

    response = gen_utils.jsonify_response(code=200, status=True, message=resultset)
    response['Expires'] = http_date((timestamp + datetime.timedelta(seconds=3600)).timestamp())
    response['Cache-Control'] = 'private, max-age=3600'
    response['Last-Modified'] = http_date(timestamp.timestamp())

    return response

  def __resolve_org_metrics(self, organisation):
    sql = '''
    with
      const_org_id as (values ({org_id})),
      const_max_popular as (values ({pop_limit})),
      ge_vis as (
        select
              ge.*,
              concat('%', ge.id::text, '%') as ent_query
          from public.clinicalcode_genericentity as ge
          join public.clinicalcode_organisation as org
            on ge.organisation_id = org.id
        where ge.organisation_id = (table const_org_id)::bigint
      ),
      hge_vis as (
        select hge.*
          from ge_vis as ge
          join public.clinicalcode_historicalgenericentity as hge
            using (id)
      ),
      ent_total as (
        select count(ge.*) as cnt
          from ge_vis as ge
      ),
      ent_created as (
        select count(ge.*) as cnt
          from ge_vis as ge
          where ge.created >= date_trunc('day', now()) - interval '30 day'
      ),
      ent_updated as (
        select count(hge.*) as cnt
          from hge_vis as hge
          where hge.updated >= date_trunc('day', now()) - interval '30 day'
      ),
      ent_reqs as (
        select *
          from public.easyaudit_requestevent as req
         where req.datetime >= date_trunc('day', now()) - interval '30 day'
      ),
      ent_visited as (
        select
              req.*,
              ge.id as ref_id
          from ge_vis as ge
          join ent_reqs as req
            on req.url like ge.ent_query
      ),
      ent_views as (
        select count(*) as cnt
          from ent_visited
      ),
      ent_downloads as (
        select count(req.*) as cnt
          from ge_vis as ge
          join ent_visited as req
            on req.url like '%api%' or req.url like '%export%'
      ),
      ent_viewcount as (
        select t0.ref_id, count(t0.*) as cnt
          from ent_visited as t0
         group by t0.ref_id
         order by cnt desc
      ),
      ent_topview as (
        select json_build_object(
                'id', req.ref_id,
                'view_count', req.cnt
              ) as dt
          from ent_viewcount as req
         limit (table const_max_popular)::int
      ),
      ent_popular as (
        select json_agg(req.dt) as cnt
          from ent_topview as req
      )
    select
        (select cnt from ent_total)     as total,
        (select cnt from ent_created)   as created,
        (select cnt from ent_updated)   as edited,
        (select cnt from ent_views)     as views,
        (select cnt from ent_downloads) as downloads,
        (select cnt from ent_popular)   as popular
    ''' \
      .format(
        org_id=organisation.id,
        pop_limit=self.MAX_POPULAR_ITEMS
      )

    with connection.cursor() as cursor:
      cursor.execute(sql)

      columns = [col[0] for col in cursor.description]
      return dict(zip(columns, cursor.fetchone()))

  def __resolve_org_context(self, organisation, user, current_brand):
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
       union
      select uau.id as user_id, org.id as organisation_id, 3 as role
        from public.auth_user as uau
        join public.clinicalcode_organisation as org
          on org.owner_id = uau.id
        where uau.id = {user.id if user else 'null'}
    '''
    if current_brand is not None:
      entity_brand_clause = f'and ge.brands && array[{current_brand.id}]'

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
         union
        select uau.id as user_id, org.id as organisation_id, 3 as role
          from public.auth_user as uau
          join public.clinicalcode_organisation as org
            on org.owner_id = uau.id
          where uau.id = {user.id if user else 'null'}
      '''
    
    sql = f'''
    with user_perms as (
      {user_perms_sql}
    ),
    entities as (
      select hge.id, hge.history_id, hge.name, hge.updated, 
              hge.publish_status, ge.organisation_id, ge.is_deleted,
              row_number() over (partition by hge.id order by hge.history_id desc) as rn
        from public.clinicalcode_historicalgenericentity as hge
        join public.clinicalcode_genericentity as ge
          on hge.id = ge.id
       where ge.organisation_id = {organisation.id}
        {entity_brand_clause}
    ),
    published as (
      select id, history_id, name, updated, publish_status
        from (
          select *,
                min(rn) over (partition by entities.id) as min_rn
            from entities
           where publish_status = {constants.APPROVAL_STATUS.APPROVED}
        ) as sq
       where rn = min_rn
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
         and entities.is_deleted is null or entities.is_deleted = false
      ) as sq
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
      'has_entities', (
        case
          when (select true from draft     limit 1) then true
          when (select true from published limit 1) then true
          else false
        end
      ),
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

    entities = entities if isinstance(entities, dict) else {}
    has_entities = entities.get('has_entities') if isinstance(entities.get('has_entities'), bool) else False
    can_view_metrics = has_entities and (is_owner or is_member)
    return {
      'instance': organisation,
      'is_owner': is_owner,
      'is_member': is_member,
      'is_admin': is_admin,
      'members': members,
      'published': entities.get('published'),
      'draft': entities.get('draft'),
      'moderated': entities.get('moderated'),
      'has_entities': has_entities,
      'can_view_metrics': can_view_metrics,
    }

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
