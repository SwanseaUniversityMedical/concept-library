from django.conf import settings
from django.http.response import JsonResponse
from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser
from django.utils.timezone import make_aware
from functools import wraps
from dateutil import parser as dateparser
from json import JSONEncoder
from uuid import UUID

import re
import time
import json
import datetime
import urllib

from . import constants

def try_parse_form(request):
    '''
        Attempts to parse multipart/form-data from the request body
    '''
    try:
        parser = MultiPartParser(request.META, request.body, request.upload_handlers)
        post, files = parser.parse()
    except:
        return None
    else:
        return post, files

def get_request_body(request):
    '''
        Decodes the body of a request and attempts to load it as JSON
    '''
    try:
        body = request.body.decode('utf-8');
        body = json.loads(body)
        return body
    except:
        return None

def try_get_param(request, key, default=None, method='GET'):
    '''
        Attempts to get a param from a request by key
            - If a default is passed and the key isn't present, the default is returned
            - If the key is present, and the default is non-null, it tries to parse the value as the default's type
    '''
    try:
        req = getattr(request, method)
        param = req.get(key, default)
    except:
        return default
    else:
        if default is not None:
            if type(key) is not type(default):
                if isinstance(default, int):
                    return parse_int(param)
                # Add other types when necessary

    return param

def is_empty_string(value):
    '''
        Checks whether a string is empty or contains only spaces

        Args:
            value {string}: the value to check
        
        Returns:
            boolean
    '''
    if value is None:
        return True
    
    value = str(value).strip()
    return len(value) < 1 or value.isspace()

def is_fetch_request(request):
    '''
        Helper method to determine if the HTTPRequest was made with a header that matches
        the FETCH-REQUEST-HEADER

        Args:
            request {WSGIRequest}: the request object
        
        Returns:
            Boolean that reflects whether this request was made with the fetch header
    '''
    return request.headers.get('X-Requested-With') == constants.FETCH_REQUEST_HEADER

def handle_fetch_request(request, obj, *args, **kwargs):
    '''
        @desc Parses the X-Target header to determine which GET method
              to respond with
    '''
    target = request.headers.get('X-Target', None)
    if target is None or target not in obj.fetch_methods:
        raise BadRequest('No such target')
    
    try:
        response = getattr(obj, target)
    except Exception as e:
        raise BadRequest('Invalid request')
    else:
        return response 

def decode_uri_parameter(value, default=None):
    '''
        Decodes an ecoded URI parameter e.g. 'wildcard:C\d+' encoded as 'wildcard%3AC%5Cd%2B'

        Args:
            value {string}: the value to decode
            default {*}: the default value to return if this method fails
        
        Returns:
            The decoded URI component
    '''
    if value is None:
        return default
    try:
        value = urllib.parse.unquote(value)
    except:
        return default
    else:
        return value

def jsonify_response(**kwargs):
    '''
        Creates a JSON response with the given status

        Args:
            code {integer}: the status code
            status {string}: the status response
            message {string}: the message response
        
        Returns:
            A JSONResponse that matches the kwargs
    '''
    code = kwargs.get('code', 400)
    status = kwargs.get('status', 'false')
    message = kwargs.get('message', '')
    return JsonResponse({
        'status': status,
        'message': message
    }, status=code)

def try_match_pattern(value, pattern):
    '''
        Tries to match a string by a pattern
    '''
    pattern = re.compile(pattern)
    return pattern.match(value)

def is_valid_uuid(value):
    '''
        Validates value as a UUID
    '''
    try:
        uuid = UUID(value)
    except ValueError:
        return False
    
    return str(uuid) == value

def parse_int(value, default=0):
    '''
        Attempts to parse an int from a value, if it fails to do so, returns the default value
    '''
    if value is None:
        return default
    
    try:
        value = int(value)
    except ValueError:
        return default
    else:
        return value

def get_start_and_end_dates(daterange):
    '''
        Sorts a date range to [min, max] and sets their timepoints to the [start] and [end] of the day respectively

        Args:
            daterange {list[string]}: List of dates as strings (size of 2)
        
        Returns:
            A sorted {list} of datetime objects, combined with their respective start and end times
    '''
    dates = [dateparser.parse(x).date() for x in daterange]
    
    max_date = datetime.datetime.combine(max(dates), datetime.time(23, 59, 59, 999))
    min_date = datetime.datetime.combine(min(dates), datetime.time(00, 00, 00, 000))
    return [min_date, max_date]

def parse_date(value, default=0):
    '''
        Attempts to parse a date from a string value, if it fails to do so, returns the default value
    '''
    try:
        date = dateparser.parse(value)
    except:
        return default
    else:
        return date.strftime('%Y-%m-%d %H:%M:%S')

def parse_as_int_list(value):
    result = []
    for x in value.split(','):
        if parse_int(x, default=None) is not None:
            result.append(int(x))
    return result

def try_value_as_type(field_value, field_type, validation=None, default=None):
    '''
        Tries to parse a value as a given type, otherwise returns default
    '''
    if field_type == 'enum' or field_type == 'int':
        if validation is not None:
            limits = validation.get('range')
            if limits is not None and (field_value < limits[0] or field_value > limits[1]):
                return default
        return parse_int(field_value, default)
    elif field_type == 'int_array':
        if isinstance(field_value, int):
            return [field_value]
        
        if not isinstance(field_value, list):
            return default
        
        valid = True
        cleaned = [ ]
        for val in field_value:
            result = parse_int(val, None)
            if result is None:
                valid = False
                break
            if validation is not None:
                limits = validation.get('range')
                if limits is not None and (field_value < limits[0] or field_value > limits[1]):
                    valid = False
                    break
            cleaned.append(result)
        return cleaned if valid else default
    elif field_type == 'string':
        try:
            value = str(field_value) if field_value is not None else ''
            if validation is not None:
                pattern = validation.get('regex')
                mandatory = validation.get('mandatory')
                if pattern is not None and not try_match_pattern(value, pattern):
                    if mandatory:
                        return default
                    else:
                        return value if is_empty_string(value) else default
        except:
            return default
        else:
            return value
    elif field_type == 'string_array':
        if isinstance(field_value, str):
            return [field_value]
        
        if not isinstance(field_value, list):
            return default
        
        valid = True
        cleaned = [ ]
        for val in field_value:
            try:
                value = str(val)
                if validation is not None:
                    pattern = validation.get('regex')
                    if pattern is not None and not try_match_pattern(value, pattern):
                        valid = False
            except:
                valid = False
            else:
                cleaned.append(value)

            if not valid:
                break
        
        return cleaned if valid else default
    elif field_type == 'concept':
        if not isinstance(field_value, list):
            return default
        return field_value
    elif field_type == 'publication':
        if not isinstance(field_value, list):
            return default
    
    return field_value

def measure_perf(func):
    '''
        Helper function to estimate view execution time

        Ref @ https://stackoverflow.com/posts/62522469/revisions
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.DEBUG:
            start = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            print('view {} takes {:.2f} ms'.format(func.__name__, duration))
            return result
        return func(*args, **kwargs)
    return wrapper

class ModelEncoder(JSONEncoder):
    '''
        Encoder class to override behaviour of the JSON encoder to allow
        encoding of datetime objects - used to JSONify instances of a model
    '''
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
