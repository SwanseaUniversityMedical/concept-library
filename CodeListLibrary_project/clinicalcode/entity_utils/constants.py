from django.http.request import HttpRequest
from django.contrib.auth.models import User, Group

import enum


class TypeStatus:
    """ Legacy type status - needs removal during cleanup """
    Disease = 0
    Biomarker = 1
    Drug = 2
    Lifestyle_risk_factor = 3
    Musculoskeletal = 4
    Surgical_procedure = 5
    Type_status = ((Disease, 'Disease or syndrome'),
                   (Biomarker, 'Biomarker'),
                   (Drug, 'Drug'),
                   (Lifestyle_risk_factor, 'Lifestyle risk factor'),
                   (Musculoskeletal, 'Musculoskeletal'),
                   (Surgical_procedure, 'Surgical procedure'))


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
    """
        Tag types used for differentiate Collections & Tags
        within the Tag table
    """
    TAG = 1
    COLLECTION = 2


class CLINICAL_RULE_TYPE(int, enum.Enum, metaclass=IterableMeta):
    """
        Ruleset type for clinical concept
    """
    INCLUDE = 1
    EXCLUDE = 2


class CLINICAL_CODE_REVIEW(int, enum.Enum, metaclass=IterableMeta):
    """
        Review status for a code within a clinical concept
    """
    INCLUDE = 1
    EXCLUDE = 2


class CLINICAL_CODE_SOURCE(int, enum.Enum, metaclass=IterableMeta):
    """
        Audit source of a clinical code within a clinical concept
    """
    CONCEPT = 1
    QUERY_BUILDER = 2
    EXPRESSION = 3
    SELECT_IMPORT = 4
    FILE_IMPORT = 5
    SEARCH_TERM = 6
    CONCEPT_IMPORT = 7


class ENTITY_STATUS(int, enum.Enum):
    """
        Status of an entity
    """
    DRAFT = 1
    FINAL = 2


class APPROVAL_STATUS(int, enum.Enum):
    """
        Approval status of a published entity
    """
    ANY = -1
    REQUESTED = 0
    PENDING = 1
    APPROVED = 2
    REJECTED = 3


class OWNER_PERMISSIONS(int, enum.Enum):
    """
        Owner permissions
    """
    NONE = 1
    VIEW = 2
    EDIT = 3


class GROUP_PERMISSIONS(int, enum.Enum):
    """
        Group permissions
    """
    NONE = 1
    VIEW = 2
    EDIT = 3


class WORLD_ACCESS_PERMISSIONS(int, enum.Enum):
    """
        Everyone else permissions
    """
    NONE = 1
    VIEW = 2


class FORM_METHODS(int, enum.Enum, metaclass=IterableMeta):
    """
        Describes form method, i.e. to create or update an entity
        Used by both template and view to modify behaviour
    """
    CREATE = 1
    UPDATE = 2

class CASE_SIGNIFICANCE(int, enum.Enum, metaclass=IterableMeta):
    """
        Indicates whether the text can be modified by varying the case
        of characters describing a SNOMED Concept

        See: https://confluence.ihtsdotools.org/pages/viewpage.action?pageId=28739261

    """
    CL = 0 # First character can be varied; rest is cast sensitive
    CI = 1 # All characters are case insensitive
    CS = 2 # All characters are case sensitive

class ONTOLOGY_TYPES(int, enum.Enum, metaclass=IterableMeta):
    """
        Defines the ontology internal type id,
        which describes the ontology type

    """
    CLINICAL_DISEASE = 0
    CLINICAL_DOMAIN = 1
    CLINICAL_FUNCTIONAL_ANATOMY = 2

"""
    Used to define the labels for each
    known ontology type

"""
ONTOLOGY_LABELS = {
    ONTOLOGY_TYPES.CLINICAL_DOMAIN: 'Clinical Domain',
    ONTOLOGY_TYPES.CLINICAL_DISEASE: 'Clinical Disease Category (SNOMED)',
    ONTOLOGY_TYPES.CLINICAL_FUNCTIONAL_ANATOMY: 'Functional Anatomy',
}

