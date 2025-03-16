from django.db import connection
from django.conf import settings
from django.db.models import Q, Subquery, OuterRef, Model
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Group

from functools import wraps

from . import model_utils, gen_utils
from ..models.Brand import Brand
from ..models.Concept import Concept
from ..models.Template import Template
from ..models.Organisation import Organisation
from ..models.GenericEntity import GenericEntity
from ..models.PublishedConcept import PublishedConcept
from ..models.PublishedGenericEntity import PublishedGenericEntity
from . import model_utils
from .constants import ORGANISATION_ROLES, APPROVAL_STATUS, GROUP_PERMISSIONS, WORLD_ACCESS_PERMISSIONS

""" Permission decorators """

def redirect_readonly(fn):
    """
      Method decorator to raise 403 if we're on the read only site
      to avoid insert / update methods via UI

      e.g. 

      @permission_utils.redirect_readonly
      def some_view_func(request):
        # stuff
    """
    @wraps(fn)
    def wrap(request, *args, **kwargs):
        if settings.CLL_READ_ONLY:
            raise PermissionDenied("ERR_403_GATEWAY")
        return fn(request, *args, **kwargs)

    return wrap


""" Render helpers """

def should_render_template(template=None, **kwargs):
    """
        Method to det. whether a template should be renderable
        based on its `hide_on_create` property

        Args:
            template {model}: optional parameter to check a model instance directly

            **kwargs (any): params to use when querying the template model
        
        Returns:
            A boolean reflecting the renderable status of a template model

    """
    if template is None:
        if len(kwargs.keys()) < 1:
            return False

        template = Template.objects.filter(**kwargs)
    
        if template.exists():
            template = template.first()

    if not isinstance(template, Template) or not hasattr(template, 'hide_on_create'):
        return False

    return not template.hide_on_create


""" Status helpers """  

def is_member(user, group_name):
    """
      Checks if a User instance is a member of a group
    """
    return user.groups.filter(name__iexact=group_name).exists()

def has_member_access(user, entity, min_permission):
    """
      Checks if a user has access to an entity via its organisation
        membership. Min_permissions relates to the organisation role, e.g.
        min_permission=1 means the user has to be an editor or above.
    """
    org = entity.organisation
    if org:
        if org.owner == user:
            return True

        membership = user.organisationmembership_set \
            .filter(organisation__id=org.id)
        if membership.exists():
            return membership.first().role >= min_permission

    return False

def is_publish_status(entity, status):
    """
      Checks the publication status of an entity
    """
    history_id = getattr(entity, 'history_id', None)
    if history_id is None:
        history_id = entity.history.latest().history_id

    approval_status = model_utils.get_entity_approval_status(
        entity.id, history_id
    )

    if approval_status:
        return approval_status in status
    return False

""" General permissions """

def was_archived(entity_id):
    """
      Checks whether an entity was ever archived:
        - Archive status is derived from the top-most entity, i.e. the latest version
        - We assume that the instance was deleted in cases where the instance does
          not exist within the database
      
      Args:
        entity_id (integer): The ID of the entity

      Returns:
        A (boolean) that describes the archived state of an entity
    """
    entity = model_utils.try_get_instance(GenericEntity, id=entity_id)
    if entity is None:
        return True

    return True if entity.is_deleted else False

def get_user_groups(request):
    """
      Get the groups related to the requesting user
    """
    user = request.user
    if not user or user.is_anonymous:
        return []

    if user.is_superuser:
        return list(Group.objects.all().exclude(name='ReadOnlyUsers').values('id', 'name'))

    return list(user.groups.all().exclude(name='ReadOnlyUsers').values('id', 'name'))

def get_editable_user_organisations(request):
    """
      Get the organisations related to the requesting user
    """
    user = request.user
    if not user or user.is_anonymous:
        return []

    if user.is_superuser:
        return list(Organisation.objects.all().values('id', 'name'))
    
    sql = '''
    select org.id, org.slug, org.name
      from public.clinicalcode_organisation org
      join public.clinicalcode_organisationmembership mem
        on org.id = mem.organisation_id
     where mem.user_id = %(user_id)s
       and mem.role >= %(role_enum)s
    ''' # [!] TODO: BrandAuthority

    with connection.cursor() as cursor:
      cursor.execute(sql, params={
        'user_id': user.id,
        'role_enum': ORGANISATION_ROLES.EDITOR
      })

      columns = [col[0] for col in cursor.description]
      results = [dict(zip(columns, row)) for row in cursor.fetchall()]
      return results

def get_moderation_entities(
    request,
    status=None
):
    """
      Returns entities with moderation status of specified status

      Args:
        request (RequestContext): HTTP context
        status (List): List of integers representing status

      Returns:
        List of all entities with specified moderation status
    """
    entities = GenericEntity.history.all() \
        .order_by('id', '-history_id') \
        .distinct('id')

    return entities.filter(Q(publish_status__in=status))

