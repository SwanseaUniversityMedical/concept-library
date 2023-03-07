from functools import cmp_to_key
from ..models import GenericEntity, Template, Statistics
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

def compute_statistics(layout, entities):
    '''
        Responsible for computing the statistics for a template, across its entities
    '''
    statistics = { }
    for entity in entities:
        if not template_utils.is_data_safe(entity):
            continue
                
        for field in layout.entity_statistics.keys():
            stats = statistics[field] if field in statistics else { }
            structure = template_utils.get_layout_field(layout, field)

            if structure is None:
                continue

            field_type = structure['validation'] if 'validation' in structure else None
            field_type = field_type['type'] if 'type' in field_type else None
            if field_type is None:
                continue
            
            validation = structure.get('validation')
            entity_field = template_utils.get_entity_field(entity, field)
            if entity_field is None:
                continue

            if field_type == 'enum':
                value = None
                if 'options' in validation:
                    value = template_utils.get_options_value(entity_field, structure)
                elif 'source' in validation:
                    value = template_utils.get_sourced_value(entity_field, structure)
                
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
                        value = template_utils.get_sourced_value(item, structure)
                        if value is not None:
                            if item not in stats:
                                stats[item] = {
                                    'value': value,
                                    'count': 0
                                }
                            
                            stats[item]['count'] += 1
        
            statistics[field] = stats
        
        for field, info in constants.metadata.items():
            if 'compute_statistics' not in info:
                continue
            
            stats = statistics[field] if field in statistics else { }
            
            entity_field = template_utils.get_entity_field(entity, field)
            if entity_field is None:
                continue

            data = template_utils.get_metadata_value_from_source(entity, field)
            if data is None:
                continue
            
            for item in data:
                if item['value'] not in stats:
                    stats[item['value']] = {
                        'value': item['name'],
                        'count': 0
                    }
                
                stats[item['value']]['count'] += 1
            
            statistics[field] = stats

    sort_fn = cmp_to_key(sort_by_count)
    for field, data in statistics.items():
        array = [
            {
                'pk': pk,
                'value': packet['value'],
                'count': packet['count']
            } for pk, packet in data.items()
        ]
        array.sort(key=sort_fn)
        
        statistics[field] = array

    return statistics

def collect_statistics(request):
    '''
        Responsible for collecting the statistics for each template across each of its entities
            - Collects information relating to usage of filterable fields
    '''
    metadata_stats = { }
    layouts = Template.objects.all()
    for layout in layouts:
        if layout.entity_statistics is None or not template_utils.is_layout_safe(layout):
            continue
        
        # Layout statistics
        entities = GenericEntity.objects.filter(template=layout)
        if entities.count() < 1:
            continue
        
        stats = compute_statistics(layout, entities)
        layout.entity_statistics = stats
        layout.save_without_historical_record()
    
        # Metadata
        for field in constants.metadata:
            if field in stats:
                meta_stats = stats[field]

                if field not in metadata_stats:
                    metadata_stats[field] = meta_stats
                else:
                    for item in meta_stats:
                        obj = next((x for x in metadata_stats[field] if x['pk'] == item['pk']), None)
                        if obj is None:
                            metadata_stats[field].append(item)
                        else:
                            obj.count += item.count

    # Compile metadata
    sort_fn = cmp_to_key(sort_by_count)
    for field, array in metadata_stats.items():
        array.sort(key=sort_fn)
        metadata_stats[field] = array
    
    obj, created = Statistics.objects.get_or_create(
        org='dynamic',
        type='metadata',
        stat=metadata_stats,
        created_by=[None, request.user][request.user.is_authenticated]
    )
