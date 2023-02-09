from .models import (Tag, CodingSystem, DataSource)

#------------ pagination lims ----------
page_size_limits = [20, 50, 100]
#---------------------------------------

#--------- Filter queries --------------
filter_queries = {
    'tags': 0,
    'collections': 0,
    'clinical_terminologies': 0,
    'data_sources': 0,
    'coding_system_id': 1,
    'phenotype_type': 2,
    'workingset_type': 3,
    'daterange': 4
}

filter_query_model = {
    'tags': Tag,
    'collections': Tag,
    'clinical_terminologies': CodingSystem,
    'coding_system_id': CodingSystem,
    'data_sources': DataSource
}

concept_order_queries = {
    'Relevance': ' ORDER BY id, history_id DESC ',
    'Created (Desc)': ' ORDER BY created DESC ',
    'Created (Asc)': ' ORDER BY created ASC ',
    'Last Updated (Desc)': ' ORDER BY modified DESC ',
    'Last Updated (Asc)': ' ORDER BY modified ASC ',
    'Published Date (Desc)': ' ORDER BY publish_date DESC ',
    'Published Date (Asc)': ' ORDER BY publish_date ASC '
}
concept_order_default = list(concept_order_queries.values())[0]
#---------------------------------------

# Component types
LOGICAL_TYPE_INCLUSION = 1
LOGICAL_TYPE_EXCLUSION = 2

LOGICAL_TYPES = (
    (LOGICAL_TYPE_INCLUSION, 'Add codes'),
    (LOGICAL_TYPE_EXCLUSION, 'Remove codes'),
)
    

# Regex types    
REGEX_TYPE_SIMPLE = 1
REGEX_TYPE_POSIX = 2

REGEX_TYPE_CHOICES = ((REGEX_TYPE_SIMPLE, 'simple (% only)'),
                      (REGEX_TYPE_POSIX, 'POSIX regex'))


# Publish approval
APPROVAL_REQUESTED = 0
PENDING = 1
APPROVED = 2
REJECTED = 3
APPROVED_STATUS = ((APPROVAL_REQUESTED, 'Requested'), 
                   (PENDING, 'Pending'),
                   (APPROVED, 'Approved'), 
                   (REJECTED, 'Rejected'))
    
    
Disease = 0
Biomarker = 1
Drug = 2
Lifestyle_risk_factor = 3
Musculoskeletal = 4
Surgical_procedure = 5
Type_status = ((Disease, 'Disease or syndrome'),
               (Biomarker,'Biomarker'),
               (Drug,'Drug'),
               (Lifestyle_risk_factor,'Lifestyle risk factor'),
               (Musculoskeletal,'Musculoskeletal'),
               (Surgical_procedure,'Surgical procedure'))


PWS_ATTRIBUTE_TYPES = ['INT', 'FLOAT', 'STRING']
PWS_ATTRIBUTE_TYPE_DATATYPE = {
    'INT': int,
    'FLOAT': float,
    'STRING': str,
}


#####################################
#####################################
### Dynamic Templates  ###
#####################################
#####################################

# Status
ENTITY_STATUS_DRAFT = 1
ENTITY_STATUS_FINAL = 2
ENTITY_STATUS = (
    (ENTITY_STATUS_DRAFT, 'Draft'),
    (ENTITY_STATUS_FINAL, 'Final'),
)
#-----------------------------------

# Layout
LAYOUT_CLINICAL_CODED_PHENOTYPE = 1
LAYOUT_CONCEPT = 2
LAYOUT_WORKINGSET = 3
LAYOUT_NLP_PHENOTYPE = 4
LAYOUT_GENOMiC_PHENOTYPE = 5

ENTITY_LAYOUT = ((LAYOUT_CLINICAL_CODED_PHENOTYPE, 'Clinical-Coded Phenotype'), 
                 (LAYOUT_CONCEPT, 'Concept'), 
                 (LAYOUT_WORKINGSET, 'Working Set'), 
                 (LAYOUT_NLP_PHENOTYPE, 'NLP Phenotype'),
                 (LAYOUT_GENOMiC_PHENOTYPE, 'Genomic Phenotype')
                 )

#-----------------------------------

# Permissions
NONE = 1
VIEW = 2
EDIT = 3
PERMISSION_CHOICES = ((NONE, 'No Access'), (VIEW, 'View'), (EDIT, 'Edit'))

PERMISSION_CHOICES_WORLD_ACCESS = ((NONE, 'No Access'), (VIEW, 'View'))

#-----------------------------------
# types of clinical-coded phenotypes
BIOMARKER = 1
DISEASE_OR_SYNDROME = 2
DRUG = 3
LIFESTYLE_RISK_FACTOR = 4
MUSCULOSKELETAL = 5
SURGICAL_PROCEDURE = 6
TYPE_CLINICAL_CODED_PHENOTYPE = ((BIOMARKER, 'Biomarker'),
                                 (DISEASE_OR_SYNDROME, 'Disease or syndrome'),
                                 (DRUG, 'Drug'),
                                 (LIFESTYLE_RISK_FACTOR, 'Lifestyle risk factor'),
                                 (MUSCULOSKELETAL, 'Musculoskeletal'),
                                 (SURGICAL_PROCEDURE, 'Surgical procedure')
                                 )

#-----------------------------------
FIELD_TYPE ={
    "int": {
        "data_type": "int",
        "input_type": "textinput"
    },
    "date": {
        "data_type": "date",
        "input_type": "date_picker"
    },
    "char_inputbox": {
        "data_type": "char",
        "input_type": "textinput",
        "max_length": 250
    },
    "textarea": {
        "data_type": "char",
        "input_type": "textarea",
        "rows": 5
    },
    "textarea_markdown": {
        "data_type": "char",
        "input_type": "textarea",
        "rows": 5,
        "display": "markdown"
    },
    "char_list_of_inputboxes": {
        "data_type": "char",
        "input_type": "list_of_inputboxes",
        "max_length": 250,
    },
    "char_list_of_inputboxes_markdown": {
        "data_type": "char",
        "input_type": "list_of_inputboxes",
        "max_length": 250,
        "display": "markdown"
    },


    "concept_informations": {
        "system_defined": True,
        "description": "json of concept ids/ver used in phenotype (managed by code snippet)"
    },
    "clinical_terminologies": {
        "system_defined": True,
        "description": "list of coding system ids (calculated from phenotype concepts) (managed by code snippet)"
    },
    "tags": {
        "system_defined": True,
        "description": "list of tags ids (managed by code snippet)"
    },
    "collections": {
        "system_defined": True,
        "description": "list of collections ids (managed by code snippet)"
    },
    "data_sources": {
        "system_defined": True,
        "description": "list of data_sources ids (managed by code snippet)"
    },


    "enum": {
        "data_type": "int",
        "input_type": "dropdown-list",
        "use_permitted_values": True
    }

} 

#####################################


