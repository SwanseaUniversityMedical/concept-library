from ..models.GenericEntity import GenericEntity
from . import model_utils
from . import permission_utils
from . import template_utils

def try_validate_entity(request, entity_id, entity_history_id):
    '''
      Validates existence of an entity and whether the user has permissions to modify it
    '''
    if not permission_utils.can_user_edit_entity(request, entity_id, entity_history_id):
        return False
    
    return GenericEntity.history.get(id=entity_id, history_id=entity_history_id)

def get_template_creation_data(entity, layout, field, default=[]):
    '''
        Used to retrieve assoc. data values for specific keys, e.g.
        concepts, in its expanded format for use with create/update pages
    '''
    data = template_utils.get_entity_field(entity, field)
    info = template_utils.get_layout_field(layout, field)
    if not info or not data:
        return default
    
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default
    
    if field_type == 'concept':
        values = []
        for item in data:
            value = model_utils.get_clinical_concept_data(
                item['concept_id'],
                item['concept_version_id'],
                aggregate_component_codes=True
            )

            if value:
                values.append(value)
        
        return values
    
    if template_utils.is_metadata(entity, field):
        return template_utils.get_metadata_value_from_source(entity, field, default=default)
    
    return template_utils.get_template_data_values(entity, layout, field, default=default)
