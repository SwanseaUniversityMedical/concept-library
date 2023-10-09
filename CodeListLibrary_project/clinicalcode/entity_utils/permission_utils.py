from django.db import connection
from django.db.models import Q, Subquery, OuterRef
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from functools import wraps

from ..models.Concept import Concept
from ..models.GenericEntity import GenericEntity
from ..models.PublishedConcept import PublishedConcept
from ..models.PublishedGenericEntity import PublishedGenericEntity
from . import model_utils
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS, WORLD_ACCESS_PERMISSIONS

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
            raise PermissionDenied
        return fn(request, *args, **kwargs)

    return wrap

""" Status helpers """

def is_member(user, group_name):
    """
      Checks if a User instance is a member of a group
    """
    return user.groups.filter(name__iexact=group_name).exists()

def has_member_access(user, entity, permissions):
    """
      Checks if a user has access to an entity via its group membership
    """
    if entity.group_id in user.groups.all():
        return entity.group_access in permissions

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
    if not user:
        return []

    if user.is_superuser:
        return list(Group.objects.all().exclude(name='ReadOnlyUsers').values('id', 'name'))
    return list(user.groups.all().exclude(name='ReadOnlyUsers').values('id', 'name'))

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
    entities = GenericEntity.history.all() \
        .order_by('id', '-history_id') \
        .distinct('id')

    brand = model_utils.try_get_brand(request)
    if consider_brand and brand:
        entities = entities.filter(Q(brands__overlap=[brand.id]))

    if user and not user.is_anonymous:
        query = Q(owner=user.id)
        query |= Q(
            group_id__in=user.groups.all(),
            group_access__in=[GROUP_PERMISSIONS.EDIT]
        )

        entities = entities.filter(query) \
            .annotate(
                was_deleted=Subquery(
                    GenericEntity.objects.filter(
                        id=OuterRef('id'),
                        is_deleted=True
                    ) \
                    .values('id')
                )
            )

        if only_deleted:
            return entities.exclude(was_deleted__isnull=True)
        else:
            return entities.exclude(was_deleted__isnull=False)

    return None

def get_accessible_entities(
    request,
    consider_user_perms=True,
    only_deleted=False,
    status=[APPROVAL_STATUS.APPROVED],
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT],
    consider_brand=True
):
    """
      Tries to get all the entities that are accessible to a specific user

      Args:
        consider_user_perms (boolean): Whether to consider user perms i.e. superuser, moderation status etc
        only_deleted (boolean): Whether to incl/excl deleted entities
        status (list): A list of publication statuses to consider
        group_permissions (list): A list of which group permissions to consider
        consider_brand (boolean): Whether to consider the request Brand (only applies to Moderators, Non-Auth'd and Auth'd accounts)

      Returns:
        List of accessible entities
    """
    user = request.user
    entities = GenericEntity.history.all() \
        .order_by('id', '-history_id') \
        .distinct('id')

    brand = model_utils.try_get_brand(request)
    if consider_brand and brand:
        entities = entities.filter(Q(brands__overlap=[brand.id]))

    if user and not user.is_anonymous:
        if consider_user_perms and user.is_superuser:
            return entities.distinct('id')

        if consider_user_perms and is_member(user, 'Moderators'):
            status += [
                APPROVAL_STATUS.REQUESTED,
                APPROVAL_STATUS.PENDING, 
                APPROVAL_STATUS.REJECTED
            ]

        query = Q(owner=user.id)
        if not status:
            query |= ~Q(publish_status=APPROVAL_STATUS.PENDING)
        elif APPROVAL_STATUS.ANY in status:
            query |= Q(publish_status=APPROVAL_STATUS.APPROVED)
        else:
            query |= Q(publish_status__in=status)

        if group_permissions:
            query |= Q(
                group_id__in=user.groups.all(),
                group_access__in=group_permissions
            )

        # get world_access shared entities (if user is authenticated)
        query |= Q(
            world_access=WORLD_ACCESS_PERMISSIONS.VIEW
        )

        entities = entities.filter(query) \
            .annotate(
                was_deleted=Subquery(
                    GenericEntity.objects.filter(
                        id=OuterRef('id'),
                        is_deleted=True
                    ) \
                    .values('id')
                )
            )

        if only_deleted:
            entities = entities.exclude(was_deleted__isnull=True)
        else:
            entities = entities.exclude(was_deleted__isnull=False)

        return entities.distinct('id')

    entities = entities.filter(
        publish_status=APPROVAL_STATUS.APPROVED
    ) \
        .annotate(
            was_deleted=Subquery(
                GenericEntity.objects.filter(
                    id=OuterRef('id'),
                    is_deleted=True
                ) \
                .values('id')
            )
        ) \
        .exclude(was_deleted__isnull=False)

    return entities.distinct('id')

