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

def get_renderable_entities(request, entity_type=None):
    '''
        Gets searchable, published entities and returns:
            1. The entity and its data
            2. The entity's rendering information joined with the template
    '''
    if entity_type is None:
        templates = Template.objects.filter(entity_count__gt=0)
    else:
        templates = Template.objects.filter(id=entity_type)
    
    layout = { }
    templates = templates.order_by('id')
    for template in templates:
        layout[template.entity_prefix] = {
            'id': template.id,
            'name': template.name,
            'definition': template.definition,
            'order': template.entity_order,
            'statistics': template.entity_statistics,
        }

    template_ids = list(templates.values_list('id', flat=True))

    entities = GenericEntity.objects.filter(template__in=template_ids).all()
    entities = PublishedGenericEntity.objects.filter(entity__in=entities).order_by('-created').distinct().order_by('id')
    entities = [x.entity.history.get(history_id=x.entity_history_id) for x in entities.all()]

    return entities, layout

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
