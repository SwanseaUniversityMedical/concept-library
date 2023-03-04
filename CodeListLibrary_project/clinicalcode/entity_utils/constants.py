from enum import Enum

from ..models import Tag

class APPROVAL_STATUS(int, Enum):
    '''
        
    '''
    REQUESTED = 0
    PENDING   = 1
    APPROVED  = 2
    REJECTED  = 3

class GROUP_PERMISSIONS(int, Enum):
    '''

    '''
    NONE = 1
    VIEW = 2
    EDIT = 3

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