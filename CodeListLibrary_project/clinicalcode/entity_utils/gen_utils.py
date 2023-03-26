from django.http.response import JsonResponse
from functools import wraps
from dateutil import parser
from json import JSONEncoder

import time
import datetime
import urllib

from . import constants

def is_empty_string(value):
    '''
        Checks whether a string is empty or contains only spaces

        Args:
            value {string}: the value to check
        
        Returns:
            boolean
    '''
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

def parse_date(value, default=0):
    '''
        Attempts to parse a date from a string value, if it fails to do so, returns the default value
    '''
    try:
        date = parser.parse(value)
    except:
        return default
    else:
        return date.strftime('%Y-%m-%d')

def measure_perf(func):
    '''
        Helper function to estimate view execution time

        Ref @ https://stackoverflow.com/posts/62522469/revisions
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        print('view {} takes {:.2f} ms'.format(func.__name__, duration))
        return result
    return wrapper

class ModelEncoder(JSONEncoder):
    '''
        Encoder class to override behaviour of the JSON encoder to allow
        encoding of datetime objects - used to JSONify instances of a model
    '''
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
