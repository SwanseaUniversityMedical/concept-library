from enum import Enum

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
    Threshold for layout count in single search pages (__gte)
'''
MIN_SINGLE_SEARCH = 1

'''
    Order by clauses for search
'''
ORDER_BY = {
    '1': {
        'name': 'Relevance',
        'clause': 'id'
    },
    '2': {
        'name': 'Created (Desc)',
        'clause': 'created'
    },
    '3': {
        'name': 'Created (Asc)',
        'clause': '-created'
    },
    '4': {
        'name': 'Updated (Desc)',
        'clause': 'updated'
    },
    '5': {
        'name': 'Updated (Asc)',
        'clause': '-updated'
    }
}

'''
    Page result limits for search
'''
PAGE_RESULTS_SIZE = {
    '1': 20,
    '2': 50,
    '3': 100
}

'''
    Used for:
        - Hashmap is used to determine how to get values from sourced data e.g. tags, collections
          that are accounted for in the metadata portion of an entity

        - By filter to determine how and when to render metadata-related filters
'''
metadata = {
    'template': {
        'title': 'Entity Type',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'int',
            'mandatory': True,
            'computed': True,
            'source': {
                'table': 'Template',
                'query': 'id',
                'relative': 'name'
            }
        },
        'search': {
            'filterable': True,
            'single_search_only': True,
        }
    },
    'name': {
        'title': 'Name',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': True
        }
    },
    'definition': {
        'title': 'Definition',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': False
        }
    },
    'implementation': {
        'title': 'Implementation',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': False
        }
    },
    'publications': {
        'title': 'Publications',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string_array',
            'mandatory': False
        }
    },
    'validation': {
        'title': 'Validation',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': False
        }
    },
    'citation_requirements': {
        'title': 'Citation Requirements',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': False
        }
    },
    'created': {
        'title': 'Date',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'datetime',
            'mandatory': True,
            'computed': True
        },
        'search': {
            'filterable': True
        }
    },
    'author': {
        'title': 'Author',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': True
        }
    },
    'collections': {
        'title': 'Collections',
        'field_type': '???',
        'active': True,
        'compute_statistics': True,
        'validation': {
            'type': 'int_array',
            'mandatory': False,
            'source': {
                'table': 'Tag',
                'query': 'id',
                'relative': 'description',
                'filter': {
                    'tag_type': 2
                }
            }
        },
        'search': {
            'filterable': True,
            'api': True
        }
    },
    'tags': {
        'title': 'Tags',
        'field_type': '???',
        'active': True,
        'compute_statistics': True,
        'validation': {
            'type': 'int_array',
            'mandatory': False,
            'source': {
                'table': 'Tag',
                'query': 'id',
                'relative': 'description',
                'filter': {
                    'tag_type': 1
                }
            }
        },
        'search': {
            'filterable': True,
            'api': True
        }
    },
    'updated': {
        'title': 'Updated',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'datetime',
            'mandatory': True
        }
    },
    'created_by': {
        'title': 'Created By',
        'field_type': '???',
        'active': True,
        'requires_auth': True,
        'validation': {
            'type': 'int', 
            'mandatory': True
        }
    },
    'updated_by': {
        'title': 'Updated By',
        'field_type': '???',
        'active': True,
        'requires_auth': True,
        'validation': {
            'type': 'int', 
            'mandatory': True
        }
    }
}
