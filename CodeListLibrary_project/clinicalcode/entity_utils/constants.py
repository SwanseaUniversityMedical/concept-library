from ..models import Tag

'''
    Hashmap is used to determine how to get values from sourced data e.g. tags, collections
    that are accounted for in the metadata portion of an entity
'''
sourced_data = {
    'collections': {
        'model': Tag,
        'query': 'id',
        'relative': 'description',
        'filter': {
            'tag_type': 2
        }
    },
    'tags': {
        'model': Tag,
        'query': 'id',
        'relative': 'description',
        'filter': {
            'tag_type': 1
        }
    },
}