"""
    The excepted X-Requested-With header if a fetch request is made
"""
FETCH_REQUEST_HEADER = 'XMLHttpRequest'

"""
    Entity render modifier(s)
        Used by entity_renderer as defaults
"""
DEFAULT_CARD = 'generic'
CARDS_DIRECTORY = 'components/search/cards'

"""
    Filter render modifier(s)
        Used by entity_renderer as defaults
"""
FILTER_DIRECTORY = 'components/search/filters'
FILTER_COMPONENTS = {
    'int': 'checkbox',
    'enum': 'checkbox',
    'int_array': 'checkbox',
    'datetime': 'datepicker',
}

"""
    Threshold for layout count in single search pages (__gte)
"""
MIN_SINGLE_SEARCH = 1

"""
    Order by clauses for search
"""
ORDER_BY = {
    '1': {
        'name': 'Relevance',
        'clause': 'id',
        'property': 'id',
        'order': 'asc',
    },
    '2': {
        'name': 'Created (Asc)',
        'clause': 'created',
        'property': 'created',
        'order': 'asc',
    },
    '3': {
        'name': 'Created (Desc)',
        'clause': '-created',
        'property': 'created',
        'order': 'desc',
    },
    '4': {
        'name': 'Updated (Asc)',
        'clause': 'updated',
        'property': 'updated',
        'order': 'asc',
    },
    '5': {
        'name': 'Updated (Desc)',
        'clause': '-updated',
        'property': 'updated',
        'order': 'desc',
    }
}

"""
    Page result limits for search
"""
PAGE_RESULTS_SIZE = {
    '1': 20,
    '2': 50,
    '3': 100
}

"""
    Entity creation related defaults
"""
CREATE_WIZARD_ASIDE = 'components/create/aside.html'
CREATE_WIZARD_SECTION_START = 'components/create/section/section_start.html'
CREATE_WIZARD_SECTION_END = 'components/create/section/section_end.html'
CREATE_WIZARD_INPUT_DIR = 'components/create/inputs'

"""
    Entity detail page related defaults
"""
DETAIL_WIZARD_ASIDE = 'components/details/aside.html'
DETAIL_WIZARD_SECTION_START = 'components/details/section/section_start.html'
DETAIL_WIZARD_SECTION_END = 'components/details/section/section_end.html'
DETAIL_WIZARD_OUTPUT_DIR = 'components/details/outputs'

"""
    Used to strip userdata from models when JSONifying them
        e.g. user account, user profile, membership
"""
USERDATA_MODELS = [str(User), str(Group)]
STRIPPED_FIELDS = ['SearchVectorField']

"""
    Describes fields that should be stripped from historical objects
"""
HISTORICAL_HIDDEN_FIELDS = [
    'id', 'history_id', 'history_date', 'history_change_reason', 'history_type', 'history_user'
]

"""
    Describes fields that should be stripped from api response
"""
API_HIDDEN_FIELDS = [
    'history_id', 'history_date', 'history_change_reason', 'history_type', 'history_user',
    'template', 'template_data', 'template_version', 'internal_comments'
]

"""
    Re-maps field names to user readable field names
"""
API_MAP_FIELD_NAMES = {
    'id': 'phenotype_id'
}

"""
    Describes fields that should be stripped from entity list api response
"""
ENTITY_LIST_API_HIDDEN_FIELDS = [
    'concept_information', 'definition', 'implementation'
]

"""
    ENTITY_FILTER_PARAMS

    @desc Used to define:
        - Filter types within the 'filter' field of a datatype to det. how to handle
          specific parameters e.g. 'source_by_brand' which filters objects by brand type
    
    @building Additional filters should be built such that:
        
        [key]: The name of the filter within the .filters property
            
            [filter]: (string) The name of the filter method within the DataTypeFilter found in filter_utils
            
            [properties]: (dict/null) Any additional params/properties to be passed
                          as args (global, not field specific)
            
            [field_properties] (dict/null): Params/Properties to be passed to the filter method
                                            based on which field was used to access the filter
            
                [field_name]: (dict) The field_name/properties to be passed as kwargs
            
            [expected_params]: (dict): The params expected by this method when attempting to generate
                                       filters 
"""
ENTITY_FILTER_PARAMS = {
    # the name of the filter found within a field's 'filter' key-value pair in its template/the metadata
    'source_by_brand': {
        # name of the filter to use within DataTypeFilters
        'filter': 'brand_filter',

        # e.g. some props if needed (this key can be removed but here for example usage)
        'properties': {

        },

        # how to generate the filter based on the field name
        'field_properties': {
            'tags': {
                'column_name': 'collection_brand'
            },
            'collections': {
                'column_name': 'collection_brand'
            }
        },

        # what params the fn needs to execute
        'expected_params': {
            'request': HttpRequest,
            'column_name': str
        }
    }
}