def get_editable_entities(
    request,
    only_deleted=False,
    consider_brand=True
):
    """
      Tries to get all the entities that are editable by a specific user

      Args:
        request (RequestContext): HTTP context
        only_deleted (boolean): Whether to only show deleted phenotypes or not 

      Returns:
        List of all editable entities
    """
    user = request.user
    if not user or user.is_anonymous:
        return None

    brand = model_utils.try_get_brand(request) if consider_brand else None
    if brand:
        brand_sql = 'and %(brand)s = any(live.brands)'
    else:
        brand_sql = ''
    
    if only_deleted:
        delete_sql = 'and live.is_deleted = true'
    else:
        delete_sql = 'and (live.is_deleted is null or live.is_deleted = false)'

    sql = '''
        with entity as (
            select distinct on (id) *
            from public.clinicalcode_historicalgenericentity entity
            order by id, history_id desc
        )
        select entity.*, 
               live.is_deleted as was_deleted,
               organisation.name as group_name,
               uac.username as owner_name
        from entity
        join public.clinicalcode_genericentity live
          on live.id = entity.id
        join public.auth_user uac
          on uac.id = entity.owner_id
        left join public.clinicalcode_organisation organisation
          on organisation.id = live.organisation_id
        left join public.clinicalcode_organisationmembership membership
          on membership.organisation_id = organisation.id
        where (live.owner_id = %(user_id)s
           or organisation.owner_id = %(user_id)s
           or (membership.user_id = %(user_id)s AND membership.role >= %(role_enum)s))
          {brand}
          {delete}
    '''.format(
        brand=brand_sql,
        delete=delete_sql
    )
    
    with connection.cursor() as cursor:
        cursor.execute(
            sql, 
            params={
                'user_id': user.id,
                'role_enum': ORGANISATION_ROLES.EDITOR,
                'brand': brand
            }
        )
        
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results

def get_accessible_entity_history(
    request,
    entity_id,
    entity_history_id,
):
    """
      Attempts to get the accessible history of an entity

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (string): some entity to resolve
        entity_history_id (integer): the entity's history id

      Returns:
        A dict containing historical entity data
    """
    if not isinstance(entity_id, str) or not isinstance(entity_history_id, int) or isinstance(model_utils.get_entity_id(entity_id), bool):
        return None
    
    user = request.user
    is_superuser = user.is_superuser if user is not None else False
    query_params = { 'pk': entity_id, 'hid': entity_history_id }

    brand_clause = ''
    brand = model_utils.try_get_brand(request)
    if brand is not None:
        brand_clause = 'and live.brands && %(brand_ids)s'
        query_params.update({ 'brand_ids': [brand.id] })

    data = f'''
        with
          pub_data as (
        	select
        	    case
        	      when t0.is_last_approved = 1 then true
        	      else false
        	    end as is_last_approved,
        	    case
        	      when t0.is_latest_pending_version = 1 then true
        	      else false
        	    end as is_latest_pending_version,
				t0.published_ids,
        	    t0.objects
			  from (
            	select
                    t0.entity_id,
                    max(
                      case
                        when t0.approval_status = {APPROVAL_STATUS.APPROVED.value} then 1
                        else 0
                      end
                    ) as is_last_approved,
                    max(
                      case
                        when t0.entity_history_id = %(hid)s and t0.approval_status = {APPROVAL_STATUS.PENDING.value} then 1
                        else 0
                      end
                    ) as is_latest_pending_version,
                    array_agg(case when t0.approval_status = {APPROVAL_STATUS.APPROVED.value} then t0.entity_history_id end) as published_ids,
					json_agg(
					  json_build_object(
                        'status', t0.approval_status,
                        'entity_history_id', t0.entity_history_id,
                        'publish_date', t0.modified,
                        'approval_status_label', (
                          case
                            when t0.approval_status = {APPROVAL_STATUS.REQUESTED.value} then 'REQUESTED'
                            when t0.approval_status = {APPROVAL_STATUS.PENDING.value} then 'PENDING'
                            when t0.approval_status = {APPROVAL_STATUS.APPROVED.value} then 'APPROVED'
                            when t0.approval_status = {APPROVAL_STATUS.REJECTED.value} then 'REJECTED'
                            else ''
                          end
						)
					  )
					) as objects
                  from public.clinicalcode_publishedgenericentity as t0
                 where t0.entity_id = %(pk)s
                 group by t0.entity_id
			  ) as t0
          ),
          ent_data as (
            select *
              from (
                select t.id, max(t.history_id) as history_id
                  from public.clinicalcode_historicalgenericentity as t
                 group by t.id
              ) as t0
             where t0.id = %(pk)s
          )'''

    # Anon user query
    #   i.e. only published phenotypes
    if not user or user.is_anonymous:
        sql = f'''
          {data},
          historical_entities as (
            select
		        pd.obj->>'approval_status_label'::text as approval_status_label,
			    to_char(cast(pd.obj->>'publish_date' as timestamptz), 'YYYY-MM-DD HH24:MI') as publish_date,
			    t0.id,
                to_char(t0.history_date, 'YYYY-MM-DD HH24:MI') as history_date,
				t0.history_id,
				t0.name,
				uau.username as updated_by,
				cau.username as created_by,
				oau.username as owner
              from public.clinicalcode_historicalgenericentity as t0
			  join pub_data as pub
				on t0.history_id = any(pub.published_ids)
              join public.clinicalcode_genericentity as live
                on live.id = t0.id
			  left join public.auth_user as uau
			    on t0.updated_by_id = uau.id
			  left join public.auth_user as cau
			    on t0.created_by_id = cau.id
			  left join public.auth_user as oau
			    on t0.owner_id = oau.id
		      left join (select json_array_elements(objects::json) as obj from pub_data pd) as pd
			    on t0.history_id = (pd.obj->>'entity_history_id')::int
			 where t0.id = %(pk)s
               {brand_clause}
          )
          select t0.history_id as latest_history_id, t1.*, t2.*
            from ent_data as t0
		    left join pub_data as t1
              on true
			left join (
			  select json_agg(row_to_json(t.*) order by t.history_id desc) as entities
			  from (
				select *, row_number() over(partition by id, history_id) as rn
				from historical_entities
			  ) as t
			  where rn = 1
			) as t2
			  on true
        '''

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchone()
            return dict(zip(columns, results)) if results else None

    # Non-anon user
    #   i.e. dependent on user role
    clauses = 'true'
    if not is_superuser:
        clauses = '''
           (live.owner_id = %(user_id)s
           or org.owner_id = %(user_id)s
           or (mem.user_id = %(user_id)s AND mem.role >= %(role_enum)s))
        '''

        query_params.update({
            'user_id': user.id,
            'role_enum': ORGANISATION_ROLES.MEMBER
        })

        pub_status = [APPROVAL_STATUS.APPROVED.value]
        if is_member(user, 'Moderators'):
            pub_status += [
                APPROVAL_STATUS.REQUESTED.value,
                APPROVAL_STATUS.PENDING.value,
                APPROVAL_STATUS.REJECTED.value
            ]

        if len(pub_status) > 1:
            clauses += f'''
            or t0.publish_status = any(%(pub_status)s)
            '''
            query_params.update({ 'pub_status': pub_status })
        else:
            clauses += f'''
            or t0.publish_status = {APPROVAL_STATUS.APPROVED.value}
            '''

    sql = f'''
      {data},
      historical_entities as (
        select
		    coalesce(pd.obj->>'approval_status_label'::text, '') as approval_status_label,
            to_char(cast(pd.obj->>'publish_date' as timestamptz), 'YYYY-MM-DD HH24:MI') as publish_date,
		    t0.id,
            to_char(t0.history_date, 'YYYY-MM-DD HH24:MI') as history_date,
			t0.history_id,
			t0.name,
			uau.username as updated_by,
			cau.username as created_by,
			oau.username as owner
          from public.clinicalcode_historicalgenericentity as t0
		  left join public.auth_user as uau
			on t0.updated_by_id = uau.id
		  left join public.auth_user as cau
			on t0.created_by_id = cau.id
		  left join public.auth_user as oau
		    on t0.owner_id = oau.id
		  left join (select json_array_elements(objects::json) as obj from pub_data pd) as pd
		    on t0.history_id = (pd.obj->>'entity_history_id')::int
          join public.clinicalcode_genericentity live
            on live.id = t0.id
          left join public.clinicalcode_organisation org
            on org.id = live.organisation_id
          left join public.clinicalcode_organisationmembership mem
            on mem.organisation_id = org.id
		 where t0.id = %(pk)s
           and ({clauses})
           {brand_clause}
      )
      select t0.history_id as latest_history_id, t1.*, t2.*
        from ent_data as t0
	    left join pub_data as t1
          on true
		left join (
		  select json_agg(row_to_json(t.*) order by t.history_id desc) as entities
		    from (
				select *, row_number() over(partition by id, history_id) as rn
				from historical_entities
			) as t
		  where rn = 1
		) as t2
		  on true
    '''

    with connection.cursor() as cursor:
        cursor.execute(sql, query_params)
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchone()
        print(dict(zip(columns, results)) if results else None)
        return dict(zip(columns, results)) if results else None

