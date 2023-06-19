from django.db.models import Q
from functools import cmp_to_key
from django.db import connection, connections  # , transaction
from ..models import GenericEntity, Template, Statistics, Brand
from . import template_utils, constants, model_utils

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

def transform_counted_field(data):
    sort_fn = cmp_to_key(sort_by_count)
    array = [
        {
            'pk': pk,
            'value': packet['value'],
            'count': packet['count']
        } for pk, packet in data.items()
    ]
    array.sort(key=sort_fn)
    return array

def try_get_cached_data(cache, entity, template, field, field_value, validation, struct, brand=None):
    if template is None or not isinstance(cache, dict):
        return get_field_values(field_value, validation, struct)
    
    if brand is not None:
        cache_key = f'{brand.name}__{field}__{field_value}__{template.id}__{template.template_version}'
    else:
        cache_key = f'{field}__{field_value}__{template.id}__{template.template_version}'
    
    if cache_key not in cache:
        value = get_field_values(field_value, validation, struct)
        if value is None:
            return None
        
        cache[cache_key] = value
        return value
    
    return cache[cache_key]

def build_statistics(statistics, entity, field, struct, data_cache=None, template_entity=None, brand=None):
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
        value = try_get_cached_data(data_cache, entity, template_entity, field, entity_field, validation, struct, brand=brand)
        
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
                value = try_get_cached_data(data_cache, entity, template_entity, field, item, validation, struct, brand=brand)
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

def compute_statistics(statistics, entity, data_cache=None, template_cache=None, brand=None):
    if not template_utils.is_data_safe(entity):
        return
    
    template_id = entity.template.id if entity.template is not None else None
    template_version = entity.template_version
    if template_id is None or template_version is None:
        return

    template = None
    layout = None
    if isinstance(template_cache, dict):
        cached = template_cache.get(f'{template_id}/{template_version}')
        if cached is not None:
            template = cached.get('template')
            layout = cached.get('layout')
    
    if template is None or layout is None:
        template = Template.history.filter(
            id=entity.template.id,
            template_version=entity.template_version
        ) \
        .latest_of_each() \
        .distinct()

        if not template.exists():
            return
        
        template = template.first()
        layout = template_utils.get_merged_definition(template)
        if not layout:
            return
        
        if isinstance(template_cache, dict):
            template_cache[f'{template_id}/{template_version}'] = { 'template': template, 'layout': layout }

    for field, struct in layout.get('fields').items():
        if not isinstance(struct, dict):
            continue


        build_statistics(statistics['all'], entity, field, struct, data_cache=data_cache, template_entity=template, brand=brand)

        if entity.publish_status == constants.APPROVAL_STATUS.APPROVED:
            build_statistics(statistics['published'], entity, field, struct, data_cache=data_cache, template_entity=template, brand=brand)

def collate_statistics(entities, data_cache=None, template_cache=None, brand=None):
    statistics = {
        'published': { },
        'all': { },
    }

    if brand is not None:
        collection_ids = model_utils.get_brand_collection_ids(brand.name)
        entities = entities.filter(Q(brands__overlap=[brand.id]) | Q(collections__overlap=collection_ids))

    for entity in entities:
        compute_statistics(statistics, entity, data_cache, template_cache, brand)

    for field, all_data in statistics['all'].items():
        statistics['all'][field] = transform_counted_field(all_data)

        published_data = statistics['published'].get(field)
        if published_data is not None:
            statistics['published'][field] = transform_counted_field(published_data)

    return statistics

'''
    Need to change this for several reasons:
        1. We can utilise receivers and signals so we don't do this as a cronjob
        2. Big O notation for this implementation is not great
'''
def collect_statistics(request):
    user = request.user if request else None
    cache = { }
    template_cache = { }

    all_entities = GenericEntity.objects.all()

    to_update = [ ]
    to_create = [ ]
    for brand in Brand.objects.all():
        stats = collate_statistics(
            all_entities,
            data_cache=cache,
            template_cache=template_cache,
            brand=brand
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
        data_cache=cache,
        template_cache=template_cache
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

    clear_statistics_history()


def clear_statistics_history():
    """
        leave only the last record per day for each statistics category
    """
    with connection.cursor() as cursor:
        sql = """ 
                WITH tbl AS (
                            SELECT *
                            FROM
                            (
                                SELECT 
                                    ROW_NUMBER () OVER (PARTITION BY org, type, date(history_date) ORDER BY history_date DESC) rn
                                    , *
                                FROM clinicalcode_historicalstatistics 
                            )t
                )
                DELETE FROM clinicalcode_historicalstatistics WHERE history_id NOT IN(SELECT history_id FROM tbl WHERE rn = 1) ;
             """
        cursor.execute(sql)

 