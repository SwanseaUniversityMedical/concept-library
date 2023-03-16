from ..models.GenericEntity import GenericEntity
from . import model_utils
from . import permission_utils

def try_validate_entity(request, entity_id):
    '''
      Validates existence of an entity and whether the user has permissions to modify it
    '''
    entity = model_utils.try_get_instance(GenericEntity, pk=entity_id)
    if entity is None:
        return False
    
    if permission_utils.has_entity_modify_permissions(request, entity):
        return entity
    
    return False
