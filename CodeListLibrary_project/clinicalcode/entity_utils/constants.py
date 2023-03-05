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

'''

'''
base_entity_fields = {
    "name": {
        "title": "Name",
        "active": True,
        "field_type": "string",
        "desired_input": "inputbox",
        "validation": {
            "mandatory": True
        }
    },
    "author": {
        "title": "Author",
        "active": True,
        "field_type": "string",
        "desired_input": "inputbox",
        "validation": {
            "mandatory": True
        }
    },
    "collections": {
        "title": "Collections",
        "active": True,
        "field_type": "int_array",
        "desired_input": "tagbox",
        "desired_output": "taglist",
        "validation": {
            "mandatory": False
        }
    },
    "tags": {
        "title": "Tags",
        "active": True,
        "field_type": "int_array",
        "desired_input": "tagbox",
        "desired_output": "taglist",
        "validation": {
            "mandatory": False
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
    "created": {
        "title": "Created",
        "active": True,
        "field_type": "datetime",
        "validation": {
            "mandatory": True
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
