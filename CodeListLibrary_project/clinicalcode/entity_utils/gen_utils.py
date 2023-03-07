from functools import wraps
import time

def parse_int(value, default=0):
    '''
        Attempts to parse an int from a value, if it fails to do so, returns the default value
    '''
    try:
        return int(value)
    except ValueError:
        return default

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
