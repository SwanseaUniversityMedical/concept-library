import json
from functools import cmp_to_key
from ..models import GenericEntity, Template
from ..entity_utils import view_utils

'''
    Used to sort filter statistics in descending order
'''
def sort_by_count(a, b):
    count0 = a['count']
    count1 = b['count']
    if count0 < count1:
        return 1
    elif count0 > count1:
        return -1
    return 0

'''
    Responsible for computing the statistics for a template, across its entities
'''
def compute_statistics(layout, entities):
    statistics = { }
    for entity in entities:
        if not view_utils.is_data_safe(entity):
            continue
        
        for field in layout.entity_statistics.keys():
            stats = statistics[field] if field in statistics else { }
            structure = view_utils.get_layout_field(layout, field)

            field_type = structure['field_type'] if 'field_type' in structure else None
            if field_type is None:
                continue

            entity_field = view_utils.get_entity_field(entity, field)
            if entity_field is None:
                continue

            if field_type == 'enum':
                value = None
                if 'options' in structure:
                    value = view_utils.get_options_value(entity_field, structure)
                elif 'source' in structure:
                    value = view_utils.get_sourced_value(entity_field, structure)
                
                if value is not None:
                    if entity_field not in stats:
                        stats[entity_field] = {
                            'value': value,
                            'count': 0
                        }
                    
                    stats[entity_field]['count'] += 1
            elif field_type == 'int_array':
                if 'source' in structure:
                    for item in entity_field:
                        value = view_utils.get_sourced_value(item, structure)
                        if value is not None:
                            if item not in stats:
                                stats[item] = {
                                    'value': value,
                                    'count': 0
                                }
                            
                            stats[item]['count'] += 1
        
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

'''
    Responsible for collecting the statistics for each template across each of its entities
        - Collects information relating to usage of filterable fields
'''
def collect_statistics():
    layouts = Template.objects.all()
    for layout in layouts:
        if layout.entity_statistics is None or not view_utils.is_layout_safe(layout):
            continue
        
        entities = GenericEntity.objects.filter(template=layout)
        if entities.count() < 1:
            continue
        
        stats = compute_statistics(layout, entities)
        layout.entity_statistics = stats
        layout.save()