def get_accessible_concepts(
    request,
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
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
                params=[WORLD_ACCESS_PERMISSIONS.VIEW.value]
            )
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            concepts = Concept.history.filter(
                id__in=[x.get('concept_id') for x in results],
                history_id__in=[x.get('concept_version_id') for x in results],
            )
        
        return concepts

    group_access = [x.value for x in group_permissions]
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
                 and (
                   entity.publish_status = %s
                   or (
                    exists (
                      select 1
                        from public.auth_user_groups as t
                       where t.user_id = %s and t.group_id = entity.group_id
                    )
                    and entity.group_access in %s
                   )
                   or entity.owner_id = %s
                   or entity.world_access = %s
                 )
          ) results
         order by concept_id desc, concept_version_id desc
        '''

        cursor.execute(
            sql,
            params=[
                APPROVAL_STATUS.APPROVED.value, user.id, tuple(group_access),
                user.id, WORLD_ACCESS_PERMISSIONS.VIEW.value
            ]
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

    if has_member_access(user, live_entity, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]):
        return check_brand_access(request, is_published, entity_id, entity_history_id)

    if user and not user.is_anonymous:
        if live_entity.world_access == WORLD_ACCESS_PERMISSIONS.VIEW:
            return check_brand_access(request, is_published, entity_id, entity_history_id)

    return False

def can_user_view_concept(request,
                          historical_concept,
                          group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]):
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

    if has_member_access(user, historical_concept, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]):
        return True

    if user and not user.is_anonymous:
        if historical_concept.world_access == WORLD_ACCESS_PERMISSIONS.VIEW:
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
            group_access = [x.value for x in group_permissions]
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
                   and (
                     entity.publish_status = %s
                     or (
                       exists (
                         select 1
                           from public.auth_user_groups as t
                          where t.user_id = %s and t.group_id = entity.group_id
                       )
                       and entity.group_access in %s
                     )
                     or entity.owner_id = %s
                     or entity.world_access = %s
                   )
              ) results
             limit 1
            '''
            cursor.execute(
                sql,
                params=[
                    historical_concept.id, historical_concept.history_id,
                    APPROVAL_STATUS.APPROVED.value,
                    user.id, tuple(group_access),
                    user.id, WORLD_ACCESS_PERMISSIONS.VIEW.value
                ]
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

    if has_member_access(user, live_entity, [GROUP_PERMISSIONS.EDIT]):
        is_allowed_to_edit = True

    if is_allowed_to_edit:
        if not is_brand_accessible(request, entity_id):
            is_allowed_to_edit = False

    return is_allowed_to_edit

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

    return has_member_access(user, concept, [GROUP_PERMISSIONS.EDIT])

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

def get_latest_entity_historical_id(entity_id, user):
    """
      Gets the latest entity history id for a given entity
      and user, given the user has the permissions to access that
      particular entity
    """
    entity = model_utils.try_get_instance(GenericEntity, id=entity_id)

    if entity:
        if user.is_superuser:
            return int(entity.history.latest().history_id)

        if user and not user.is_anonymous:
            history = entity.history.filter(
                Q(owner=user.id) |
                Q(
                    group_id__in=user.groups.all(),
                    group_access__in=[
                        GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
                ) |
                Q(
                    world_access=WORLD_ACCESS_PERMISSIONS.VIEW
                )
            ) \
                .order_by('-history_id')

            if history.exists():
                return history.first().history_id

        published = get_latest_entity_published(entity.id)
        if published:
            return published.history_id

    return None

def get_latest_concept_historical_id(concept_id, user):
    """
      Gets the latest concept history id for a given concept
      and user, given the user has the permissions to access that
      particular concept
    """
    concept = model_utils.try_get_instance(Concept, pk=concept_id)

    if concept:
        if user.is_superuser:
            return int(concept.history.latest().history_id)

        if user and not user.is_anonymous:
            history = concept.history.filter(
                Q(owner=user.id) |
                Q(
                    group_id__in=user.groups.all(),
                    group_access__in=[
                        GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
                ) |
                Q(
                    world_access=WORLD_ACCESS_PERMISSIONS.VIEW
                )
            ) \
                .order_by('-history_id')

            if history.exists():
                return history.first().history_id

        published = get_latest_publicly_accessible_concept(concept_id)
        if published:
            return published.history_id

    return None

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

def get_latest_published_version(set_class, set_id):
    """
        [!] Note: Legacy method from ./permissions.py
        
            Updated to only check GenericEntity since Phenotype/WorkingSet
            no longer exists in the current application

        Get latest published version
    """

    latest_published_version = None 
    if set_class == GenericEntity:
        latest_published_version = PublishedGenericEntity.objects.filter(
            entity_id=set_id,
            approval_status=2
        ) \
        .order_by('-entity_history_id') \
        .first()

        if latest_published_version is not None:
            return latest_published_version.entity_history_id

    return latest_published_version

def try_get_valid_history_id(request, set_class, set_id):
    """
        [!] Note: Legacy method from ./permissions.py
        
        Tries to resolve a valid history id for an entity query.
        If the entity is accessible (i.e. validate_access_to_view() is TRUE), 
        then return the most recent version if the user is authenticated,      
        Otherwise, this method will return the most recently published version, if available.

        Args:
            request (RequestContext): the request
            set_class (str): a model
            set_id (str): the id of the entity

        Returns:
            int representing history_id
    """
    set_history_id = None
    is_authenticated = request.user.is_authenticated

    if is_authenticated:                   
        set_history_id = int(set_class.objects.get(pk=set_id).history.latest().history_id)

    if not set_history_id:
        latest_published_version_id = get_latest_published_version(set_class, set_id)
        if latest_published_version_id:
            set_history_id = latest_published_version_id

    return set_history_id

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