"""
    [!] All items will be appended to the list of renderables, meaning they will always appear last

    Used to define:
        - Sections and fields that relate to permissions for create interface
"""
APPENDED_SECTIONS = [
    {
        "title": "Permissions",
        "description": "Settings for sharing and collaboration.",
        "fields": ["group", "group_access", "world_access"]
    }
]

"""
    [!] All items will be appended to the list of renderables in the detail page, meaning they will always appear last

    Used to define:
        - Sections and fields that relate to permissions for the detail page
"""
DETAIL_PAGE_APPENDED_SECTIONS = [
    {
        "title": "Permissions",
        "description": "",
        "fields": ["permissions"],
        "requires_auth": True
    },
    {
        "title": "API",
        "description": "",
        "fields": ["api"]
    },
    {
        "title": "Version History",
        "description": "",
        "fields": ["version_history"]
    }
]

"""
    Used to define:
        - fields that relate to DETAIL_PAGE_APPENDED_SECTIONS for the detail page
"""
DETAIL_PAGE_APPENDED_FIELDS = {
    "permissions": {
        "title": "Permissions",
        "field_type": "permissions_section",
        "active": True,
        "hide_on_create": True
    },
    "api": {
        "title": "API",
        "field_type": "api_section",
        "active": True,
        "hide_on_create": True
    },
    "version_history": {
        "title": "Version History",
        "field_type": "version_history_section",
        "active": True,
        "hide_on_create": True
    },
    "history_id": {
        "title": "Version ID",
        "field_type": "history_id",
        "active": True,
        "hide_on_create": True
    }
}

