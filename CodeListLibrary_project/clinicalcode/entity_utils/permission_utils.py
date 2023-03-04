from . import model_utils
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS

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
    entity.entity_prefix, entity.entity_id, entity.entity_history_id
  )

  if approval_status:
    return approval_status in status

  return False

def has_entity_view_permissions(request, entity):
  '''

  '''  
  user = request.user
  if user.is_superuser:
    return True
  
  moderation_required = is_publish_status(entity, [APPROVAL_STATUS.PENDING, APPROVAL_STATUS.REJECTED])
  if is_member(user, "Moderators") and moderation_required:
    return True
  
  if entity.owner == user:
    return True
  
  is_published = is_publish_status(entity, [APPROVAL_STATUS.APPROVED])
  if is_published:
    return True
  
  return has_member_access(user, entity, [GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT])
