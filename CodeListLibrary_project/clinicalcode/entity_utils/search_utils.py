import json
from django.apps import apps
from django.db.models import Q
from ..models import PublishedGenericEntity, GenericEntity, Template, Statistics
from . import model_utils, permission_utils, template_utils, constants

def get_request_body(body):
    '''
        Decodes the body of a request and attempts to load it as JSON
    '''
    try:
        body = body.decode('utf-8');
        body = json.loads(body)
        return body
    except:
        return None

def parse_int(value, default=0):
    '''
        Attempts to parse an int from a value, if it fails to do so, returns the default value
    '''
    try:
        return int(value)
    except ValueError:
        return default

def try_get_param(request, key, default=None, method='GET'):
    '''
        Attempts to get a param from a request by key
            - If a default is passed and the key isn't present, the default is returned
            - If the key is present, and the default is non-null, it tries to parse the value as the default's type
    '''
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

def validate_query_param(template, data, default=None):
    '''
    
    '''
    if 'source' in template:
        try:
            model = apps.get_model(app_label='clinicalcode', model_name=template['source'])
            query = {
                'pk__in': data
            }

            if 'filter' in template:
                query = query | template['filter']
                
            queryset = model.objects.filter(Q(**query))
            queryset = list(queryset.values_list('id', flat=True))
        except:
            return default
        else:
            return queryset if len(queryset) > 0 else default
    elif 'options' in data:
        options = template['options']
        cleaned = [ ]
        for item in data:
            if item in options:
                cleaned.append(item)
        return cleaned if len(cleaned) > 0 else default

def apply_param_to_query(query, template, param, data):
    '''
    
    '''
    template_data = template_utils.try_get_content(template, param)
    if 'filterable' not in template_data:
        return False

    field_type = template_utils.try_get_content(template_data, 'field_type')
    if field_type is None:
        return False
    
    if field_type == 'int' or field_type == 'enum':
        data = [int(x) for x in data.split(',') if parse_int(x)]
        data = validate_query_param(template_data, data)
        if data is not None:
            query[f'{param}__in'] = data
    elif field_type == 'int_array':
        data = [int(x) for x in data.split(',') if parse_int(x)]
        data = validate_query_param(template_data, data)
        if data is not None:
            query[f'{param}__overlap'] = data

def get_renderable_entities(request, entity_type=None, method='GET'):
    '''
        Method gets searchable, published entities and applies filters retrieved from the request param(s)

        Returns:
            1. The entities and their data
            2. The template associated with each of the entities
    '''
    if entity_type is None:
        templates = Template.objects.filter(entity_count__gt=0)
    else:
        if isinstance(entity_type, list):
            templates = Template.objects.filter(id__in=entity_type)
        else:
            templates = Template.objects.filter(id=entity_type)
    
    layouts = { }
    templates = templates.order_by('id')
    for template in templates:
        layouts[template.entity_prefix] = {
            'id': template.id,
            'name': template.name,
            'definition': template.definition,
            'order': template.entity_order,
            'statistics': template.entity_statistics,
        }

    is_single_search = Template.objects.count() > constants.MIN_SINGLE_SEARCH
    template_ids = list(templates.values_list('id', flat=True))

    # Get all entities assoc. with the templates requested
    entities = GenericEntity.objects.filter(template__in=template_ids).all()
    entities = PublishedGenericEntity.objects.filter(entity__in=entities).order_by('-created').distinct()
    
    # Gather request params for the filters across template when not single search
    template_filters = [ ]
    if not is_single_search:
        filters = set([])
        for items in templates.values_list('entity_filters', flat=True).distinct():
            filters = filters | set(items)
        template_filters = list(filters)

        template_fields = list(layouts.values())
        if len(template_fields) > 0:
            template_fields = template_utils.get_layout_fields(template_fields[0])

    # Gather metadata filter params
    metadata_filters = [key for key, value in constants.metadata.items() if 'filterable' in value]
    
    # Build query from filters
    query = { }
    for param, data in getattr(request, method).items():
        if param in metadata_filters:
            apply_param_to_query(query, constants.metadata, param, data)
        elif param in template_filters and not is_single_search:
            if template_fields is not None:
                apply_param_to_query(query, template_fields, param, data)
    
    # Collect all entities that are (1) published and (2) match request parameters
    #   [!] Need to add order clause modifier based on request param(s)
    entities = GenericEntity.history.filter(
        Q(**query) \
        & \
        Q(
            history_id__in=list(entities.values_list('entity_history_id', flat=True)),
            id__in=list(entities.values_list('entity_id', flat=True))
        )
    ).order_by('id')

    return entities, layouts

def get_metadata_stats_by_field(field):
    '''
        Retrieves the global statistics from metadata fields
    '''
    instance = model_utils.try_get_instance(Statistics, type='metadata')
    if instance is not None:
        stats = instance.stat
        return template_utils.try_get_content(stats, field)

def get_source_references(struct, default=[]):
    '''
        Retrieves the refence values from source fields e.g. tags, collections, entity type
    '''
    relative = template_utils.try_get_content(struct, 'relative')
    query = template_utils.try_get_content(struct, 'query', 'pk')
    if not relative:
        return default
    
    try:
        model = apps.get_model(app_label='clinicalcode', model_name=struct['source'])
        objs = model.objects.all()
        
        ref = []
        for obj in objs:
            pk = template_utils.try_get_instance_field(obj, query)
            data = template_utils.try_get_instance_field(obj, relative)
            if pk is not None and data is not None:
                ref.append({
                    'pk': pk,
                    'value': data
                })
        
        return ref
    except:
        return default

def get_filter_info(field, structure, default=None):
    '''
        Compiles the filter_info for a given field
    '''
    field_type = template_utils.try_get_content(structure, 'field_type')
    if field_type is None:
        return default
    
    return {
        'field': field,
        'type': field_type,
        'title': structure.get('title', field),
    }

def try_get_template_statistics(struct, field, default=None):
    '''
        Attempts to retrieve the statistics for a templated field from its parent template
    '''
    if not template_utils.is_layout_safe(struct):
        return default

    stats = template_utils.try_get_content(struct, 'statistics') if isinstance(struct, dict) else getattr(struct, 'entity_statistics')
    if stats is None:
        return default
    
    stats = template_utils.try_get_content(stats, field)
    if stats is None:
        return default
    
    return stats