"""
    [!] Note: Will be moved to a table once tooling is finished, accessible through the 'base_template_version'

    Used to define:
        - Hashmap for values from sourced data
        - By filter to determine metadata-related filters
"""
metadata = {
    'template': {
        'title': 'Type',
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
        },
        'ignore': True
    },
    'brands': {
        'title': 'Brand',
        'description': 'The brand that this Phenotype is related to.',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'int_array',
            'mandatory': False,
            'computed': True,
            'source': {
                'table': 'Brand',
                'query': 'id',
                'relative': 'name',
            }
        },
        "search": {
            "api": True
        },
    },
    "name": {
        "title": "Name",
        "description": "Unsurprisingly, the name of the phenotype.",
        "field_type": "string_inputbox",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True,
            "sanitise": "strict",
        },
        'is_base_field': True
    },
    "definition": {
        "title": "Definition",
        "description": "An overview of the phenotype.",
        "field_type": "textarea_markdown",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False,
            "sanitise": "markdown",
        },
        'is_base_field': True
    },
    "implementation": {
        "title": "Implementation",
        "description": "Information on how the phenotype is applied to data.",
        "field_type": "textarea_markdown",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False,
            "sanitise": "markdown",
        },
        'is_base_field': True
    },
    "publications": {
        "title": "Publications",
        "description": "Publication(s) where the phenotype was defined or has been used.",
        "field_type": "publications",
        "sort": {"key": lambda pub: 0 if pub.get('primary') == 1 else 1},
        "active": True,
        "validation": {
            "type": "publication",
            "mandatory": False
        },
        'is_base_field': True
    },
    'validation': {
        'title': 'Validation',
        'field_type': 'textarea_markdown',
        'active': True,
        'validation': {
            'type': 'string',
            'mandatory': False,
            "sanitise": "markdown",
        },
        'is_base_field': True
    },
    "citation_requirements": {
        "title": "Citation Requirements",
        "description": "A request for how this phenotype is referenced if used in other work.",
        "field_type": "citation_requirements",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": False,
            "sanitise": "markdown",
        },
        'is_base_field': True
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
        },
        'hide_on_create': True,
        'is_base_field': True
    },
    "author": {
        "title": "Author",
        "description": "List of authors who contributed to this phenotype.",
        "field_type": "string_inputbox",
        "active": True,
        "validation": {
            "type": "string",
            "mandatory": True,
            "sanitise": "strict",
        },
        'is_base_field': True
    },
    "collections": {
        "title": "Collections",
        "description": "List of content collections this phenotype belongs to.",
        "field_type": "collections",
        "active": True,
        "hydrated": True,
        "compute_statistics": True,
        "validation": {
            "type": "int_array",
            "mandatory": False,
            "source": {
                "table": "Tag",
                "query": "id",
                "relative": "description",
                "filter": {
                    "tag_type": 2,

                    ## Can be added once we det. what we're doing with brands
                    # "source_by_brand": None
                }
            }
        },
        'search': {
            'filterable': True,
            'api': True
        },
        'is_base_field': True
    },
    "tags": {
        "title": "Tags",
        "description": "Optional keywords helping to categorize this content.",
        "field_type": "tags",
        "active": True,
        "hydrated": True,
        "compute_statistics": True,
        "validation": {
            "type": "int_array",
            "mandatory": False,
            "source": {
                "table": "Tag",
                "query": "id",
                "relative": "description",
                "filter": {
                    "tag_type": 1,

                    ## Can be added once we det. what we're doing with brands
                    # "source_by_brand": None
                }
            }
        },
        'search': {
            'filterable': True,
            'api': True
        },
        'is_base_field': True
    },
    "group": {
        "title": "Group",
        "description": "The group that owns this phenotype for permissions purposes.",
        "field_type": "group_field",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": False,
            "computed": True
        },
        'is_base_field': True
    },
    "group_access": {
        "title": "Group Access",
        "description": "Optionally enable this phenotype to be viewed or edited by the group.",
        "field_type": "access_field_editable",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": True,
            "range": [1, 3]
        },
        'is_base_field': True
    },
    "world_access": {
        "title": "All authenticated users",
        "description": "Enables this phenotype to be viewed by all logged-in users of the Library (does not make it public on the web -- use the Publish action for that).",
        "field_type": "access_field",
        "active": True,
        "validation": {
            "type": "int",
            "mandatory": True,
            "range": [1, 3]
        },
        'is_base_field': True
    },
    'updated': {
        'title': 'Updated',
        'field_type': '???',
        'active': True,
        'validation': {
            'type': 'datetime',
            'mandatory': True,
            'computed': True
        },
        'hide_on_create': True,
        'is_base_field': True
    },
    'created_by': {
        'title': 'Created By',
        'field_type': '???',
        'active': True,
        'requires_auth': True,
        'validation': {
            'type': 'int',
            'mandatory': True,
            'computed': True
        },
        'hide_on_create': True,
        'is_base_field': True
    },
    'updated_by': {
        'title': 'Updated By',
        'field_type': '???',
        'active': True,
        'requires_auth': True,
        'validation': {
            'type': 'int',
            'mandatory': True,
            'computed': True
        },
        'hide_on_create': True,
        'is_base_field': True
    },
    'id': {
        'title': 'ID',
        'field_type': 'id',
        'active': True,
        'hide_on_create': True,
        'ignore': True
    },
}

