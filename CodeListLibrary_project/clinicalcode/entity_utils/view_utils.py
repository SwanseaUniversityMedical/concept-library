import json
from django.apps import apps
from django.db.models import Q
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from ..models import GenericEntity, Template
from ..entity_utils import constants

'''
    Attempts to parse an int from a value, if it fails to do so, returns the default value
'''
def parse_int(value, default=0):
    try:
        return int(value)
    except ValueError:
        return default

'''
    Attempts to get a param from a request by key
        - If a default is passed and the key isn't present, the default is returned
        - If the key is present, and the default is non-null, it tries to parse the value as the default's type
'''
def try_get_param(request, key, default=None, method='GET'):
    try:
        req = getattr(request, method)
        param = req.get(key, default)
    except:
        return default
    else:
        if default is not None:
            if type(key) is not type(default):
                if isinstance(default, int):
                    return parse_int(param)
                # Add other types when necessary

    return param

'''
    Decodes the body of a request and attempts to load it as JSON
'''
def get_request_body(body):
    try:
        body = body.decode('utf-8');
        body = json.loads(body)
        return body
    except:
        return None

'''
    Attempts to get content within a dict by a key, if it fails to do so, returns the default value
'''
def try_get_content(body, key, default=None):
    try:
        if key in body:
            return body[key]
        return default
    except:
        return default

'''
    Checks whether a field is accounted for in the metadata of an entity e.g. name, tags, collections
'''
def is_metadata(entity, field):
    try:
        model = type(entity)
        data = model._meta.get_field(field)
        return True
    except:
        return False

'''
    Determines whether the definition of a layout is null
'''
def is_layout_safe(layout):
    if layout is None or 'definition' not in layout:
        return False

    return isinstance(layout['definition'], dict)

'''
    Determines whether the template data of an entity instance is null
'''
def is_data_safe(entity):
    if entity is not None:
        data = getattr(entity, 'template_data')
        return isinstance(data, dict)

'''
    Safely gets a field from a layout's field within its definition
'''
def get_layout_field(layout, field, default=None):
    if is_layout_safe(layout):
        definition = layout['definition']
        fields = try_get_content(definition, 'fields')
        if fields is not None:
            return try_get_content(fields, field, default)
    
    return default

'''
    Safely gets a field from an entity, either at the toplevel (e.g. its name) or from its template data (e.g. some dynamic field)
'''
def get_entity_field(entity, field, default=None):
    if not is_data_safe(entity):
        return default

    try:
        data = getattr(entity, field)
        if data is not None:
            return data
    except:
        data = getattr(entity, 'template_data')
        return try_get_content(data, field, default)

'''
    Safely gets a top-level metadata field
'''
def try_get_instance_field(instance, field, default=None):
    try:
        data = getattr(instance, field)
    except:
        return default
    else:
        return data

'''
    Tries to get the values from a top-level metadata field
        - This method assumes it is sourced i.e. has a foreign key (has different names and/or filters)
          to another table
'''
def get_metadata_value_from_source(entity, field, default=None):
    try:
        data = getattr(entity, field)
        if field in constants.sourced_data:
            info = constants.sourced_data[field]
            model = info['model']

            column = 'id'
            if 'query' in info:
                column = info['query']
            
            query = {
                f'{column}__in': data
            }

            if 'filter' in info:
                query = {**query, **info['filter']}

            queryset = model.objects.filter(Q(**query))
            if queryset.exists():
                relative = 'name'
                if 'relative' in info:
                    relative = info['relative']
                
                output = []
                for instance in queryset:
                    output.append({
                        'name': getattr(instance, relative),
                        'value': getattr(instance, column)
                    })
                
                return output if len(output) > 0 else default
    except:
        return default
    else:
        return default

'''
    Tries to get the options parameter from a layout's field entry
'''
def get_options_value(data, info, default=None):
    key = str(data)
    if key in info['options']:
        return info['options'][key]
    return default

'''
    Tries to get the sourced value of a dynamic field from its layout and/or another model (if sourced)
'''
def get_sourced_value(data, info, default=None):
    try:
        model = apps.get_model(app_label='clinicalcode', model_name=info['source'])
        relative = None
        if 'relative' in info:
            relative = info['relative']

        query = None
        if 'query' in info:
            query = {
                info['query']: data
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

'''
    Gets searchable entities and returns:
        1. The entity and its data
        2. The entity's rendering information joined with the template
'''
def get_renderable_entities(request):
    prefixes = GenericEntity.objects.order_by().values_list('entity_prefix', flat=True).distinct()
    prefixes = list(prefixes)
    
    templates = Template.objects.filter(entity_prefix__in=prefixes)
    
    layout = { }
    for template in templates:
        layout[template.entity_prefix] = {
            'id': template.id,
            'name': template.name,
            'definition': template.definition,
            'order': template.entity_order,
            'statistics': template.entity_statistics,
        }

    return GenericEntity.objects.all(), layout