def get_accessible_entities(
    request,
    consider_user_perms=True,
    only_deleted=False,
    status=[APPROVAL_STATUS.APPROVED],
    min_group_permission=ORGANISATION_ROLES.MEMBER,
    consider_brand=True,
    raw_query=False,
    pk=None
):
    """
      Tries to get all the entities that are accessible to a specific user

      Args:
        request (RequestContext): the HTTPRequest
        consider_user_perms (boolean): Whether to consider user perms i.e. superuser, moderation status etc
        only_deleted (boolean): Whether to incl/excl deleted entities
        status (list): A list of publication statuses to consider
        group_permissions (list): A list of which group permissions to consider
        consider_brand (boolean): Whether to consider the request Brand (only applies to Moderators, Non-Auth'd and Auth'd accounts)
        raw_query (boolean): Specifies whether this func should return a RawQuerySet (defaults to `False`)
        pk (string): optionally specify some pk to filter

      Returns:
        (Raw)QuerySet of accessible entities
    """
    user = request.user
    query_params = { }

    # Build brand query
    brand = model_utils.try_get_brand(request) if consider_brand else None
    brand_clause = ''
    if consider_brand and brand is not None:
        brand_clause = 'and live_entity.brands && %(brand_ids)s'
        query_params.update({ 'brand_ids': [brand.id] })

    # Append pk clause if entity_id is valid
    pk_clause = ''
    if isinstance(pk, str) and not isinstance(model_utils.get_entity_id(pk), bool):
        pk_clause = 'and hist_entity.id = %(pk)s'
        query_params.update({ 'pk': pk })

    # Early exit if we're a superuser and want to consider privileges
    if len(pk_clause) < 1 and consider_user_perms and user and user.is_superuser:
        if brand is not None:
            results = GenericEntity.objects.filter(brands__overlap=[brand.id])
            results = GenericEntity.history \
                .filter(id__in=list(results.values_list('id', flat=True)))
        else:
            results = GenericEntity.history.all()
        return results.latest_of_each()

    # Anon user query
    #   i.e. only published phenotypes
    if not user or user.is_anonymous:
        # Note: removed `template__hide_on_create` recently as it might interfere
        #       with previously published templates
        sql = f'''
        select t0.id, t0.history_id
          from (
            select
                  hist_entity.id,
                  hist_entity.history_id,
                  row_number() over (
                    partition by hist_entity.id
                    order by hist_entity.history_id desc
                  ) as rn_ref_n
              from public.clinicalcode_historicalgenericentity as hist_entity
              join public.clinicalcode_genericentity as live_entity
                on hist_entity.id = live_entity.id
              join public.clinicalcode_historicaltemplate as hist_tmpl
                on hist_entity.template_id = hist_tmpl.id and hist_entity.template_version = hist_tmpl.template_version
              join public.clinicalcode_template as live_tmpl
                on hist_tmpl.id = live_tmpl.id
             where (live_entity.is_deleted is null or live_entity.is_deleted = false)
               and (hist_entity.is_deleted is null or hist_entity.is_deleted = false)
               and hist_entity.publish_status = {APPROVAL_STATUS.APPROVED.value}
               {brand_clause}
               {pk_clause}
          ) as t0
          join public.clinicalcode_historicalgenericentity as t1
            on t0.id = t1.id
           and t0.history_id = t1.history_id
         where t0.rn_ref_n = 1;
        '''

        if raw_query:
            return GenericEntity.history.raw(sql, params=query_params)

        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            return GenericEntity.history.filter(history_id__in=[row[1] for row in cursor.fetchall()])

    # Clean publication status
    pub_status = status.copy() if isinstance(status, list) else []
    if consider_user_perms and is_member(user, 'Moderators'):
        pub_status += [
            APPROVAL_STATUS.REQUESTED,
            APPROVAL_STATUS.PENDING, 
            APPROVAL_STATUS.REJECTED
        ]

    if len(pub_status) > 0:
        pub_status = [
            x.value if x in APPROVAL_STATUS else gen_utils.parse_int(x, default=None)
            for x in pub_status
                if x in APPROVAL_STATUS or gen_utils.parse_int(x, default=None) is not None
        ]

    # Non-anon user
    #   i.e. dependent on user role
    clauses = '''
        (live_entity.owner_id = %(user_id)s
        or org.owner_id = %(user_id)s
        or (mem.user_id = %(user_id)s AND mem.role >= %(role_enum)s))
    '''

    query_params.update({
        'user_id': user.id,
        'role_enum': min_group_permission
    })

    if len(pub_status) < 1:
        clauses += f'''
          or hist_entity.publish_status != {APPROVAL_STATUS.PENDING.value}
        '''
    elif APPROVAL_STATUS.ANY in pub_status or APPROVAL_STATUS.ANY.value in pub_status:
        clauses += f'''
          or hist_entity.publish_status = {APPROVAL_STATUS.APPROVED.value}
        '''
    else:
        clauses += '''
          or hist_entity.publish_status = any(%(pub_status)s)
        '''
        query_params.update({ 'pub_status': pub_status })

    conditional = ''
    if only_deleted:
        conditional = '''
             and live_entity.id is not null and live_entity.is_deleted = true
        '''
    else:
        conditional = '''
             and (live_entity.id is not null and (live_entity.is_deleted is null or live_entity.is_deleted = false))
             and (hist_entity.is_deleted is null or hist_entity.is_deleted = false)
        '''

    sql = f'''
    select t0.id, t0.history_id
      from (
          select
              hist_entity.id,
              hist_entity.history_id,
              row_number() over (
                partition by hist_entity.id
                order by hist_entity.history_id desc
              ) as rn_ref_n
            from public.clinicalcode_historicalgenericentity as hist_entity
            join public.clinicalcode_genericentity as live_entity
              on hist_entity.id = live_entity.id
            join public.clinicalcode_historicaltemplate as hist_tmpl
              on hist_entity.template_id = hist_tmpl.id and hist_entity.template_version = hist_tmpl.template_version
            join public.clinicalcode_template as live_tmpl
              on hist_tmpl.id = live_tmpl.id
            left join public.clinicalcode_organisation org
              on org.id = live_entity.organisation_id
            left join public.clinicalcode_organisationmembership mem
              on mem.organisation_id = org.id
           where (
               {clauses}
           )
             {conditional}
             {pk_clause}
             {brand_clause}
      ) as t0
      join public.clinicalcode_historicalgenericentity as t1
        on t0.id = t1.id
       and t0.history_id = t1.history_id
     where t0.rn_ref_n = 1;
    '''

    if raw_query:
        return GenericEntity.history.raw(sql, params=query_params)

    with connection.cursor() as cursor:
        cursor.execute(sql, query_params)
        return GenericEntity.history.filter(history_id__in=[row[1] for row in cursor.fetchall()])

