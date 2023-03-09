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
