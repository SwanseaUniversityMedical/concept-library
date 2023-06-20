from django.db.models import Q, Subquery, OuterRef
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from functools import wraps

from ..models.Concept import Concept
from ..models.GenericEntity import GenericEntity
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from . import model_utils
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS, WORLD_ACCESS_PERMISSIONS

''' Permission decorators '''
def redirect_readonly(fn):
  '''
    Method decorator to raise 403 if we're on the read only site
    to avoid insert / update methods via UI

    e.g. 
    
    @permission_utils.redirect_readonly
    def some_view_func(request):
      # stuff
    
  '''
  @wraps(fn)
  def wrap(request, *args, **kwargs):
    if settings.CLL_READ_ONLY:
      raise PermissionDenied
    return fn(request, *args, **kwargs)
  
  return wrap

''' Status helpers '''

def is_member(user, group_name):
  '''
    Checks if a User instance is a member of a group
  '''
  return user.groups.filter(name__iexact=group_name).exists()

def has_member_access(user, entity, permissions):
  '''
    Checks if a user has access to an entity via its group membership
  '''
  if entity.group_id in user.groups.all():
    return entity.group_access in permissions
  
  return False

def is_publish_status(entity, status):
  '''
    Checks the publication status of an entity
  '''
  history_id = getattr(entity, 'history_id', None)
  if history_id is None:
    history_id = entity.history.latest().history_id
  
  approval_status = model_utils.get_entity_approval_status(
    entity.id, history_id
  )

  if approval_status:
    return approval_status in status
  return False

''' General permissions '''
def get_user_groups(request):
  '''
    Get the groups related to the requesting user
  '''
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
  '''
    Returns entities with moderation status of specified status

    Args:
      request {RequestContext}: HTTP context
      status {List}: List of integers representing status
    
    Returns:
      List of all entities with specified moderation status
  '''
  entities = GenericEntity.history.all() \
    .order_by('id', '-history_id') \
    .distinct('id')
  
  return entities.filter(Q(publish_status__in=status))

def get_editable_entities(
    request,
    only_deleted=False
  ):
  '''
    Tries to get all the entities that are editable by a specific user

    Args:
      request {RequestContext}: HTTP context
      only_deleted {boolean}: Whether to only show deleted phenotypes or not 
  
    Returns:
      List of all editable entities
  '''
  user = request.user
  entities = GenericEntity.history.all() \
    .order_by('id', '-history_id') \
    .distinct('id')
  
  if user and not user.is_anonymous:
    query = Q(owner=user.id) 
    query |= Q(
      group_id__in=user.groups.all(), 
      group_access__in=[GROUP_PERMISSIONS.EDIT]
    )

    entities = entities.filter(query)
    if only_deleted:
      return entities.exclude(Q(is_deleted=False) | Q(is_deleted__isnull=True) | Q(is_deleted=None))
    else:
      return entities.exclude(Q(is_deleted=True))

  return None

def get_accessible_entities(
    request, 
    consider_user_perms=True,
    only_deleted=False,
    status=[APPROVAL_STATUS.APPROVED],
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT],
    consider_brand=True
  ):
  '''
    Tries to get all the entities that are accessible to a specific user

    Args:
      consider_user_perms {boolean}: Whether to consider user perms i.e. superuser, moderation status etc

      only_deleted {boolean}: Whether to incl/excl deleted entities

      status {list}: A list of publication statuses to consider

      group_permissions {list}: A list of which group permissions to consider

      consider_brand {boolean}: Whether to consider the request Brand (only applies to Moderators, Non-Auth'd and Auth'd accounts)
      
    Returns:
      List of accessible entities
    
  '''
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
      status += [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
      
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

    entities = entities.filter(query)
    if only_deleted:
      entities = entities.exclude(Q(is_deleted=False) | Q(is_deleted__isnull=True) | Q(is_deleted=None))
    else:
      entities = entities.exclude(Q(is_deleted=True))

    return entities.distinct('id')
  
  entities = entities.filter(
    publish_status=APPROVAL_STATUS.APPROVED
  ) \
  .filter(Q(is_deleted=False) | Q(is_deleted=None))
  
  return entities.distinct('id')

def get_accessible_concepts(
    request, 
    consider_user_perms=True,
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
  ):
  '''
    Tries to get all the concepts that are accessible to a specific user

    Args:
      consider_user_perms {boolean}: Whether to consider user perms i.e. superuser
      group_permissions {list}: A list of which group permissions to consider

    Returns:
      List of accessible concepts
    
  '''
  phenotypes = get_accessible_entities(
    request, 
    consider_user_perms=consider_user_perms, 
    status=[APPROVAL_STATUS.ANY]
  )
  concepts_from_phenotypes = Concept.history.all() \
    .filter(phenotype_owner__id__in=phenotypes.values('id')) \
    .distinct('id')
  
  concepts = Concept.history.all() \
    .annotate(
      is_published=Subquery(
        PublishedConcept.objects.filter(
          concept_id=OuterRef('id'),
          concept_history_id=OuterRef('history_id')
        ) \
        .order_by('id') \
        .distinct('id') \
        .values('id')
      )
    ) \
    .order_by('id', '-history_id') \
    .distinct('id')
  
  user = request.user
  if user and not user.is_anonymous:
    if consider_user_perms and user.is_superuser:
      return concepts.distinct('id')
    
    concepts = concepts.filter(
      Q(owner=user.id) | 
      Q(
        group_id__in=user.groups.all(), 
        group_access__in=group_permissions
      ) |
      Q(world_access=WORLD_ACCESS_PERMISSIONS.VIEW) |
      Q(is_published__isnull=False)
    )
  
    return (concepts | concepts_from_phenotypes).distinct('id')
  
  concepts = concepts.filter(Q(is_published__isnull=False))

  return (concepts | concepts_from_phenotypes).distinct('id')

def can_user_view_entity(request, entity_id, entity_history_id=None):
  '''
    Checks whether a user has the permissions to view an entity
    
    Args:
      entity_id {number}: The entity ID of interest
      entity_history_id {number} (optional): The entity's historical id of interest
    
    Returns:
      A boolean value reflecting whether the user is able to view an entity
  '''
  
  # since permissions are derived from the live entity (not from historical records),
  # get live entity  
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
    historical_entity, [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
  )
  if is_member(user, "Moderators") and moderation_required:
    return check_brand_access(request, is_published, entity_id, entity_history_id)
  
  if live_entity.owner == user:
    return check_brand_access(request, is_published, entity_id, entity_history_id)
    
  if has_member_access(user, live_entity, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]):
    return check_brand_access(request, is_published, entity_id, entity_history_id)
  
  if user and not user.is_anonymous:
    if live_entity.world_access == WORLD_ACCESS_PERMISSIONS.VIEW:
      return check_brand_access(request, is_published, entity_id, entity_history_id)
     
  return False