def get_latest_owner_version_from_concept(phenotype_id, concept_id, concept_version_id=None, default=None):
    """
        Gets the latest phenotype owner version id from a given concept
        and its expected owner id

        Args:
            phenotype_id (int): The phenotype owner id

            concept_id (int): The child concept id

            concept_version_id (int): An optional child concept version id

            default (any): An optional default return value

        Returns:
            Returns either (a) an integer representing the version id
                       OR; (b) the optional default value
    """
    latest_version = default
    with connection.cursor() as cursor:
        sql = None
        params = { 'phenotype_id': phenotype_id, 'concept_id': concept_id }
        if isinstance(concept_version_id, int):
            sql = '''

            with
              phenotype_children as (
                select id as phenotype_id,
                       history_id as phenotype_version_id,
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from (
                    select id,
                           history_id,
                           concepts
                      from public.clinicalcode_historicalgenericentity as entity,
                           json_array_elements(entity.template_data::json->'concept_information') as concepts
                     where json_array_length(entity.template_data::json->'concept_information') > 0
                       and id = %(phenotype_id)s
                  ) hge_concepts
                 where (concepts->>'concept_id')::int = %(concept_id)s
              ),
              priorities as (
                select t1.*, 1 as sel_priority
                  from phenotype_children as t1
                 where t1.concept_version_id = %(concept_version_id)s
                 union all
                select t2.*, 2 as sel_priority
                  from phenotype_children as t2
              ),
              sorted_ref as (
                select phenotype_id,
                       phenotype_version_id,
                       concept_id,
                       concept_version_id,
                       row_number() over (
                         partition by concept_version_id
                             order by sel_priority
                       ) as reference
                  from priorities
              )

            select phenotype_id,
                   max(phenotype_version_id) as phenotype_version_id
              from (
                select *
                  from sorted_ref
                 where reference = 1
              ) as pheno
              join public.clinicalcode_historicalgenericentity as entity
                on pheno.phenotype_id = entity.id
                and pheno.phenotype_version_id = entity.history_id
             group by phenotype_id;

            '''

            params.update({ 'concept_version_id': concept_version_id })
        else:
            sql = '''

            with
              phenotype_children as (
                select id as phenotype_id,
                       history_id as phenotype_version_id,
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from (
                    select id,
                           history_id,
                           concepts
                      from public.clinicalcode_historicalgenericentity as entity,
                           json_array_elements(entity.template_data::json->'concept_information') as concepts
                     where json_array_length(entity.template_data::json->'concept_information') > 0
                       and id = %(phenotype_id)s
                  ) hge_concepts
                 where (concepts->>'concept_id')::int = %(concept_id)s
              )

            select phenotype_id,
                   max(phenotype_version_id) as phenotype_version_id
              from phenotype_children as pheno
              join public.clinicalcode_historicalgenericentity as entity
                on pheno.phenotype_id = entity.id
                and pheno.phenotype_version_id = entity.history_id
             group by phenotype_id;
            '''

        cursor.execute(sql, params=params)

        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()

        if row is not None:
            row = dict(zip(columns, row))
            latest_version = row.get('phenotype_version_id')

    return latest_version
        

