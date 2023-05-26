from django.db.models import Q, F, Subquery, OuterRef
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response

from functools import wraps

from ..models import GenericEntity
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from . import model_utils, template_utils
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

def get_accessible_entities(
    request, 
    consider_user_perms=True,
    only_deleted=False,
    status=[APPROVAL_STATUS.APPROVED],
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT],
    consider_brand=True
  ):
  '''
    Tries to get the all entities that are accessible to a specific user

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
  
  brand = request.CURRENT_BRAND if request.CURRENT_BRAND != '' else None
  if consider_brand and brand:
    brand_collection_ids = model_utils.get_brand_collection_ids(brand)
    entities = entities.filter(collections__overlap=brand_collection_ids)
  
  if user and not user.is_anonymous:
    if consider_user_perms and user.is_superuser:
      return entities.distinct('id')
    
    if consider_user_perms and is_member(user, 'Moderators'):
      status += [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
      
    query = Q(owner=user.id) 
    if not status or APPROVAL_STATUS.ANY not in status:
      if status:
        query |= Q(publish_status__in=status)
      else:
        query |= ~Q(publish_status=APPROVAL_STATUS.PENDING)
    else:
      query |= Q(publish_status=APPROVAL_STATUS.APPROVED)
    
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
  
  if live_entity.owner == user:
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

def get_latest_publicly_accessible_concept():
  '''
    Finds the latest publicly accessible published concept
    
    Returns:
      HistoricalConcept {obj} that is accessible by the user
  '''
  concepts = Concept.history.annotate(
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
    return True
  
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
  
  # Concept doesn't have approval status?
  published_concept = is_concept_published(concept_id, concept_history_id)
  if published_concept and is_member(user, [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING]):
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
    When in a brand, show only this brand's data
  """

  # setting entity_history_id = None,
  # so this permission is always checked from the live obj like other permissions
  entity_history_id = None

  brand = request.CURRENT_BRAND
  if brand == "":
    return True
  
  brand_collection_ids = model_utils.get_brand_collection_ids(brand)
  if not brand_collection_ids:
    return True
  
  history_id = entity_history_id
  if entity_history_id is None:
    history_id = GenericEntity.objects.get(pk=entity_id).history.latest().history_id

  entity_collections = []
  entity_collections = GenericEntity.history.get(id=entity_id, history_id=history_id).collections

  if not entity_collections:
    return False
  
  # check if the set collections has any of the brand's collection tags
  return any(c in entity_collections for c in brand_collection_ids)

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
    user is a super-user
    OR
    user owns the object.
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
