from .models import *

#--------- Filter queries --------------
filter_queries = {
    'tags': 0,
    'clinical_terminologies': 0,
    'data_sources': 0,
    'coding_system_id': 1,
    'phenotype_type': 2,
    'daterange': 3
}

filter_query_model = {
    'tags': Tag,
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
    
    
    