def get_accessible_concepts(
    request,
    min_group_permission=ORGANISATION_ROLES.MEMBER
):
    """
      Tries to get all the concepts that are accessible to a specific user

      Args:
        request (RequestContext): the HTTPRequest
        group_permissions (list): A list of which group permissions to consider

      Returns:
        List of accessible concepts
    """
    user = request.user
    concepts = Concept.history.none()

    if user.is_superuser:
        return Concept.history.all()

    if not user or user.is_anonymous:
        with connection.cursor() as cursor:
            sql = '''
            select distinct on (concept_id)
                   id as phenotype_id,
                   cast(concepts->>'concept_id' as integer) as concept_id,
                   cast(concepts->>'concept_version_id' as integer) as concept_version_id
              from (
                select id,
                       concepts
                  from public.clinicalcode_historicalgenericentity as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                 where
                   not exists (
                     select *
                       from public.clinicalcode_genericentity as ge
                      where ge.is_deleted = true and ge.id = entity.id
                   )
                   and entity.publish_status = %s
              ) results
             order by concept_id desc, concept_version_id desc
            '''
            cursor.execute(
                sql,
                params=[APPROVAL_STATUS.APPROVED.value]
            )
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            concepts = Concept.history.filter(
                id__in=[x.get('concept_id') for x in results],
                history_id__in=[x.get('concept_version_id') for x in results],
            )
        
        return concepts

    with connection.cursor() as cursor:
        sql = '''
        select distinct on (concept_id)
               results.id as phenotype_id,
               cast(results.concepts->>'concept_id' as integer) as concept_id,
               cast(results.concepts->>'concept_version_id' as integer) as concept_version_id
          from (
            select id,
                   concepts,
                   publish_status
              from public.clinicalcode_historicalgenericentity as entity,
                   json_array_elements(entity.template_data::json->'concept_information') as concepts
              where 
                 not exists (
                   select *
                     from public.clinicalcode_genericentity as ge
                    where ge.is_deleted = true and ge.id = entity.id
                 )
          ) results
          join public.clinicalcode_genericentity as live
            on live.id = results.id
          left join public.clinicalcode_organisation as org
            on org.id = live.organisation_id
          left join public.clinicalcode_organisationmembership as mem
            on mem.organisation_id = org.id
         where (
              results.publish_status = %(publish_status)s
           or org.owner_id = %(user_id)s
           or (mem.user_id = %(user_id)s and mem.role >= %(role_enum)s)
           or live.owner_id = %(user_id)s
         )
         order by concept_id desc, concept_version_id desc
        '''

        cursor.execute(
            sql,
            params={
                'publish_status': APPROVAL_STATUS.APPROVED.value, 
                'user_id': user.id, 
                'role_enum': min_group_permission,
            }
        )

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        concepts = Concept.history.filter(
            id__in=[x.get('concept_id') for x in results],
            history_id__in=[x.get('concept_version_id') for x in results],
        )

    return concepts

