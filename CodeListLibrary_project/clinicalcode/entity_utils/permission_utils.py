from django.db.models import Q, F, Subquery, OuterRef
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied

from functools import wraps

from ..models import GenericEntity
from ..models import PublishedGenericEntity
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from . import model_utils
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS

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

  '''
  return user.groups.filter(name__iexact=group_name).exists()

def has_member_access(user, entity, permissions):
  '''

  '''
  if entity.group_id in user.groups.all():
    return entity.group_access in permissions
  
  return False

def is_publish_status(entity, status):
  '''
  
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
    group_permissions=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
  ):  
  user = request.user
  if user and not user.is_anonymous:
    entities = GenericEntity.history.all() \
      .order_by('id', '-history_id') \
      .distinct('id')
  
    if consider_user_perms and user.is_superuser:
      return entities
    
    if consider_user_perms and is_member(user, "Moderators"):
      status += [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
      
    query = Q(owner=user.id) 
    if not status or APPROVAL_STATUS.ANY not in status:
      if status:
        published_entities = PublishedGenericEntity.objects.filter(approval_status__in=status)
        entities = entities.filter(
          id__in=published_entities.values_list('entity_id', flat=True)
        )
      else:
        published_entities = PublishedGenericEntity.objects.all()
        entities = entities.exclude(
          id__in=list(published_entities.values_list('entity_id', flat=True))
        )
    
    if group_permissions:
      query |= Q(
        group_id__in=user.groups.all(), 
        group_access__in=group_permissions
      )
      
    entities = entities.filter(query)

    if only_deleted:
      entities = entities.exclude(Q(is_deleted=False) | Q(is_deleted__isnull=True) | Q(is_deleted=None))
    else:
      entities = entities.exclude(Q(is_deleted=True))

    return entities
  
  entities = PublishedGenericEntity.objects \
    .filter(approval_status=APPROVAL_STATUS.APPROVED) \
    .order_by('-created') \
    .distinct()
  
  entities = GenericEntity.history.filter(
    id__in=list(entities.values_list('entity_id', flat=True)),
    history_id__in=list(entities.values_list('entity_history_id', flat=True))
  )
  
  return entities.filter(Q(is_deleted=False) | Q(is_deleted=None))

def has_entity_view_permissions(request, entity):
  '''

  '''  
  user = request.user
  if user.is_superuser:
    return True
  
  moderation_required = is_publish_status(
    entity, [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
  )
  if is_member(user, "Moderators") and moderation_required:
    return True
  
  if entity.owner == user:
    return True
  
  is_published = is_publish_status(entity, [APPROVAL_STATUS.APPROVED])
  if is_published:
    return True
  
  return has_member_access(user, entity, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT])

def has_entity_modify_permissions(request, entity):
  '''
    Checks whether a user has the permissions to modify an entity
  '''
  user = request.user
  if user.is_superuser:
    return True
  
  moderation_required = is_publish_status(
    entity, [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING]
  )
  if is_member(user, "Moderators") and moderation_required:
    return True
  
  if entity.owner == user:
    return True

  return has_member_access(user, entity, [GROUP_PERMISSIONS.EDIT])

def can_user_edit_entity(request, entity_id, entity_history_id):
  '''
    Checks whether a user has the permissions to modify an entity

    Args:
      entity_id {number}: The entity ID of interest
      entity_history_id {number}: The entity's historical id of interest
    
    Returns:
      A boolean value reflecting whether the user is able to modify an entity
  '''
  
  entity = model_utils.try_get_instance(
    GenericEntity,
    pk=entity_id
  )
  if entity is None:
    return False
  
  historical_entity = model_utils.try_get_entity_history(entity, entity_history_id)
  if historical_entity is None:
    return False
  
  user = request.user
  if user.is_superuser:
    return True
  
  if is_member(user, 'moderator'):
    published_entity = model_utils.try_get_instance(
      PublishedGenericEntity,
      entity_id=entity_id,
      entity_history_id=entity_history_id
    )
  
    if published_entity is not None and published_entity.approval_status in [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING]:
      return True
  
  if historical_entity.owner == user:
    return True
  
  return has_member_access(user, historical_entity, [GROUP_PERMISSIONS.EDIT])

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

def can_user_edit_concept(request, concept_id, concept_history_id):
  '''
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