"""
    Describes the input and output presentation of common and dynamic fields
    through components and modifiers
"""
FIELD_TYPES = {
    'int': {
        'data_type': 'int',
        'input_type': 'inputbox',
        'output_type': 'inputbox'
    },
    'date': {
        'data_type': 'date',
        'input_type': 'datepicker',
        'output_type': 'datepicker'
    },
    'daterange': {
        'data_type': 'date',
        'input_type': 'daterange_selector',
        'output_type': 'datepicker_range'
    },
    'string_inputbox': {
        'data_type': 'string',
        'input_type': 'inputbox',
        'output_type': 'inputbox'
    },
    'string_inputbox_code': {
        'data_type': 'string',
        'input_type': 'inputbox',
        'output_type': 'inputbox',
        'apply_code_style': True
    },
    'textarea': {
        'data_type': 'string',
        'input_type': 'textarea',
        'output_type': 'textarea',
        'rows': 5
    },
    'textarea_markdown': {
        'data_type': 'string',
        'input_type': 'markdown',
        'output_type': 'markdown',
        'rows': 5
    },
    'string_list_of_inputboxes': {
        'data_type': 'string'
    },
    'string_list_of_inputboxes_markdown': {
        'data_type': 'string',
        'input_type': 'list_of_inputboxes',
        'output_type': 'list_of_inputboxes'
    },

    'citation_requirements': {
        'data_type': 'string',
        'input_type': 'markdown',
        'output_type': 'citation_requirements'
    },

    'enum': {
        'data_type': 'int',
        'input_type': 'dropdown-list',
        'output_type': 'dropdown-list'
    },

    'grouped_enum': {
        'data_type': 'int',
        'input_type': 'grouped_enum',
        'output_type': 'radiobutton',
        'apply_badge_style': True
    },

    'ontology': {
        'input_type': 'generic/ontology',
        'output_type': 'generic/ontology'
    },

    'enum_radio_badge': {
        'data_type': 'int',
        'input_type': 'radiobutton',
        'output_type': 'radiobutton',
        'apply_badge_style': True
    },

    'enum_dropdown_badge': {
        'data_type': 'int',
        'input_type': 'dropdown',
        'output_type': 'dropdown',
        'apply_badge_style': True
    },

    'concept_information': {
        'system_defined': True,
        'description': 'json of concept ids/ver used in phenotype (managed by code snippet)',
        'input_type': 'clinical/concept',
        'output_type': 'phenotype_clinical_code_lists'
    },
    'publications': {
        'input_type': 'clinical/publication',
        'output_type': 'clinical/publication',
    },
    'endorsements': {
        'input_type': 'clinical/endorsement',
        'output_type': 'clinical/endorsement',
    },
    'trials': {
        'input_type': 'clinical/trial',
        'output_type': 'clinical/trial',
    },
    'coding_system': {
        'system_defined': True,
        'description': 'list of coding system ids (calculated from phenotype concepts) (managed by code snippet)',
        'input_type': 'tagbox',
        'output_type': 'tagbox'
    },
    'tags': {
        'system_defined': True,
        'description': 'list of tags ids (managed by code snippet)',
        'input_type': 'tagbox',
        'output_type': 'tagbox'
    },
    'collections': {
        'system_defined': True,
        'description': 'list of collections ids (managed by code snippet)',
        'input_type': 'tagbox',
        'output_type': 'tagbox'
    },
    'data_sources': {
        'system_defined': True,
        'description': 'list of data_sources ids (managed by code snippet)',
        'input_type': 'tagbox',
        'output_type': 'data_source'
    },
    'phenoflowid': {
        'system_defined': True,
        'description': 'URL for phenoflow (managed by code snippet)',
        'input_type': 'inputbox',
        'output_type': 'phenoflowid',
    },
    'group_field': {
        'input_type': 'group_select',
    },
    'access_field': {
        'input_type': 'access_select',
    },
    'access_field_editable': {
        'input_type': 'access_select_editable',
    },
    'permissions_section': {
        'system_defined': True,
        'output_type': 'permissions'
    },
    'api_section': {
        'system_defined': True,
        'output_type': 'api'
    },
    'version_history_section': {
        'system_defined': True,
        'output_type': 'version_history'
    },
    'id': {
        'system_defined': True,
        'output_type': 'id'
    },
    'history_id': {
        'system_defined': True,
        'output_type': 'history_id'
    },
    'string_inputlist': {
        'input_type': 'string_inputlist',
        'output_type': 'string_inputlist',
    },
    'url_list': {
        'input_type': 'generic/url_list',
        'output_type': 'generic/url_list',
    },
    'source_reference': {
        'data_type': 'string',
        'input_type': 'inputbox',
        'output_type': 'source_reference'
    },
}