def can_user_view_concept(request, concept):
  '''
    Checks whether a user has the permissions to view a concept
    
    Args:
      concept {Concept}: The concept of interest
    
    Returns:
      A boolean value reflecting whether the user is able to view a concept
  '''
  published_concept = PublishedConcept.objects.filter(
    concept_id=concept.id,
    concept_history_id=concept.history_id
  ).order_by('-concept_history_id').first()

  if published_concept is not None:
    return True
  
  user = request.user
  if user.is_superuser:
    return True
  
  if concept.owner == user:
    return True
  
  if has_member_access(user, concept, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]):
    return True
  
  if user and not user.is_anonymous:
    if concept.world_access == WORLD_ACCESS_PERMISSIONS.VIEW:
      return True
  
  associated_phenotype = concept.phenotype_owner
  if associated_phenotype is not None:
    return can_user_view_entity(
      request, 
      associated_phenotype.id,
      associated_phenotype.history().latest().history_id
    )
  
  return False
 
def check_brand_access(request, is_published, entity_id, entity_history_id=None):
  '''
    Checks whether an entity is accessible for the request brand,
    if the entity is published the accessibility via is_brand_accessible() will be ignored
  '''
  if not is_published:
    return is_brand_accessible(request, entity_id, entity_history_id)
  return True

def can_user_edit_entity(request, entity_id, entity_history_id=None):
  '''
    Checks whether a user has the permissions to modify an entity

    Args:
      entity_id {number}: The entity ID of interest
      entity_history_id {number} (optional): The entity's historical id of interest
    
    Returns:
      A boolean value reflecting whether the user is able to modify an entity
  '''
  
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
  
  ''' Moderator does not have EDIT permission on publish-requests '''
  # if is_member(user, 'moderator'):
  #   status = historical_entity.publish_status  
  #   if status is not None and status in [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING]:
  #     is_allowed_to_edit = True
  
  if live_entity.owner == user or live_entity.created_by == user:
    is_allowed_to_edit = True
  
  if has_member_access(user, live_entity, [GROUP_PERMISSIONS.EDIT]):
    is_allowed_to_edit = True
    
  # check brand access
  if is_allowed_to_edit:
    if not is_brand_accessible(request, entity_id):
        is_allowed_to_edit = False
            
  return is_allowed_to_edit 

def is_concept_published(concept_id, concept_history_id):
  '''
    [!] Legacy permission method

    Checks whether a concept is published, and if so, returns the PublishedConcept

    Args:
      concept_id {number}: The concept ID of interest
      concept_history_id {number}: The concept's historical id of interest
    
    Returns:
      PublishedConcept value that reflects whether that particular concept is published
      Or returns None type if not published
  '''
  published_concept = model_utils.try_get_instance(
    PublishedConcept,
    concept_id=concept_id,
    concept_history_id=concept_history_id
  )
  
  return published_concept

def get_latest_publicly_accessible_concept(concept_id):
  '''    
    Finds the latest publicly accessible published concept
    
    Returns:
      HistoricalConcept {obj} that is accessible by the user
  '''
  concepts = Concept.history.filter(
    pk=concept_id
  ) \
  .annotate(
    is_published=Subquery(
      PublishedConcept.objects.filter(
        concept_id=OuterRef('id'),
        concept_history_id=OuterRef('history_id')
      ) \
      .order_by('id') \
      .distinct('id') \
      .values('id')
    )
  ) \
  .exclude(is_published__isnull=True) \
  .order_by('-history_id')

  return concepts.first() if concepts.exists() else None