def can_user_view_entity(request, entity_id, entity_history_id=None):
    """
      Checks whether a user has the permissions to view an entity

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (number): The entity ID of interest
        entity_history_id (number) (optional): The entity's historical id of interest

      Returns:
        A boolean value reflecting whether the user is able to view an entity
    """
    live_entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if live_entity is None:
        return False

    if entity_history_id is not None:
        historical_entity = model_utils.try_get_entity_history(live_entity, entity_history_id)
        if historical_entity is None:
            return False
    else:
        historical_entity = live_entity.history.latest()
        entity_history_id = historical_entity.history_id

    is_published = is_publish_status(historical_entity, [APPROVAL_STATUS.APPROVED])
    if is_published:
        return True

    user = request.user
    if user.is_superuser:
        return check_brand_access(request, is_published, entity_id, entity_history_id)

    moderation_required = is_publish_status(
        historical_entity,
        [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
    )
    if is_member(user, 'Moderators') and moderation_required:
        return check_brand_access(request, is_published, entity_id, entity_history_id)

    if live_entity.owner == user:
        return check_brand_access(request, is_published, entity_id, entity_history_id)

    if has_member_access(user, live_entity, ORGANISATION_ROLES.MEMBER):
        return check_brand_access(request, is_published, entity_id, entity_history_id)

    return False

def get_accessible_detail_entity(request, entity_id, entity_history_id=None):
    """
      Gets the parent entity from a given `id`, returning both (a) the entity
      and (b) the edit/view access perms

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (number): The entity ID of interest

      Returns:
        Either tuple in which the first element is either (a) a dict containing the entity and the user's edit/view access or (b) a `None` type value;
        while the latter element, if unsuccessful, specifies a dict containing a `status_code`, a `title`, and a `message` property describing the failed state of this operation
    """
    live_entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if live_entity is None:
            return None, { 'title': 'Page Not Found - Missing Phenotype', 'message': 'No Phenotype exists with the ID.', 'status_code': 404 }

    if entity_history_id is not None:
        historical_entity = model_utils.try_get_entity_history(live_entity, entity_history_id)
        if historical_entity is None:
            return None, { 'title': 'Page Not Found - Missing Version', 'message': 'No Phenotype version exists with the specified version ID.', 'status_code': 404 }
    else:
        historical_entity = live_entity.history.latest()
        entity_history_id = historical_entity.history_id

    brand = getattr(request, 'BRAND_OBJECT', None)
    if isinstance(brand, (Brand, dict,)):
        brand_id = brand.get('id') if isinstance(brand, dict) else getattr(brand, 'id')
        brand_id = gen_utils.parse_int(brand_id, default=None)

    brand_accessible = False
    if brand_id is not None:
        related_brands = live_entity.brands
        if isinstance(related_brands, list):
            brand_accessible = brand_id in related_brands
    else:
        brand_accessible = True

    user = request.user if request.user and not request.user.is_anonymous else None
    user_groups = user.groups.all() if user is not None else None
    user_has_groups = user_groups.exists() if user_groups is not None else None

    user_is_admin = user.is_superuser if user else False
    user_is_moderator = ('Moderators' in list(user_groups.values_list('name', flat=True))) if user_has_groups else False

    is_viewable = False
    is_editable = False
    is_published = historical_entity.publish_status == APPROVAL_STATUS.APPROVED.value

    if user is not None:
        is_owner = live_entity.owner == user
        is_moderatable = False
        is_org_member = False

        if user_is_admin:
            is_editable = True
        elif brand_accessible:
            if live_entity.owner == user or live_entity.created_by == user:
                is_editable = True

            entity_org = live_entity.organisation if isinstance(live_entity.organisation, Model) else None
            if entity_org is not None:
                if entity_org.owner_id == user.id:
                    is_org_member = True
                else:
                    membership = user.organisationmembership_set \
                        .filter(organisation__id=entity_org.id)
                    is_org_member = membership.exists()

            if user_is_moderator and historical_entity.publish_status is not None:
                is_moderatable = historical_entity.publish_status in [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]

        is_viewable = brand_accessible and (
            user_is_admin
            or is_published
            or is_moderatable
            or (is_owner or is_org_member)
        )
    else:
        is_viewable = brand_accessible and is_published

    return {
        'entity': live_entity,
        'historical_entity': historical_entity,
        'edit_access': is_editable,
        'view_access': is_viewable,
        'is_published': is_published,
    }, None

def can_user_view_concept(
    request,
    historical_concept,
    min_group_permission=ORGANISATION_ROLES.MEMBER
):
    """
      Checks whether a user has the permissions to view a concept

      Args:
        request (RequestContext): the HTTPRequest
        historical_concept (HistoricalConcept): The concept of interest
        group_permissions (list): A list of which group permissions to consider

      Returns:
        A boolean value reflecting whether the user is able to view a concept
    """

    user = request.user
    if user and user.is_superuser:
        return True

    # Check legacy publish status & legacy ownership
    published_concept = PublishedConcept.objects.filter(
        concept_id=historical_concept.id,
        concept_history_id=historical_concept.history_id
    ).order_by('-concept_history_id').first()

    if published_concept is not None:
        return True

    if historical_concept.owner == user:
        return True

    # Check associated phenotypes
    concept = getattr(historical_concept, 'instance')
    if not concept:
        return False

    associated_phenotype = concept.phenotype_owner
    if associated_phenotype is not None:
        can_view = can_user_view_entity(
            request,
            associated_phenotype.id,
            associated_phenotype.history.latest().history_id
        )
        if can_view:
            return True
    
    # Check concept presence and status within Phenotypes
    # - this includes cases where phenotypes may have been imported and published later
    with connection.cursor() as cursor:
        if user.is_anonymous:
            sql = '''
            select *
              from (
                select distinct on (id)
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from public.clinicalcode_historicalgenericentity as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                 where 
                   (
                     cast(concepts->>'concept_id' as integer) = %s
                     and cast(concepts->>'concept_version_id' as integer) = %s
                   )
                   and not exists (
                     select *
                       from public.clinicalcode_genericentity as ge
                      where ge.is_deleted = true and ge.id = entity.id
                   )
                   and entity.publish_status = %s
                ) results
             limit 1;
            '''
            cursor.execute(
                sql,
                params=[
                    historical_concept.id, historical_concept.history_id,
                    APPROVAL_STATUS.APPROVED.value
                ]
            )
        else:
            sql = '''
            select distinct results.concept_id, results.concept_version_id
              from (
                select distinct on (id)
                       entity.id,
                       entity.publish_status,
                       cast(concepts->>'concept_id' as integer) as concept_id,
                       cast(concepts->>'concept_version_id' as integer) as concept_version_id
                  from public.clinicalcode_historicalgenericentity as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                 where 
                   (
                     cast(concepts->>'concept_id' as integer) = %(concept_id)s
                     and cast(concepts->>'concept_version_id' as integer) = %(concept_version_id)s
                   )
                   and not exists (
                     select *
                       from public.clinicalcode_genericentity as ge
                      where ge.is_deleted = true and ge.id = entity.id
                   )
              ) results
              join public.clinicalcode_genericentity as live
                on live.id = results.id
              left join public.clinicalcode_organisation as org
                on org.id = live.organisation_id
              left join public.clinicalcode_organisationmembership as mem
                on mem.organisation_id = org.id
             where (
                   results.publish_status = %(publish_status)s
                or org.owner_id = %(user_id)s
                or (mem.user_id = %(user_id)s and mem.role >= %(role_enum)s)
                or live.owner_id = %(user_id)s
             )
             limit 1
            '''
            cursor.execute(
                sql,
                params={
                    'concept_id': historical_concept.id, 
                    'concept_version_id': historical_concept.history_id,
                    'publish_status': APPROVAL_STATUS.APPROVED.value,
                    'user_id': user.id,
                    'role_enum': min_group_permission,
                }
            )
        
        row = cursor.fetchone()
        if row is not None:
            return True

    return False

def check_brand_access(request, is_published, entity_id, entity_history_id=None):
    """
      Checks whether an entity is accessible for the request brand,
      if the entity is published the accessibility via is_brand_accessible() will be ignored
    """
    if not is_published:
        return is_brand_accessible(request, entity_id, entity_history_id)
    return True

def can_user_edit_entity(request, entity_id, entity_history_id=None):
    """
      Checks whether a user has the permissions to modify an entity

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (number): The entity ID of interest
        entity_history_id (number) (optional): The entity's historical id of interest

      Returns:
        A boolean value reflecting whether the user is able to modify an entity
    """
    live_entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if live_entity is None:
        return False

    if entity_history_id is not None:
        historical_entity = model_utils.try_get_entity_history(live_entity, entity_history_id)
        if historical_entity is None:
            return False
    else:
        historical_entity = live_entity.history.latest()
        entity_history_id = historical_entity.history_id

    is_allowed_to_edit = False

    user = request.user
    if user.is_superuser:
        is_allowed_to_edit = True

    if live_entity.owner == user or live_entity.created_by == user:
        is_allowed_to_edit = True

    if has_member_access(user, live_entity, ORGANISATION_ROLES.EDITOR):
        is_allowed_to_edit = True

    if is_allowed_to_edit:
        if not is_brand_accessible(request, entity_id):
            is_allowed_to_edit = False

    return is_allowed_to_edit

def has_derived_edit_access(request, entity_id, entity_history_id=None):
    """
      Checks whether a user has derived its permissions from something
      other than ownership, e.g. in the case of group permissions

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (number): The entity ID of interest
        entity_history_id (number) (optional): The entity's historical id of interest

      Returns:
        A boolean value reflecting whether the user has derived edit access
    """
    user = request.user
    if not user or user.is_anonymous:
        return False
    
    live_entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if live_entity is None:
        return False

    if not is_brand_accessible(request, entity_id):
        return False

    if entity_history_id is not None:
        historical_entity = model_utils.try_get_entity_history(live_entity, entity_history_id)
        if historical_entity is None:
            return False
    else:
        historical_entity = live_entity.history.latest()
        entity_history_id = historical_entity.history_id

    if user.is_superuser or live_entity.owner == user or live_entity.created_by == user:
        return False
    elif has_member_access(user, live_entity, ORGANISATION_ROLES.EDITOR):
        return True

    return False

def get_latest_publicly_accessible_concept(concept_id):
    """
      Finds the latest publicly accessible published concept

      Returns:
        HistoricalConcept (obj) that is accessible by the user
    """

    concept = Concept.objects.filter(id=concept_id)
    if not concept.exists():
        return None

    concept = Concept.objects.none()
    with connection.cursor() as cursor:
        sql = '''
        select *
          from (
            select cast(concepts->>'concept_id' as integer) as concept_id,
                   cast(concepts->>'concept_version_id' as integer) as concept_version_id
              from public.clinicalcode_historicalgenericentity as entity,
                   json_array_elements(entity.template_data::json->'concept_information') as concepts
              where 
                    not exists (
                      select *
                        from public.clinicalcode_genericentity as ge
                       where ge.is_deleted = true and ge.id = entity.id
                    )
                    and entity.publish_status = %s
                    and entity.world_access = %s
          ) results
         where concept_id = %s
         order by concept_version_id desc
         limit 1
        '''

        cursor.execute(
            sql,
            params=[
                APPROVAL_STATUS.APPROVED.value,
                WORLD_ACCESS_PERMISSIONS.VIEW.value,
                concept_id
            ]
        )
        
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        concept = Concept.history.filter(
            id__in=[x.get('concept_id') for x in results],
            history_id__in=[x.get('concept_version_id') for x in results],
        )

    return concept.first() if concept.exists() else None

def user_can_edit_via_entity(request, concept):
    """
      Checks to see if a user can edit a child concept via it's phenotype owner's permissions
    """
    entity = concept.phenotype_owner

    if entity is None:
        try:
            instance = getattr(concept, 'instance')
            if instance is not None:
                entity = instance.phenotype_owner
        except:
            pass
    
    if entity is None:
        return False

    return can_user_edit_entity(request, entity)

def user_has_concept_ownership(user, concept):
    """
      [!] Legacy permissions method

      Determines whether the user has top-level access to the Concept,
      and can therefore modify it

      Args:
        user (User()): the user instance
        concept (Concept()): the concept instance

      Returns:
        (boolean) that reflects whether the user has top-level access
    """
    if user is None or concept is None:
        return False

    if concept.owner == user:
        return True

    return user.is_superuser or has_member_access(user, concept, ORGANISATION_ROLES.EDITOR)

def validate_access_to_view(request, entity_id, entity_history_id=None):
    """
      Validate access to view the entity
    """

    # Check if entity_id is valid, i.e. matches regex '^[a-zA-Z]\d+'
    true_entity_id = model_utils.get_entity_id(entity_id)
    if not true_entity_id:
        raise PermissionDenied

    # Check if the user has the permissions to view this entity version
    user_can_access = can_user_view_entity(request, entity_id, entity_history_id)
    if not user_can_access:
        # message = 'Entity version must be published or you must have permission to access it'
        raise PermissionDenied

def is_brand_accessible(request, entity_id, entity_history_id=None):
    """
      @desc Uses the RequestContext's brand value to det. whether an entity
            is accessible to a user

      Args:
        request (RequestContext): the HTTPRequest
        entity_id (string): the entity's ID
        entity_history_id (int, optional): the entity's historical id

      Returns:
        A (boolean) that reflects its accessibility to the request context
    """
    entity = model_utils.try_get_instance(GenericEntity, id=entity_id)
    if entity is None:
        return False

    brand = model_utils.try_get_brand(request)
    if brand is None:
        return True

    related_brands = entity.brands
    if not related_brands or len(related_brands) < 1:
        return False

    return brand.id in related_brands

def allowed_to_create():
    """
      Permit creation unless we have a READ-ONLY application.
    """
    return settings.CLL_READ_ONLY

def allowed_to_permit(user, entity_id):
    """
      The ability to change the owner of an entity remains with the owner and
      not with those granted editing permission. And with superusers to get
      us out of trouble, when necessary.

      Allow user to change permissions if:
        1. user is a super-user
        OR
        2. user owns the object.
    """
    if user.is_superuser:
        return True

    return GenericEntity.objects.filter(Q(id=entity_id), Q(owner=user)).exists()

class HasAccessToViewGenericEntityCheckMixin(object):
  """
    Mixin to check if user has view access to a working set
    this mixin is used within class based views and can be overridden
  """
  def dispatch(self, request, *args, **kwargs):
    if not can_user_view_entity(request, self.kwargs['pk']):
      raise PermissionDenied
    
    return super(HasAccessToViewGenericEntityCheckMixin, self).dispatch(request, *args, **kwargs)

def get_latest_entity_published(entity_id):
    """
      Gets latest published entity given an entity id
    """
    entity = GenericEntity.history.filter(
        id=entity_id, publish_status=APPROVAL_STATUS.APPROVED)
    if not entity.exists():
        return None

    entity = entity.order_by('-history_id')
    entity = entity.first()
    return entity

""" Legacy methods that require clenaup """
def get_publish_approval_status(set_class, set_id, set_history_id):
    """
        [!] Note: Legacy method from ./permissions.py
    
            Updated to only check GenericEntity since Phenotype/WorkingSet
            no longer exists in the current application
        
        @desc Get the publish approval status
    """

    if set_class == GenericEntity:
        return PublishedGenericEntity.objects.filter(
            entity_id=set_id,
            entity_history_id=set_history_id
        ) \
        .values_list('approval_status', flat=True) \
        .first()

    return False


def check_if_published(set_class, set_id, set_history_id):
    """
        [!] Note: Legacy method from ./permissions.py
        
            Updated to only check GenericEntity since Phenotype/WorkingSet
            no longer exists in the current application
        
        @desc Check if an entity version is published
    """
    
    if set_class == GenericEntity:
        return PublishedGenericEntity.objects.filter(
            entity_id=set_id,
            entity_history_id=set_history_id,
            approval_status=2
        ).exists()

    return False


def allowed_to_edit(request, set_class, set_id, user=None):
    """
        Legacy method from ./permissions.py for set_class

        Desc:
            Permit editing access if:
                - user is a super-user or the OWNER
                OR;
                - editing is permitted to EVERYONE
                OR;
                - editing is permitted to a GROUP that the user belongs to
        
            but NOT if:
                - the application is configured as READ-ONLY.
        
        (skip this for now)(The object must not be marked as deleted - even for superuser)
        --
        user will be read from request.user unless given directly via param: user
    """

    if settings.CLL_READ_ONLY:
        return False

    user = user if user else (request.user if request else None)
    if user is None:
        return False

    if user.is_superuser:
        return True

    is_allowed_to_edit = False
    if set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0:
        is_allowed_to_edit = True
    else:
        for group in user.groups.all():
            if set_class.objects.filter(Q(id=set_id), Q(group_access=GROUP_PERMISSIONS.EDIT, group_id=group)).count() > 0:
                is_allowed_to_edit = True

    if is_allowed_to_edit and request is not None and not is_brand_accessible(request, set_class, set_id):
        return False

    return is_allowed_to_edit
