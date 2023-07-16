import inspect

from . import model_utils

def is_class_method(method, expected_class):
    '''
        @desc determines whether a method is:
            1. A class method
            2. A class method of a specific class
        
        Args:
            method {fn}: a class method / function
            expected_class {class}: a class
        
        Returns:
            {boolean} that reflects whether the fn is a method and method
            of a specific class
    '''
    bound_to = getattr(method, '__self__', None)
    if not isinstance(bound_to, type):
        return False
    return inspect.ismethod(method) and bound_to is expected_class

class DataTypeFilters:
    ''' Class Utilities '''
    @classmethod
    def test_params(cls, expected_params, **kwargs):
        '''
            @desc Tests whether kwargs incl. the expected params

            Args:
                expected_params {dict}: the expected parameters

                **kwargs: the passed parameters
            
            Returns:
                {boolean} that reflects whether the kwargs incl. the expected
                parameters
        '''
        for key, expected in expected_params.items():
            item = kwargs.get(key)
            if not isinstance(item, expected):
                return False
        return True

    @classmethod
    def try_generate_filter(cls, desired_filter, expected_params=None, **kwargs):
        '''
            @desc Tries to generate the filter query if its method is available within this class
                  and if the expected parameters are met

            Args:
                desired_filter {string}: the name of the desired filter method
                
                expected_params {dict}: the expected parameters
                
                **kwargs: the parameters that were provided by the calling fn and any provided
                          by ENTITY_FILTER_PARAMS[{%s}].PROPERTIES

            Returns:
                Either (a) a null result if it fails or (b) the generated filter query
        '''
        desired_filter = getattr(cls, desired_filter)
        if desired_filter is None or not is_class_method(desired_filter, cls):
            return
        
        if isinstance(expected_params, dict) and not cls.test_params(expected_params, **kwargs):
            return
        
        return desired_filter(**kwargs)

    ''' Filters '''
    @classmethod
    def brand_filter(cls, request, column_name):
        '''
            @desc Generates the brand-related filter query

            Args:
                request {RequestContext}: the request context during this execution

                column_name {string}: the name of the column to filter by

            Result:
                Either (a) a null result or (b) the generated filter query
        '''
        current_brand = model_utils.try_get_brand(request)
        if current_brand is None:
            return
        
        return {
            f'{column_name}': current_brand.id 
        }
