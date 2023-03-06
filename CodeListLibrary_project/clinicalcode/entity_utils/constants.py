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
        'active': True,
        'field_type': 'int',
        'source': 'Template',
        'query': 'id',
        'relative': 'name',
        'computed': True,
        'filterable': True,
        'single_search_only': True,
        "validation": {
            "mandatory": True
        }
    },
    "name": {
        "title": "Name",
        "active": True,
        "field_type": "string",
        "desired_input": "inputbox",
        "validation": {
            "mandatory": True
        }
    },
    "definition": {
        "title": "Definition",
        "active": True,
        "field_type": "string",
        "desired_input": "markdown",
        "desired_output": "markdown",
        "validation": {
            "mandatory": False
        }
    },
    "implementation": {
        "title": "Implementation",
        "active": True,
        "field_type": "string",
        "desired_input": "markdown",
        "desired_output": "markdown",
        "validation": {
            "mandatory": False
        }
    },
    "publications": {
        "title": "Publications",
        "active": True,
        "field_type": "string_array",
        "desired_input": "inputbox",
        "validation": {
            "mandatory": False
        }
    },
    "validation": {
        "title": "Validation",
        "active": True,
        "field_type": "string",
        "desired_input": "markdown",
        "desired_output": "markdown",
        "hide_if_empty": True,
        "validation": {
            "mandatory": False
        }
    },
    "citation_requirements": {
        "title": "Citation Requirements",
        "active": True,
        "field_type": "textarea",
        "desired_input": "inputbox",
        "hide_if_empty": True,
        "validation": {
            "mandatory": False
        }
    },
    'created': {
        'title': 'Date',
        'active': True,
        'field_type': 'datetime',
        'computed': True,
        'filterable': True,
        "validation": {
            "mandatory": True
        }
    },
    'author': {
        'title': 'Author',
        'active': True,
        'field_type': 'string',
        'desired_input': 'inputbox',
        'searchable': True,
        "validation": {
            "mandatory": True
        }
    },
    'collections': {
        'title': 'Collections',
        'active': True,
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
        "validation": {
            "mandatory": False
        }
    },
    'tags': {
        'title': 'Tags',
        'active': True,
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
        "validation": {
            "mandatory": False
        }
    },
    "updated": {
        "title": "Updated",
        "active": True,
        "field_type": "datetime",
        "validation": {
            "mandatory": True
        }
    },
    "created_by": {
        "title": "Created By",
        "active": True,
        "field_type": "string",
        "validation": {
            "mandatory": True
        },
        "requires_auth": True
    },
    "updated_by": {
        "title": "Updated By",
        "active": True,
        "field_type": "string",
        "validation": {
            "mandatory": True
        },
        "requires_auth": True
    }
}
