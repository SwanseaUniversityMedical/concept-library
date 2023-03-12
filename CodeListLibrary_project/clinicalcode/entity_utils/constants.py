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
FILTER_SERVICE_FILE = 'js/clinicalcode/redesign/services/filterService.js'
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
        'name': 'Created (Asc)',
        'clause': 'created'
    },
    '3': {
        'name': 'Created (Desc)',
        'clause': '-created'
    },
    '4': {
        'name': 'Updated (Asc)',
        'clause': 'updated'
    },
    '5': {
        'name': 'Updated (Desc)',
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
    Entity creation related defaults
'''
CREATE_WIZARD_ASIDE = 'components/create/aside.html'
CREATE_WIZARD_SECTION_START = 'components/create/section/section_start.html'
CREATE_WIZARD_SECTION_END = 'components/create/section/section_end.html'
CREATE_WIZARD_INPUT_DIR = 'components/create/inputs'

'''
    [!] Note: Could be moved once we determine who has responsibility to create/edit FieldTypes.json
              and where it should be located
    
    Used to define:
        - Hashmap whose value reflects how to display template-related data
        - By ./create and ./detail pages for field components, how to organise the page, and so forth
'''
field_types = {
    "create_sections": [
        {
            "title": "Definition",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "fields": ["name", "definition", "author", "event_date_range", "sex", "type", "tags", "collections", "data_sources"]
        },
        {
            "title": "Concepts",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "fields": ["concept_information"]
        },
        {
            "title": "Publication",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "fields": ["publications"]
        },
        {
            "title": "Validation",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "fields": ["validation"],
        },
        {
            "title": "Permissions",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "fields": ["group"]
        }
    ],
    "components": {
        "name": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "inputbox",
        },
        "definition": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "textarea"
        },
        "author": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "inputbox"
        },
        "event_date_range": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "datepicker_range"
        },
        "sex": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "radiobutton"
        },
        "type": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "dropdown"
        },
        "tags": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "tagbox"
        },
        "collections": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "tagbox"
        },
        "data_sources": {
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "input": "tagbox"
        },
        "concept_information": {
            "input": "clinical/concept"
        },
        "publications": {
            "input": "clinical/publication"
        },
        "validation": {
            "input": "clinical/validation"
        },
        "group": {
            "input": "group_select"
        }
    }
}


'''
    Used to define:
        - Hashmap for values from sourced data
        - By filter to determine metadata-related filters
'''
metadata = {
    "template": {
        "title": "Entity Type",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": True,
            "computed": True,
            "source": {
                "table": "Template",
                "query": "id",
                "relative": "name"
            }
        },
        "search": {
            "filterable": True,
            "single_search_only": True,
        }
    },
    "name": {
        "title": "Name",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True
        },
        "is_base_field": True
    },
    "definition": {
        "title": "Definition",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "implementation": {
        "title": "Implementation",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "publications": {
        "title": "Publications",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string_array",
            "mandatory": False
        },
        "is_base_field": True
    },
    "validation": {
        "title": "Validation",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "citation_requirements": {
        "title": "Citation Requirements",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "created": {
        "title": "Date",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "datetime",
            "mandatory": True,
            "computed": True
        },
        "search": {
            "filterable": True
        },
        "is_base_field": True
    },
    "author": {
        "title": "Author",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True
        },
        "is_base_field": True
    },
    "collections": {
        "title": "Collections",
        "field_type": "???",
        "active": True,
        "compute_statistics": True,
        "validation": {
            "type": "int_array",
            "mandatory": False,
            "source": {
                "table": "Tag",
                "query": "id",
                "relative": "description",
                "filter": {
                    "tag_type": 2
                }
            }
        },
        "search": {
            "filterable": True,
            "api": True
        },
        "is_base_field": True
    },
    "tags": {
        "title": "Tags",
        "field_type": "???",
        "active": True,
        "compute_statistics": True,
        "validation": {
            "type": "int_array",
            "mandatory": False,
            "source": {
                "table": "Tag",
                "query": "id",
                "relative": "description",
                "filter": {
                    "tag_type": 1
                }
            }
        },
        "search": {
            "filterable": True,
            "api": True
        },
        "is_base_field": True
    },
    "updated": {
        "title": "Updated",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "datetime",
            "mandatory": True
        },
        "is_base_field": True
    },
    "created_by": {
        "title": "Created By",
        "field_type": "???",
        "active": True,
        "requires_auth": True,
        "validation": {
            "type": "int", 
            "mandatory": True
        },
        "is_base_field": True
    },
    "updated_by": {
        "title": "Updated By",
        "field_type": "???",
        "active": True,
        "requires_auth": True,
        "validation": {
            "type": "int", 
            "mandatory": True
        },
        "is_base_field": True
    },
}