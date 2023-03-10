from django.db.models import Q

from ..models import GenericEntity
from ..models import PublishedGenericEntity
from . import model_utils
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS

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
  approval_status = model_utils.get_entity_approval_status(
    entity.id, entity.history_id
  )

  if approval_status:
    return approval_status in status

  return False

''' General permissions '''

def get_accessible_entities(request):  
  user = request.user
  if not user or not user.is_anonymous:
    entities = GenericEntity.history.all() \
      .order_by('id', '-history_id') \
      .distinct('id')
  
    if user.is_superuser:
      return entities
    
    status = [APPROVAL_STATUS.APPROVED]
    if is_member(user, "Moderators"):
      status += [APPROVAL_STATUS.REQUESTED, APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED]
      
    published_entities = PublishedGenericEntity.objects.filter(approval_status__in=status)

    entities = entities.filter(
      Q(owner=user.id) | 
      Q(
        group_id__in=user.groups.all(), 
        group_access__in=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
      ) |
      Q(id__in=list(published_entities.values_list('entity_id', flat=True)))
    )

    return entities
  
  entities = PublishedGenericEntity.objects \
    .filter(approval_status=APPROVAL_STATUS.APPROVED) \
    .order_by('-created') \
    .distinct()
  
  entities = GenericEntity.history.filter(
    id__in=list(entities.values_list('entity_id', flat=True)),
    history_id__in=list(entities.values_list('entity_history_id', flat=True))
  )
  
  return entities

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
