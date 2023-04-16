from django.apps import apps
from django.db.models import Q, ForeignKey
from django.contrib.auth.models import User, Group

from . import model_utils
from . import constants
from ..models import Brand
from ..models import Tag

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

def get_brand_collection_ids(brand_name):
    """
        Rreturns list of collections (tags) ids associated with the brand
    """
    if Brand.objects.all().filter(name__iexact=brand_name).exists():
        brand = Brand.objects.get(name__iexact=brand_name)
        brand_collection_ids = list(Tag.objects.filter(collection_brand=brand.id).values_list('id', flat=True))
        return brand_collection_ids
    else:
        return [-1]

def is_metadata(entity, field):
    '''
        Checks whether a field is accounted for in the metadata of an entity e.g. name, tags, collections
    '''
    try:
        data = entity._meta.get_field(field)
        return True
    except:
        pass

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
    
    return try_get_content(layout, field, default)

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

def get_one_of_field(entity, entity_fields, default=None):
    '''
    '''
    for field in entity_fields:
        value = None
        try:
            value = getattr(entity, field)
        except:
            pass

        if value:
            return value

    return default

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
        pass
    
    try:
        data = getattr(entity, 'template_data')
        return try_get_content(data, field, default)
    except:
        pass

    return default

def is_valid_field(entity, field):
    if is_metadata(entity, field):
        return True
    
    template = entity.template
    if template is None:
        return False
    
    if get_layout_field(template, field):
        return True
    
    return False

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

def get_metadata_field_value(entity, field_name, default=None):
    '''
    '''
    field = entity._meta.get_field(field_name)
    if not field:
        return default
    
    field_type = field.get_internal_type()
    if field_type in constants.STRIPPED_FIELDS or field_type in constants.HISTORICAL_HIDDEN_FIELDS:
        return default
    
    field_value = get_entity_field(entity, field_name)
    if field_value is None:
        return default
    
    if isinstance(field, ForeignKey):
        model = field.target_field.model
        model_type = str(model)
        if model_type in constants.USERDATA_MODELS:
            return {
                'id': field_value.id,
                'name': get_one_of_field(field_value, ['username', 'name'])
            }

    return field_value

def get_metadata_value_from_source(entity, field, default=None):
    '''
        Tries to get the values from a top-level metadata field
            - This method assumes it is sourced i.e. has a foreign key (has different names and/or filters)
            to another table
    '''
    try:
        data = getattr(entity, field)
        if field in constants.metadata:
            validation = get_field_item(constants.metadata, field, 'validation', { })
            source_info = validation.get('source')
            
            model = apps.get_model(
                app_label='clinicalcode', model_name=source_info.get('table')
            )

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
        pass
    else:
        return default

def get_template_sourced_values(template, field, default=None):
    '''
        Returns the complete option list of an enum or a sourced field
    '''
    struct = get_layout_field(template, field)
    if struct is None:
        return default

    validation = try_get_content(struct, 'validation')
    if validation is None:
        return default

    if 'options' in validation:
        output = []
        for i, v in validation.get('options').items():
            output.append({
                'name': v,
                'value': i
            })
        
        return output
    elif 'source' in validation:
        source_info = validation.get('source')
        try:
            model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
            
            column = 'id'
            if 'query' in source_info:
                column = source_info['query']

            if 'filter' in source_info:
                query = {**source_info['filter']}
            else:
                query = { }
            
            
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
            pass

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

def get_template_data_values(entity, layout, field, hide_user_details=False, default=[]):
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
            value = model_utils.get_clinical_concept_data(
                item['concept_id'], 
                item['concept_version_id'], 
                hide_user_details=hide_user_details
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