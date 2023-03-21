from functools import wraps
from dateutil import parser
from json import JSONEncoder

import time
import datetime

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
    """
        Helper function to estimate view execution time

        Ref @ https://stackoverflow.com/posts/62522469/revisions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        print('view {} takes {:.2f} ms'.format(func.__name__, duration))
        return result
    return wrapper

class ModelEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
