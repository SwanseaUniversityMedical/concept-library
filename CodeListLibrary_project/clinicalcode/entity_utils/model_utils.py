from django.db.models import Q
import re

from ..models.GenericEntity import GenericEntity
from ..models.PublishedGenericEntity import PublishedGenericEntity
from ..models.Concept import Concept
from .constants import APPROVAL_STATUS, GROUP_PERMISSIONS

def try_get_instance(model, **kwargs):
  '''
    
  '''
  try:
    instance = model.objects.get(**kwargs)
  except:
    return None
  else:
    return instance
  
def try_get_entity_history(entity, history_id):
  '''
    
  '''
  try:
    instance = entity.history.get(history_id=history_id)
  except:
    return None
  else:
    return instance

def get_entity_id(primary_key):
  '''
    
  '''
  entity_id = re.split('(\d.*)', primary_key)
  if len(entity_id) >= 2 and entity_id[0].isalpha() and entity_id[1].isdigit():
    return entity_id[:2]
  else:
    return False

def get_latest_entity_published(entity_id):
  '''
    
  '''
  latest_published_entity = PublishedGenericEntity.objects.filter(
    entity_id=entity_id, approval_status=2
  ).order_by('-entity_history_id')
  
  if latest_published_entity.exists():
    return latest_published_entity.first()

  return None

def get_entity_approval_status(entity_id, historical_id):
  '''
    
  '''
  entity = try_get_instance(
    PublishedGenericEntity,
    entity_id=entity_id, 
    entity_history_id=historical_id
  )

  if entity:
    return entity.approval_status
  
  return None

def get_latest_entity_historical_id(entity_id, user):
  '''

  '''
  entity = try_get_instance(GenericEntity, id=entity_id)
      
  if entity:
    if user.is_superuser:
      return int(entity.history.latest().history_id)
    
    if user:
      history = entity.history.filter(
        Q(owner=user.id) | 
        Q(
          group_id__in=user.groups.all(),
          group_access__in=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
        )
      )
      
      if history.exists():
        return history.history_id
  
    published = get_latest_entity_published(entity)
    if published:
      return published.history.latest().history_id

  return None

def get_concept_data(concept_id, concept_history_id):
  concept = try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return None
  
  concept = try_get_entity_history(concept, concept_history_id)
  if not concept:
    return None
  
  return {
    'concept_id': concept_id,
    'concept_verion_id': concept_history_id,
    'coding_system': concept.coding_system.name,
    'data': {}
  }
