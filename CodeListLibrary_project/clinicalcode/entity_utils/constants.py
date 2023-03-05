from enum import Enum
from django.conf import settings

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
    Entity render modifier(s)
        Used by entity_renderer as defaults
'''
DEFAULT_CARD = 'generic'
CARDS_DIRECTORY = 'components/search/cards'

'''
    Filter render modifier(s)
        Used by entity_renderer as defaults
'''
FILTER_DIRECTORY = 'components/search/filters'
FILTER_COMPONENTS = {
    'int': 'checkbox',
    'enum': 'checkbox',
    'int_array': 'checkbox',
    'datetime': 'datepicker',
}

'''
    Controls whether the 'Entity Type' filter is present
        - in dev, this will always be present
        - in prod, the entity filter will only be present on single search pages
'''
MIN_SINGLE_SEARCH = int(not settings.DEBUG)

'''
    Used for:
        - Hashmap is used to determine how to get values from sourced data e.g. tags, collections
          that are accounted for in the metadata portion of an entity

        - By filter to determine how and when to render metadata-related filters
'''
metadata = {
    'template': {
        'title': 'Entity Type',
        'field_type': 'int',
        'source': 'Template',
        'query': 'id',
        'relative': 'name',
        'computed': True,
        'filterable': True,
        'single_search_only': True,
    },
    'created': {
        'title': 'Date',
        'field_type': 'datetime',
        'computed': True,
        'filterable': True,
    },
    'author': {
        'title': 'Author',
        'field_type': 'string',
        'desired_input': 'inputbox',
        'searchable': True,
    },
    'collections': {
        'title': 'Collections',
        'field_type': 'int_array',
        'source': 'Tag',
        'query': 'id',
        'relative': 'description',
        'filter': {
            'tag_type': 2
        },
        'desired_input': "tagbox",
        'desired_output': "taglist",
        'compute_statistics': True,
        'filterable': True,
    },
    'tags': {
        'title': 'Tags',
        'field_type': 'int_array',
        'source': 'Tag',
        'query': 'id',
        'relative': 'description',
        'filter': {
            'tag_type': 1
        },
        'desired_input': "tagbox",
        'desired_output': "taglist",
        'compute_statistics': True,
        'filterable': True,
    },
}