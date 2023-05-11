from functools import cmp_to_key
from ..models import GenericEntity, Template, Statistics, PublishedGenericEntity, Brand
from . import template_utils, constants, gen_utils

def sort_by_count(a, b):
    '''
        Used to sort filter statistics in descending order
    '''
    count0 = a['count']
    count1 = b['count']
    if count0 < count1:
        return 1
    elif count0 > count1:
        return -1
    return 0

def get_field_values(field, validation, struct):
    value = None
    if 'options' in validation:
        value = template_utils.get_options_value(field, struct)
    elif 'source' in validation:
        value = template_utils.get_sourced_value(field, struct)
    return value

def try_get_cached_data(cache, template, field, validation, struct):
    if template is None or not isinstance(cache, dict):
        return get_field_values(field, validation, struct)
    
    cache_key = f'{field}__{template.id}__{template.template_version}'
    if not cache_key in cache:
        value = get_field_values(field, validation, struct)
        if value is None:
            return None
        
        cache[cache_key] = value
        return value
    
    return cache[cache_key]

def build_statistics(statistics, entity, field, struct, is_dynamic=False, data_cache=None, template_entity=None):
    if not is_dynamic:
        struct = template_utils.try_get_content(constants.metadata, field)
    
    if struct is None:
        return
    
    if 'search' not in struct:
        return

    if 'filterable' not in struct.get('search'):
        return
    
    validation = template_utils.try_get_content(struct, 'validation')
    if validation is None:
        return
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return
    
    entity_field = template_utils.get_entity_field(entity, field)
    if entity_field is None:
        return

    stats = statistics[field] if field in statistics else { }
    if field_type == 'enum':
        value = try_get_cached_data(data_cache, template_entity, entity_field, validation, struct)
        
        if value is not None:
            if entity_field not in stats:
                stats[entity_field] = {
                    'value': value,
                    'count': 0
                }
            
            stats[entity_field]['count'] += 1
    elif field_type == 'int_array':
        if 'source' in validation:
            for item in entity_field:
                value = try_get_cached_data(data_cache, template_entity, item, validation, struct)
                if value is None:
                    continue
                if item not in stats:
                    stats[item] = {
                        'value': value,
                        'count': 0
                    }
                
                stats[item]['count'] += 1
    else:
        return
    
    statistics[field] = stats

def compute_statistics(statistics, entity, data_cache=None):
    if not template_utils.is_data_safe(entity):
        return
    
    template = Template.history.filter(
        id=entity.template.id,
        template_version=entity.template_version
    ) \
    .latest_of_each() \
    .distinct()

    if not template.exists():
        return
    
    template = template.first()
    layout = template.definition
    for field, struct in layout.get('fields').items():
        if not isinstance(struct, dict):
            continue

        is_dynamic = 'is_base_field' not in struct
        build_statistics(statistics, entity, field, struct, is_dynamic=is_dynamic, data_cache=None, template_entity=template)

def collate_statistics(all_entities, published_entities, data_cache=None):
    statistics = {
        'published': { },
        'all': { },
    }

    for entity in all_entities:
        compute_statistics(statistics['all'], entity, data_cache)

    for entity in published_entities:
        compute_statistics(statistics['published'], entity, data_cache)

    sort_fn = cmp_to_key(sort_by_count)
    for field, data in statistics['all'].items():
        array = [
            {
                'pk': pk,
                'value': packet['value'],
                'count': packet['count']
            } for pk, packet in data.items()
        ]
        array.sort(key=sort_fn)
        
        statistics['all'][field] = array
    
    for field, data in statistics['published'].items():
        array = [
            {
                'pk': pk,
                'value': packet['value'],
                'count': packet['count']
            } for pk, packet in data.items()
        ]
        array.sort(key=sort_fn)
        
        statistics['published'][field] = array
    
    return statistics

'''
    Need to change this for several reasons:
        1. We can utilise receivers and signals so we don't do this as a cronjob
        2. Big O notation for this implementation is not great
'''
def collect_statistics(request):
    user = request.user if request else None
    cache = { }

    all_entities = GenericEntity.objects.all()

    published_entities = GenericEntity.history.filter(
        publish_status=constants.APPROVAL_STATUS.APPROVED
    ) \
    .order_by('id', '-history_id') \
    .distinct('id')

    to_update = [ ]
    to_create = [ ]
    for brand in Brand.objects.all():
        collection_ids = template_utils.get_brand_collection_ids(brand.name)
        stats = collate_statistics(
            all_entities.filter(collections__overlap=collection_ids),
            published_entities.filter(collections__overlap=collection_ids),
            data_cache=cache
        )

        obj = Statistics.objects.filter(
            org=brand.name,
            type='GenericEntity',
        )

        if obj.exists():
            obj = obj.first()
            obj.stat = stats
            obj.updated_by = user
            to_update.append(obj)
            continue

        obj = Statistics(
            org=brand.name,
            type='GenericEntity',
            stat=stats,
            created_by=user
        )
        to_create.append(obj)
    
    stats = collate_statistics(
        all_entities,
        published_entities,
        data_cache=cache
    )

    obj = Statistics.objects.filter(
        org='ALL',
        type='GenericEntity',
    )

    if obj.exists():
        obj = obj.first()
        obj.stat = stats
        obj.updated_by = user
        to_update.append(obj)
    else:
        obj = Statistics(
            org='ALL',
            type='GenericEntity',
            stat=stats,
            created_by=user
        )
        to_create.append(obj)
    
    # Create / Update stat objs
    Statistics.objects.bulk_create(to_create)
    Statistics.objects.bulk_update(to_update, ['stat', 'updated_by'])