def user_can_edit_via_entity(request, concept):
  '''
    Checks to see if a user can edit a child concept via it's phenotype owner's permissions
  '''
  entity = concept.phenotype_owner
  if entity is None:
    return False
  
  return can_user_edit_entity(request, entity)

def can_user_edit_concept(request, concept_id, concept_history_id):
  '''
    [!] Legacy permissions method

    Checks whether a user can edit with a concept, e.g. in the case that:
      1. If they are a superuser
      2. If they are a moderator and its in the approval process
      3. If they own that version of the concept
      4. If they share group access

    Args:
      request {RequestContext}: The HTTP Request context
      concept_id {number}: The concept ID of interest
      concept_history_id {number}: The concept's historical id of interest
    
    Returns:
      Boolean value that reflects whether is it able to be edited
      by the user
  '''  
  concept = model_utils.try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return False
  
  historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
  if not historical_concept:
    return False
  
  user = request.user
  if user.is_superuser:
    return True
      
  if concept.owner == user:
    return True
  
  return has_member_access(user, concept, [GROUP_PERMISSIONS.EDIT])

def user_has_concept_ownership(user, concept):
  '''
    [!] Legacy permissions method

    Determines whether the user has top-level access to the Concept,
    and can therefore modify it

    Args:
      user {User()} - the user instance
      concept {Concept()} the concept instance
    
    Returns:
      {boolean} that reflects whether the user has top-level access
  '''
  if user is None or concept is None:
    return False

  if concept.owner == user:
    return True
  
  return has_member_access(user, concept, [GROUP_PERMISSIONS.EDIT])

def validate_access_to_view(request, entity_id, entity_history_id=None):
  '''
    Validate access to view the entity
  '''
  
  # Check if entity_id is valid, i.e. matches regex '^[a-zA-Z]\d+'
  true_entity_id = model_utils.get_entity_id(entity_id)
  if not true_entity_id:
    raise PermissionDenied

  # Check if the user has the permissions to view this entity version
  user_can_access = can_user_view_entity(request, entity_id, entity_history_id)
  if not user_can_access:
    #message = 'Entity version must be published or you must have permission to access it'
    raise PermissionDenied

def is_brand_accessible(request, entity_id, entity_history_id=None):
  """
    @desc Uses the RequestContext's brand value to det. whether an entity
          is accessible to a user

    Args:
      request {RequestContext}: the HTTPRequest

      entity_id {string}: the entity's ID

      entity_history_id {int/null}: the entity's historical id

    Returns:
      A {boolean} that reflects its accessibility to the request context

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
  '''
    Permit creation unless we have a READ-ONLY application.
  '''
  return settings.CLL_READ_ONLY

def allowed_to_permit(user, entity_id):
  '''
    The ability to change the owner of an entity remains with the owner and
    not with those granted editing permission. And with superusers to get
    us out of trouble, when necessary.

    Allow user to change permissions if:
      1. user is a super-user
      OR
      2. user owns the object.
  '''
  if user.is_superuser:
    return True
  
  return GenericEntity.objects.filter(Q(id=entity_id), Q(owner=user)).exists()

class HasAccessToViewGenericEntityCheckMixin(object):
  '''
    Mixin to check if user has view access to a working set
    this mixin is used within class based views and can be overridden
  '''
  def dispatch(self, request, *args, **kwargs):
    if can_user_view_entity(request.user, self.kwargs['pk']):
      raise PermissionDenied

    return super(HasAccessToViewGenericEntityCheckMixin, self).dispatch(request, *args, **kwargs)

def get_latest_entity_published(entity_id):
  '''
    Gets latest published entity given an entity id
  '''
  entity = GenericEntity.history.filter(id=entity_id, publish_status=APPROVAL_STATUS.APPROVED)
  if not entity.exists():
    return None
  
  entity = entity.order_by('-history_id')
  entity = entity.first()
  return entity

def get_latest_entity_historical_id(entity_id, user):
  '''
    Gets the latest entity history id for a given entity
    and user, given the user has the permissions to access that
    particular entity
  '''
  entity = model_utils.try_get_instance(GenericEntity, id=entity_id)
      
  if entity:
    if user.is_superuser:
      return int(entity.history.latest().history_id)
    
    if user and not user.is_anonymous:
      history = entity.history.filter(
        Q(owner=user.id) | 
        Q(
          group_id__in=user.groups.all(),
          group_access__in=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
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
  '''
    Gets the latest concept history id for a given concept
    and user, given the user has the permissions to access that
    particular concept
  '''
  concept = model_utils.try_get_instance(Concept, pk=concept_id)

  if concept:
    if user.is_superuser:
      return int(concept.history.latest().history_id)
    
    if user and not user.is_anonymous:
      history = concept.history.filter(
        Q(owner=user.id) | 
        Q(
          group_id__in=user.groups.all(),
          group_access__in=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
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
