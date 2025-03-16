from operator import or_
from functools import reduce
from django.db.models import Q, Model

import inspect

from . import gen_utils
from ..models import Brand

def is_class_method(method, expected_class):
    """
        @desc determines whether a method is:
            1. A class method
            2. A class method of a specific class
        
        Args:
            method (fn): a class method / function
            expected_class (class): a class
        
        Returns:
            (boolean) that reflects whether the fn is a method and method
            of a specific class
    """
    bound_to = getattr(method, '__self__', None)
    if not isinstance(bound_to, type):
        return False
    return inspect.ismethod(method) and bound_to is expected_class

class DataTypeFilters:
    """ Class Utilities """
    @classmethod
    def test_params(cls, expected_params, **kwargs):
        """
            @desc Tests whether kwargs incl. the expected params

            Args:
                expected_params (dict): the expected parameters

                **kwargs: the passed parameters
            
            Returns:
                A boolean reflecting the kwargs validity as described by the expected parameters arg
        """
        for key, expected in expected_params.items():
            item = kwargs.get(key)
            if not isinstance(item, expected):
                return False
        return True

    @classmethod
    def try_generate_filter(cls, desired_filter, expected_params=None, **kwargs):
        """
            @desc Tries to generate the filter query if its method is available within this class
                  and if the expected parameters are met

            Args:
                desired_filter (string): the name of the desired filter method
                
                expected_params (dict): the expected parameters
                
                **kwargs: the parameters that were provided by the calling fn and any provided
                          by ENTITY_FILTER_PARAMS[(%s)].PROPERTIES

            Returns:
                Either (a) a `None` type result if it fails or (b) the generated filter query
        """
        desired_filter = getattr(cls, desired_filter)
        if desired_filter is None or not is_class_method(desired_filter, cls):
            return None

        if isinstance(expected_params, dict) and not cls.test_params(expected_params, **kwargs):
            return None

        return desired_filter(**kwargs)

    """ Filters """
    @classmethod
    def brand_filter(cls, **kwargs):
        """
            Generates the brand-related filter query

            Args:
                request (RequestContext): the request context during this execution

                column_name (string): the name of the column to filter by

            Result:
                Either (a) a `None` type result or (b) the generated filter query
        """
        column_name = kwargs.get('column_name', None)
        if not column_name:
            return None

        request = kwargs.get('request', None)
        if request is None:
            current_brand = kwargs.get('brand_target', None)
        else:
            current_brand = getattr(request, 'BRAND_OBJECT', None)
            if not isinstance(current_brand, Model):
                current_brand = getattr(request, 'CURRENT_BRAND', None)
                if not isinstance(current_brand, str) or gen_utils.is_empty_string(current_brand):
                    current_brand = None
                else:
                    current_brand = Brand.objects.filter(name=current_brand)
                    if current_brand.exists():
                        current_brand = current_brand.first()
                    else:
                        current_brand = None

        if current_brand is None:
            return None

        target_id = current_brand.id
        source_value = kwargs.get('source_value')

        result = [ Q(**{column_name: target_id}) ]
        if isinstance(source_value, dict):
            # Modify behaviour on brand request target
            modifier = source_value.get(current_brand.name)
            if isinstance(modifier, bool) and not modifier:
                # Don't apply filter if this request target ignores brand context
                return []
            elif isinstance(modifier, str) and modifier == 'allow_null':
                # Allow null values as well as request target
                result.append(Q(**{f'{column_name}__isnull': True}))
                result = [reduce(or_, result)] 
            elif isinstance(modifier, dict):
                allowed_brands = gen_utils.parse_as_int_list(modifier.get('allowed_brands'), None)
                if isinstance(allowed_brands, list):
                    # Vary the filter if this request target desires different behaviour
                    if target_id not in allowed_brands:
                        allowed_brands = [target_id, *allowed_brands]

                    result = [ Q(**{f'{column_name}__id__in': allowed_brands}) ]

                if modifier.get('allow_null', False):
                    # Allow null values
                    result.append(Q(**{f'{column_name}__isnull': True}))
                    result = [reduce(or_, result)] 

        return result
