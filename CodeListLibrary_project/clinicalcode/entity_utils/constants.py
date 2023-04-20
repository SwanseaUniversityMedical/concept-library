from django.contrib.auth.models import User, Group

import enum

class IterableMeta(enum.EnumMeta):
    def from_name(cls, name):
        if name in cls:
            return getattr(cls, name)
    
    def __contains__(cls, lhs):
        try:
            cls(lhs)
        except ValueError:
            return lhs in cls.__members__.keys()
        else:
            return True

class TAG_TYPE(int, enum.Enum):
    '''
        Tag types used for differentiate Collections & Tags
        within the Tag table
    '''
    TAG = 1
    COLLECTION = 2

class CLINICAL_RULE_TYPE(int, enum.Enum, metaclass=IterableMeta):
    '''
        Ruleset type for clinical concept
    '''
    INCLUDE = 1
    EXCLUDE = 2

class CLINICAL_CODE_REVIEW(int, enum.Enum, metaclass=IterableMeta):
    '''
        Review status for a code within a clinical concept
    '''
    INCLUDE = 1
    EXCLUDE = 2

class CLINICAL_CODE_SOURCE(int, enum.Enum, metaclass=IterableMeta):
    '''
        Audit source of a clinical code within a clinical concept
    '''
    CONCEPT = 1
    QUERY_BUILDER = 2
    EXPRESSION = 3
    SELECT_IMPORT = 4
    FILE_IMPORT = 5
    SEARCH_TERM = 6

class ENTITY_STATUS(int, enum.Enum):
    '''
        Status of an entity
    '''
    DRAFT = 1
    FINAL = 2

class APPROVAL_STATUS(int, enum.Enum):
    '''
        Approval status of a published entity
    '''
    ANY       = -1
    REQUESTED = 0
    PENDING   = 1
    APPROVED  = 2
    REJECTED  = 3

class OWNER_PERMISSIONS(int, enum.Enum):
    '''
        Owner permissions
    '''
    NONE = 1
    EDIT = 2
    VIEW = 3

class GROUP_PERMISSIONS(int, enum.Enum):
    '''
        Group permissions
    '''
    NONE = 1
    EDIT = 2
    VIEW = 3

class FORM_METHODS(int, enum.Enum, metaclass=IterableMeta):
    '''
        Describes form method, i.e. to create or update an entity
        Used by both template and view to modify behaviour
    '''
    CREATE = 1
    UPDATE = 2

'''
    The excepted X-Requested-With header if a fetch request is made
'''
FETCH_REQUEST_HEADER = 'XMLHttpRequest'

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
    Entity detail page related defaults
'''
DETAIL_WIZARD_ASIDE = 'components/details/aside.html'
DETAIL_WIZARD_SECTION_START = 'components/details/section/section_start.html'
DETAIL_WIZARD_SECTION_END = 'components/details/section/section_end.html'
DETAIL_WIZARD_OUTPUT_DIR = 'components/details/outputs'


'''
    Used to strip userdata from models when JSONifying them
        e.g. user account, user profile, membership
'''
USERDATA_MODELS = [str(User), str(Group)]
STRIPPED_FIELDS = ['SearchVectorField']

'''
    Describes fields that should be stripped from historical objects
'''
HISTORICAL_HIDDEN_FIELDS = [
    'id', 'history_id', 'history_date', 'history_change_reason', 'history_type', 'history_user'
]

'''
    Describes fields that should be stripped from api response
'''
API_HIDDEN_FIELDS = [
    'history_id', 'history_date', 'history_change_reason', 'history_type', 'history_user', 
    'template', 'template_data', 'template_version', 'internal_comments'
]

'''
    Describes fields that should be stripped from entity list api response
'''
ENTITY_LIST_API_HIDDEN_FIELDS = [
    'concept_information', 'definition', 'implementation'
]

'''
    [!] Note: Will be moved to a table once tooling is finished, accessible through the 'base_template_version'

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
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "string_inputbox",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True
        },
        "is_base_field": True
    },
    "definition": {
        "title": "Definition",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "textarea_markdown",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "implementation": {
        "title": "Implementation",
        "field_type": "textarea_markdown",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "publications": {
        "title": "Publications",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "publications",
        "active": True,
        "validation": {
            "type": "publication",
            "mandatory": False
        },
        "is_base_field": True
    },
    "validation": {
        "title": "Validation",
        "field_type": "textarea_markdown",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False
        },
        "is_base_field": True
    },
    "citation_requirements": {
        "title": "Citation Requirements",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "textarea_markdown",
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
        "hide_on_create": True,
        "is_base_field": True
    },
    "author": {
        "title": "Author",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "string_inputbox",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True
        },
        "is_base_field": True
    },
    "collections": {
        "title": "Collections",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "collections",
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
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "tags",
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
    "group": {
        "title": "Group",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "group_field",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": False,
            "computed": True
        },
        "is_base_field": True
    },
    "group_access": {
        "title": "Group Access",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "access_field_editable",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": True,
            "range": [1, 3]
        },
        "is_base_field": True
    },
    "world_access": {
        "title": "World Access",
        "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "field_type": "access_field",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": True,
            "range": [1, 3]
        },
        "is_base_field": True
    },
    "updated": {
        "title": "Updated",
        "field_type": "???",
        "active": True,
        "validation": {
            "type": "datetime",
            "mandatory": True,
            "computed": True
        },
        "hide_on_create": True,
        "is_base_field": True
    },
    "created_by": {
        "title": "Created By",
        "field_type": "???",
        "active": True,
        "requires_auth": True,
        "validation": {
            "type": "int", 
            "mandatory": True,
            "computed": True
        },
        "hide_on_create": True,
        "is_base_field": True
    },
    "updated_by": {
        "title": "Updated By",
        "field_type": "???",
        "active": True,
        "requires_auth": True,
        "validation": {
            "type": "int", 
            "mandatory": True,
            "computed": True
        },
        "hide_on_create": True,
        "is_base_field": True
    },
    "id": {
        "title": "ID",
        "field_type": "id",
        "active": True,
        "hide_on_create": True
    },

}

