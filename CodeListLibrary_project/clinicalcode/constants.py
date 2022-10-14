from .models import *

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
Type_status = ((Disease, 'Disease or syndrome '),
               (Biomarker,'Biomarker'),(Drug,'Drug'),
               (Lifestyle_risk_factor,'Lifestyle risk factor'),
               (Musculoskeletal,'Musculoskeletal'),
               (Surgical_procedure,'Surgical procedure'))


PWS_ATTRIBUTE_TYPES = ['INT', 'FLOAT', 'STRING']
PWS_ATTRIBUTE_TYPE_DATATYPE = {
    'INT': int,
    'FLOAT': float,
    'STRING': str,
}