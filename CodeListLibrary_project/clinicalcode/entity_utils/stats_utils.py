from functools import cmp_to_key
from ..models import GenericEntity, Template, Statistics, PublishedGenericEntity, Brand
from . import template_utils, constants

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

def build_statistics(statistics, entity, field, struct, is_dynamic=False):
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
        value = None
        if 'options' in validation:
            value = template_utils.get_options_value(entity_field, struct)
        elif 'source' in validation:
            value = template_utils.get_sourced_value(entity_field, struct)
        
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
                value = template_utils.get_sourced_value(item, struct)
                if value is not None:
                    if item not in stats:
                        stats[item] = {
                            'value': value,
                            'count': 0
                        }
                    
                    stats[item]['count'] += 1
    else:
        return
    
    statistics[field] = stats

def compute_statistics(statistics, entity):
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
        build_statistics(statistics, entity, field, struct, is_dynamic=is_dynamic)

def collate_statistics(all_entities, published_entities):
    statistics = {
        'published': { },
        'all': { },
    }

    for entity in all_entities:
        compute_statistics(statistics['all'], entity)

    for entity in published_entities:
        compute_statistics(statistics['published'], entity)

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

def collect_statistics(request):
    user = request.user if request else None

    all_entities = GenericEntity.objects.all()
    published_entities = PublishedGenericEntity.objects.filter(approval_status=constants.APPROVAL_STATUS.APPROVED).order_by('-created').distinct()

    published_entities = GenericEntity.history.filter(
        id__in=list(published_entities.values_list('entity_id', flat=True)),
        history_id__in=list(published_entities.values_list('entity_history_id', flat=True))
    )

    for brand in Brand.objects.all():
        collection_ids = template_utils.get_brand_collection_ids(brand.name)
        stats = collate_statistics(
            all_entities.filter(collections__overlap=collection_ids),
            published_entities.filter(collections__overlap=collection_ids)
        )

        obj = Statistics.objects.filter(
            org=brand.name,
            type='GenericEntity',
        )

        if obj.exists():
            obj = obj.first()
            obj.stat = stats
            obj.updated_by = user
            obj.save()
        else:
            obj = Statistics.objects.create(
                org=brand.name,
                type='GenericEntity',
                stat=stats,
                created_by=user
            )
    
    stats = collate_statistics(
        all_entities,
        published_entities
    )

    obj = Statistics.objects.filter(
        org='ALL',
        type='GenericEntity',
    )

    if obj.exists():
        obj = obj.first()
        obj.stat = stats
        obj.updated_by = user
        obj.save()
    else:
        obj = Statistics.objects.create(
            org='ALL',
            type='GenericEntity',
            stat=stats,
            created_by=user
        )
