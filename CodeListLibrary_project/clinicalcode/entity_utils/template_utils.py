from django.apps import apps
from django.db.models import Q

from . import model_utils
from . import constants

def try_get_content(body, key, default=None):
    '''
        Attempts to get content within a dict by a key, if it fails to do so, returns the default value
    '''
    try:
        if key in body:
            return body[key]
        return default
    except:
        return default

def is_metadata(entity, field):
    '''
        Checks whether a field is accounted for in the metadata of an entity e.g. name, tags, collections
    '''
    try:
        model = type(entity)
        data = model._meta.get_field(field)
        return True
    except:
        return False

def is_layout_safe(layout):
    '''
        Determines whether the definition of a layout is null
    '''
    if layout is None:
        return False

    definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout, 'definition')
    if layout is None:
        return False
    return isinstance(definition, dict)

def is_data_safe(entity):
    '''
        Determines whether the template data of an entity instance is null
    '''
    if entity is not None:
        data = getattr(entity, 'template_data')
        return isinstance(data, dict)

def get_layout_fields(layout, default=None):
    '''
        Safely gets the fields from a layout
    '''
    if is_layout_safe(layout):
        definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout, 'definition')
        return try_get_content(definition, 'fields')
    return default

def get_layout_field(layout, field, default=None):
    '''
        Safely gets a field from a layout's field within its definition
    '''
    if is_layout_safe(layout):
        definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout, 'definition')
        fields = try_get_content(definition, 'fields')
        if fields is not None:
            return try_get_content(fields, field, default)
    
    return default

def get_ordered_definition(definition, clean_fields=False):
    '''
        Safely gets the 'layout_order' field from the definition and tries
        to reorder the JSONB result so that iteration over fields are in the correct
        order
    '''
    layout_order = try_get_content(definition, 'layout_order')
    if layout_order is None:
        return definition

    fields = try_get_content(definition, 'fields')
    if fields is None:
        return definition
    
    ordered_fields = { }
    for field in layout_order:
        content = try_get_content(fields, field)
        if clean_fields:
            content.pop('order')
        
        ordered_fields[field] = content

    definition['fields'] = ordered_fields

    if clean_fields:
        definition.pop('layout_order')

    return definition

def get_entity_field(entity, field, default=None):
    '''
        Safely gets a field from an entity, either at the toplevel (e.g. its name) or from its template data (e.g. some dynamic field)
    '''
    if not is_data_safe(entity):
        return default

    try:
        data = getattr(entity, field)
        if data is not None:
            return data
    except:
        data = getattr(entity, 'template_data')
        return try_get_content(data, field, default)

def get_field_item(layout, field, item, default=None):
    '''
        Gets a field item from a layout's field lookup
    '''
    field_data = try_get_content(layout, field)
    if field_data is None:
        return default
    
    return try_get_content(field_data, item, default)  

def try_get_instance_field(instance, field, default=None):
    '''
        Safely gets a top-level metadata field
    '''
    try:
        data = getattr(instance, field)
    except:
        return default
    else:
        return data

def is_filterable(layout, field):
    '''
        Checks if a field is filterable as defined by its layout
    '''
    search = get_field_item(layout, field, 'search')
    if search is None:
        return False
    
    return try_get_content(search, 'filterable')

def get_metadata_value_from_source(layout, entity, field, default=None):
    '''
        Tries to get the values from a top-level metadata field
            - This method assumes it is sourced i.e. has a foreign key (has different names and/or filters)
            to another table
    '''
    try:
        data = getattr(entity, field)
        fields = try_get_content(layout, 'fields')
        if field in fields:
            validation = get_field_item(fields, field, 'validation', { })
            source_info = validation.get('source')

            model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))

            column = 'id'
            if 'query' in source_info:
                column = source_info['query']

            if isinstance(data, model):
                data = getattr(data, column)
            
            if isinstance(data, list):
                query = {
                    f'{column}__in': data
                }
            else:
                query = {
                    f'{column}': data
                }

            if 'filter' in source_info:
                query = {**query, **source_info['filter']}
            
            queryset = model.objects.filter(Q(**query))
            if queryset.exists():
                relative = 'name'
                if 'relative' in source_info:
                    relative = source_info['relative']
                
                output = []
                for instance in queryset:
                    output.append({
                        'name': getattr(instance, relative),
                        'value': getattr(instance, column)
                    })
                
                return output if len(output) > 0 else default
    except:
        raise
    else:
        return default

def get_options_value(data, info, default=None):
    '''
        Tries to get the options parameter from a layout's field entry
    '''
    validation = try_get_content(info, 'validation')
    if validation is None:
        return False
    
    key = str(data)
    if key in validation['options']:
        return validation['options'][key]
    return default

def get_sourced_value(data, info, default=None):
    '''
        Tries to get the sourced value of a dynamic field from its layout and/or another model (if sourced)
    '''
    validation = try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        relative = None
        if 'relative' in source_info:
            relative = source_info['relative']

        query = None
        if 'query' in source_info:
            query = {
                source_info['query']: data
            }
        else:
            query = {
                'pk': data
            }

        queryset = model.objects.filter(Q(**query))
        if queryset.exists():
            queryset = queryset.first()
            return try_get_instance_field(queryset, relative, default)
        return default
    except:
        return default

def get_template_data_values(entity, layout, field, default=[]):
    '''
        Retrieves the sourced values from an entity in an array
    '''
    data = get_entity_field(entity, field)
    info = get_layout_field(layout, field)
    if not info or not data:
        return default
    
    validation = try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = try_get_content(validation, 'type')
    if field_type is None:
        return default

    if field_type == 'enum' or field_type == 'int':
        output = None
        if 'options' in validation:
            output = get_options_value(data, info)
        elif 'source' in validation:
            output = get_sourced_value(data, info)
        if output is not None:
            return [{
                'name': output,
                'value': data
            }]
    elif field_type == 'int_array':
        if 'source' in validation:
            values = [ ]
            for item in data:
                value = get_sourced_value(item, info)
                if value is not None:
                    values.append({
                        'name': value,
                        'value': item,
                    })
            
            return values
    elif field_type == 'concept':
        values = []
        for item in data:
            value = model_utils.get_concept_data(
                item['concept_id'], item['concept_version_id']
            )

            if value:
                values.append(value)

        return values

    return default

def is_single_search_only(template, field):
    '''
        Checks if the single_search_only attribute is present in a given template's field
    '''
    template = try_get_content(template, field)
    if template is None:
        return False
    
    search = get_field_item(template, field, 'search')
    if search is None:
        return False
        
    return try_get_content(search, 'single_search_only')