'''
    Describes the input and output presentation of common and dynamic fields
    through components and modifiers
'''
FIELD_TYPES = {
    "int": {
        "data_type": "int",
        "input_type": "inputbox",
        "output_type": "inputbox"
    },
    "date": {
        "data_type": "date",
        "input_type": "datepicker",
        "output_type": "datepicker"
    },
    "daterange": {
        "data_type": "date",
        "input_type": "datepicker_range",
        "output_type": "datepicker_range"
    },
    "string_inputbox": {
        "data_type": "string",
        "input_type": "inputbox",
        "output_type": "inputbox",
        "max_length": 250
    },
    "string_inputbox_code": {
        "data_type": "string",
        "input_type": "inputbox",
        "output_type": "inputbox",
        "max_length": 250,
        "apply_code_style": True
    },
    "textarea": {
        "data_type": "string",
        "input_type": "textarea",
        "output_type": "textarea",
        "rows": 5
    },
    "textarea_markdown": {
        "data_type": "string",
        "input_type": "markdown",
        "output_type": "markdown",
        "rows": 5,
        "display": "markdown"
    },
    "string_list_of_inputboxes": {
        "data_type": "string",
        "max_length": 250
    },
    "string_list_of_inputboxes_markdown": {
        "data_type": "string",
        "input_type": "list_of_inputboxes",
        "output_type": "list_of_inputboxes",
        "max_length": 250,
        "display": "markdown"
    },

    "enum": {
        "data_type": "int",
        "input_type": "dropdown-list",
        "output_type": "dropdown-list",
        "use_permitted_values": True
    },

    "enum_radio_badge": {
        "data_type": "int",
        "input_type": "radiobutton",
        "output_type": "radiobutton",
        "use_permitted_values": True,
        "apply_badge_style": True
    },

    "enum_dropdown_badge": {
        "data_type": "int",
        "input_type": "dropdown",
        "output_type": "dropdown",
        "use_permitted_values": True,
        "apply_badge_style": True
    },

    "concept_information": {
        "system_defined": True,
        "description": "json of concept ids/ver used in phenotype (managed by code snippet)",
        "input_type": "clinical/concept",
        "output_type": "phenotype_clinical_code_lists"
    },
    "publications": {
        "input_type": "clinical/publication",
        "output_type": "clinical/publication",
    },
    "coding_system": {
        "system_defined": True,
        "description": "list of coding system ids (calculated from phenotype concepts) (managed by code snippet)",
        "input_type": "tagbox",
        "output_type": "tagbox"
    },
    "tags": {
        "system_defined": True,
        "description": "list of tags ids (managed by code snippet)",
        "input_type": "tagbox",
        "output_type": "tagbox"
    },
    "collections": {
        "system_defined": True,
        "description": "list of collections ids (managed by code snippet)",
        "input_type": "tagbox",
        "output_type": "tagbox"
    },
    "data_sources": {
        "system_defined": True,
        "description": "list of data_sources ids (managed by code snippet)",
        "input_type": "tagbox",
        "output_type": "tagbox"
    },
    "phenoflowid": {
        "system_defined": True,
        "description": "URL for phenoflow (managed by code snippet)",
        "input_type": "phenoflowid",
        "output_type": "phenoflowid",
    },

    "group_field": {
        "input_type": "group_select",
    },
    "access_field": {
        "input_type": "access_select",
    },
    "access_field_editable": {
        "input_type": "access_select_editable",
    },

    "permissions_section":{
        "system_defined": True,
        "output_type": "permissions"
    },
    "api_section": {
        "system_defined": True,
        "output_type": "api"
    },
    "version_history_section": {
        "system_defined": True,
        "output_type": "version_history"
    },
    "id": {
        "system_defined": True,
        "output_type": "id"
    },
    "history_id": {
        "system_defined": True,
        "output_type": "history_id"
    }
}

#####################################


