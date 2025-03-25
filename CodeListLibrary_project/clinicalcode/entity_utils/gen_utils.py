from uuid import UUID
from json import JSONEncoder
from typing import Pattern
from dateutil import parser as dateparser
from functools import wraps
from django.http import HttpRequest
from django.apps import apps
from django.conf import settings
from django.db.models import Q, Model
from django.core.cache import cache
from django.http.response import JsonResponse
from rest_framework.request import Request
from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser

import re
import time
import json
import urllib
import inspect
import hashlib
import logging
import datetime

from cll.settings import Symbol
from . import constants, sanitise_utils

logger = logging.getLogger(__name__)

def is_datetime(x):
    """
        Legacy method from ./utils.py

        Desc:
            - "Checks if a parameter can be parsed as a datetime"
    """
    try:
        dateparser(x)
    except ValueError:
        return False
    else:
        return True


def is_float(x):
    """
        Legacy method from ./utils.py

        Desc:
            - "Checks if a param can be parsed as a float"
    """
    try:
        a = float(x)
    except ValueError:
        return False
    else:
        return True


def is_int(x):
    """
        Legacy method from ./utils.py

        Desc:
            - "Checks if a number is an integer"
    """
    try:
        a = float(x)
        b = int(a)
    except ValueError:
        return False
    else:
        return a == b


def clean_str_as_db_col_name(txt):
    """
        Legacy method from ./utils.py

        Desc:
            - "Clean string to be valid column name"
    """
    s = txt.strip()
    s = s.replace(' ', '_').replace('.', '_').replace('-', '_')

    if is_int(s[0]):
        s = '_' + s

    s = re.sub('_+', '_', s)
    return re.sub('[^A-Za-z0-9_]+', '', s)


def try_parse_form(request):
    """
        Attempts to parse multipart/form-data from the request body
    """
    try:
        parser = MultiPartParser(request.META, request.body, request.upload_handlers)
        post, files = parser.parse()
    except:
        return None
    else:
        return post, files


def get_request_body(request):
    """
        Decodes the body of a request and attempts to load it as JSON
    """
    try:
        body = request.body.decode('utf-8')
        body = json.loads(body)
        return body
    except:
        return None


def try_get_param(request, key, default=None, method='GET'):
    """
        Attempts to get a param from a request by key
            - If a default is passed and the key isn't present, the default is returned
            - If the key is present, and the default is non-null, it tries to parse the value as the default's type
    """
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
                elif isinstance(default, str):
                    return str(param)
                # Add other types when necessary

    return param


def parse_model_field_query(model, params, ignored_fields=None, default=None):
    """
        Attempts to parse ORM query fields & desired values for the specified model given the request parameters

        Args:
            model                                       (Model): the model from which to build the ORM query
            params         (dict[str, str]|Request|HttpRequest): either the query parameter dict or the request assoc. with this query
            ignored_fields                          (list[str]): optionally specify a list of fields on the given model to ignore when building the query; defaults to `None`
            default                                       (Any): optionally specify the default value to return on failure; defaults to `None`
        
        Returns:
            Either (a) a `dict[str, Any]` containing the ORM query, or (b) the specified `default` param if no query could be resolved
    """
    ignored_fields = ignored_fields if isinstance(ignored_fields, list) else None

    if not inspect.isclass(model) or not issubclass(model, Model):
        return default

    if isinstance(params, Request):
        params = params.query_params
    elif isinstance(params, HttpRequest):
        params = params.GET.dict()

    if not isinstance(params, dict):
        return default

    result = None
    for field in model._meta.get_fields():
        field_name = field.name
        if ignored_fields is not None and field_name in ignored_fields:
            continue

        value = params.get(field_name)
        if value is None:
            continue

        typed = field.get_internal_type()
        is_fk = typed == 'ForeignKey' and field.auto_created and (field.many_to_one or field.one_to_one)
        if is_fk:
            typed = field.target_field.get_internal_type()

        query = None
        match typed:
            case 'AutoField' | 'IntegerField' | 'BigAutoField' | 'BigIntegerField':
                if not is_empty_string(value):
                    value = parse_as_int_list(value, default=None)
                    length = len(value) if isinstance(value, list) else 0
                    if length == 1:
                        value = value[0]
                        query = f'{field_name}__eq'
                    elif length > 1:
                        value = value
                        query = f'{field_name}__in'
                    else:
                        value = None
            case 'CharField' | 'TextField':
                if not is_empty_string(value):
                    if is_fk:
                        values = value.split(',')
                        if len(values) > 1:
                            value = values
                            query = f'{field_name}__contained_by'

                    if query is None:
                        value = str(value)
                        query = f'{field_name}__icontains'
            case _:
                pass

        if query is not None and value is not None:
            if not isinstance(result, dict):
                result = { }
            result[query] = value

    return result if isinstance(result, dict) else default


def is_empty_string(value):
    """
        Checks whether a string is empty or contains only spaces

        Args:
            value (string): the value to check
        
        Returns:
            A (bool) reflecting whether the value is an empty string and/or contains only spaces
    """
    if value is None:
        return True

    value = str(value).strip()
    return len(value) < 1 or value.isspace()


def is_fetch_request(request):
    """
        Helper method to determine if the HTTPRequest was made with a header that matches
        the FETCH-REQUEST-HEADER

        Args:
            request (WSGIRequest): the request object
        
        Returns:
            Boolean that reflects whether this request was made with the fetch header
    """
    return request.headers.get('X-Requested-With') == constants.FETCH_REQUEST_HEADER


def handle_fetch_request(request, obj, *args, **kwargs):
    """
        @desc Parses the X-Target header to determine which GET method
              to respond with
    """
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
    """
        Decodes an ecoded URI parameter e.g. 'wildcard:C\d+' encoded as 'wildcard%3AC%5Cd%2B'

        Args:
            value (string): the value to decode
            default (*): the default value to return if this method fails
        
        Returns:
            The decoded URI component
    """
    if value is None:
        return default
    try:
        value = urllib.parse.unquote(value)
    except:
        return default
    else:
        return value


def jsonify_response(**kwargs):
    """
        Creates a JSON response with the given status

        Args:
            code (integer): the status code
            status (string): the status response
            message (string): the message response
        
        Returns:
            A JSONResponse that matches the kwargs
    """
    code = kwargs.get('code', 400)
    status = kwargs.get('status', 'false')
    message = kwargs.get('message', '')
    return JsonResponse({
            'status': status,
            'message': message
    }, status=code)


def try_match_pattern(value, pattern, flags=re.IGNORECASE):
    """
        Tries to match a string by a pattern
    """
    if not isinstance(value, str):
        return False

    if isinstance(pattern, (str, Pattern)):
        return re.match(pattern, value)
    elif isinstance(pattern, list):
        res = None
        try:
            for x in pattern:
                if not isinstance(x, (str, Pattern)):
                    continue

                res = re.match(x, value, flags)
                if res:
                    break
        except Exception as e:
            logger.warning(f'Failed to test Pattern<value: {value}, re: {x}> with err: {e}')
            res = None
        finally:
            return res

    logger.warning(f'Expected Pattern to be of (str, Pattern) type but got Arg<type: {type(pattern)}, value: {pattern}>')
    return False


def is_valid_uuid(value):
    """
        Validates value as a UUID
    """
    try:
        uuid = UUID(value)
    except ValueError:
        return False

    return str(uuid) == value


def parse_int(value, default=None):
    """
        Attempts to parse an int from a value, if it fails to do so, returns the default value
    """
    if isinstance(value, int):
        return value

    if value is None:
        return default

    try:
        value = int(value)
    except:
        return default
    else:
        return value


def get_start_and_end_dates(daterange):
    """
        Sorts a date range to [min, max] and sets their timepoints to the [start] and [end] of the day respectively

        Args:
            daterange (list[string]): List of dates as strings (size of 2)
        
        Returns:
            A sorted (list) of datetime objects, combined with their respective start and end times
    """
    dates = [dateparser.parse(x).date() for x in daterange]

    max_date = datetime.datetime.combine(max(dates), datetime.time(23, 59, 59, 999))
    min_date = datetime.datetime.combine(min(dates), datetime.time(00, 00, 00, 000))
    return [min_date, max_date]


def parse_date(value, default=None):
    """
        Attempts to parse a date from a string value, if it fails to do so, returns the default value
    """
    try:
        date = dateparser.parse(value)
    except:
        return default
    else:
        return date.strftime('%Y-%m-%d %H:%M:%S')


def parse_as_int_list(value, default=Symbol('EmptyList')):
    """
        Coerces the given value into a list of integers

        Args:
            value (str|list|int): some value to coerce

            default (any|None): the default value to return if this method fails; defaults to an empty list `[]`

        Returns:
            Either...
                a) If successful: a list of integers
                b) On failure: the specified default value

    """
    if isinstance(default, Symbol):
        default = []

    if isinstance(value, str):
        if value.find(','):
            return [int(x) for x in value.split(',') if parse_int(x, default=None) is not None]

        value = parse_int(value, default=None)
        if value is not None:
            return [value]
    elif isinstance(value, list):
        return [int(x) for x in value if parse_int(x, default=None) is not None]
    elif isinstance(value, int):
        return [value]

    return default

def parse_prefixed_references(values, acceptable=None, pattern=None, transform=None, should_trim=False, default=None):
    """
        Attempts to parse prefixed references from a list object. Note that this
        is primarily used for Ontology-like source mapping(s).
        
        Non-prefixed and/or unmapped items will fallback to parsing each element
        as an integer-like value.

        Args:
            values           (list): the request context of the form
            acceptable  (dict|None): a dict in which each key describes a prefix and its corresponding value specifies how to parse said prefix
            pattern   (string|None): a regex pattern to separate individual values into [prefix, value] pairs (optional)
            transform (string|None): a regex pattern to manipulate results (e.g. creating `alt_codes` with no dot formatting) (optional)
            should_trim   (boolean): specifies whether the input value should be trimmed
            default             (*): the default value to return if this method fails

        Returns:
            Either...
                a) If successful: a dict specifying each of the matched values for the mapping(s) and a `__root__` key describing the parsed integer values (if any)
                b) On failure: the specified default value
    """
    if not isinstance(values, list):
        return None

    if not isinstance(acceptable, dict):
        acceptable = None

    if not is_empty_string(pattern):
        try:
            pattern = re.compile(pattern)
        except:
            return default
    else:
        pattern = None

    should_trim = not not should_trim
    if not is_empty_string(transform):
        try:
            transform = re.compile(transform)
        except:
            transform = None
    else:
        transform = None

    root = []
    prefixed = {}
    for value in values:
        if isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            root.append(value)
            continue
        elif is_empty_string(value):
            continue

        if should_trim:
            value = value.strip()

        matched = pattern.findall(value) if pattern is not None else None
        if matched is not None and len(matched) > 0:
            matched = matched.pop(0)

            prefix = matched[0].lower()
            target = matched[1]
            if acceptable is not None:
                if not prefix in acceptable:
                    target = None
                else:
                    expected = acceptable.get(prefix).get('type')
                    if not is_empty_string(expected):
                        target = try_value_as_type(target, expected, default=None)

            if target is not None:
                if not prefix in prefixed:
                    prefixed.update({ prefix: [] })
                prefixed.get(prefix).append(target)

                if isinstance(target, str) and transform:
                    alt_target = transform.sub('', target)
                    if not is_empty_string(alt_target) and target != alt_target:
                        prefixed.get(prefix).append(alt_target)
                continue

        value = parse_int(value, default=None)
        if value is not None:
            root.append(value)

    result = { '__root__': root }
    if len(prefixed) > 0:
        result |= prefixed

    return result


def try_value_as_type(
        field_value,
        field_type,
        validation=None,
        loose_coercion=False,
        strict_elements=True,
        default=None
    ):
    """
        Tries to parse a value as a given type, otherwise returns default

        Args:
            field_value (any): some input to consider

            field_type (str): the type that 

            validation (dict): a dict describing how the given value should be validated; defaults to `None`

            loose_coercion (boolean): optionally specify whether to attempt to loosely coerce the value; defaults to `False`

            strict_elements (boolean): optionally specify whether all items in a list should be validated (not appended otherwise); defaults to `True`

            default (any|None): optionally specify the default return value; defaults to `None`

        Returns:
            Either (a) the default value if invalid
                or (b) if validated as some type given the inputs, the typed value
    """
    if field_type == 'enum' or field_type == 'int':
        field_value = parse_int(field_value, default)
        if field_value is not None and validation is not None:
            limits = validation.get('range')
            if isinstance(limits, list) and isinstance(field_type, int) and (field_value < limits[0] or field_value > limits[1]):
                return default
        return field_value
    elif field_type == 'int_array':
        if isinstance(field_value, int):
            return [field_value]

        if loose_coercion:
            if strict_elements and isinstance(field_value, str):
                if field_value.find(','):
                    field_value = field_value.split(',')
                else:
                    field_value = [int(field_value)] if parse_int(field_value, None) is not None else None
            else:
                field_value = parse_as_int_list(field_value, default=None)

        if not isinstance(field_value, list):
            return default

        if validation is not None:
            source = validation.get('source', None)
            references = source.get('references', False) if isinstance(source, dict) else None
            if references:
                mapping = references.get('mapping', None)
                pattern = references.get('pattern', None)
                transform = references.get('transform', None)
                should_trim = references.get('trim', False)
                return parse_prefixed_references(field_value, mapping, pattern, transform, should_trim, default)

        valid = True
        cleaned = []
        limits = validation.get('range') if validation is not None and isinstance(validation.get('range'), list) else []
        if not isinstance(limits, list) or len(limits) < 2:
            limits = None

        for val in field_value:
            result = parse_int(val, None)
            if result is None:
                valid = False
            elif limits is not None and (result < limits[0] or result > limits[1]):
                valid = False
            else:
                valid = True

            if not valid and strict_elements:
                break
            elif valid:
                cleaned.append(result)

        if not strict_elements:
            return cleaned
        return cleaned if valid else default
    elif field_type == 'code':
        try:
            value = str(field_value) if field_value is not None else ''
            if validation is not None:
                sanitiser = validation.get('sanitise')
                if sanitiser is not None:
                    empty = is_empty_string(value)
                    value = sanitise_utils.sanitise_value(value, method=sanitiser, default=None)
                    if value is None or (is_empty_string(value) and not empty):
                        return default

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
    elif field_type == 'string':
        try:
            value = str(field_value) if field_value is not None else ''
            if validation is not None:
                sanitiser = validation.get('sanitise')
                if sanitiser is not None:
                    empty = is_empty_string(value)
                    value = sanitise_utils.sanitise_value(value, method=sanitiser, default=None)
                    if value is None or (is_empty_string(value) and not empty):
                        return default

                length = validation.get('length')
                if isinstance(length, int):
                    # treat as max length
                    charlen = len(value)
                    if charlen > length:
                        return default
                elif isinstance(length, list) and len(length) >= 2:
                    # treat as range
                    charlen = len(value)
                    if charlen < length[0] or charlen > length[1]:
                        return default

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
        if loose_coercion:
            if isinstance(field_value, str):
                if field_value.find(','):
                    field_value = field_value.split(',')
                else:
                    field_value = [field_value]
            else:
                field_value = str(field_value) if field_value is not None else ''
        else:
            if isinstance(field_value, str):
                return [field_value]

        if not isinstance(field_value, list):
            return default

        valid = True
        cleaned = []

        length = None
        pattern = None
        sanitiser = None

        if validation is not None:
            length = validation.get('length') \
                if (isinstance(length, list) and len(length) >= 2) or isinstance(length, int) \
                else None

            pattern = validation.get('regex') if isinstance(pattern, (list, str, Pattern)) else None

            sanitiser = validation.get('sanitise') if isinstance(validation.get('sanitise'), str) else None

        for val in field_value:
            try:
                value = str(val)
                if sanitiser is not None:
                    empty = is_empty_string(value)
                    value = sanitise_utils.sanitise_value(value, method=sanitiser, default=None)
                    if value is None or (is_empty_string(value) and not empty):
                        valid = False

                if valid and length is not None:
                    if isinstance(length, int):
                        charlen = len(value)
                        if charlen > length:
                            valid = False
                    elif isinstance(length, list):
                        charlen = len(value)
                        if charlen < length[0] or charlen > length[1]:
                            valid = False

                if valid and pattern is not None and not try_match_pattern(value, pattern):
                    valid = False
            except:
                valid = False

            if not valid and strict_elements:
                break
            elif valid:
                cleaned.append(value)

        if not strict_elements:
            return cleaned
        return cleaned if valid else default
    elif field_type == 'concept':
        if not isinstance(field_value, list):
            return default
        return field_value
    elif field_type == 'organisation':
        if isinstance(field_value, str) and not is_empty_string(field_value):
            org = apps.get_model(app_label='clinicalcode', model_name='Organisation')
            org = org.objects.filter(Q(name__iexact=field_value) | Q(slug__iexact=field_value))
            return org.first().pk if org.exists() else default
        elif isinstance(field_value, int):
            return field_value
        return default
    elif field_type == 'group': # [!] Delete in future
        if isinstance(field_value, str) and not is_empty_string(field_value):
            group = apps.get_model(app_label='clinicalcode', model_name='Group')
            group = group.objects.filter(name__iexact=field_value)
            return group.first().pk if group.exists() else default
        elif isinstance(field_value, int):
            return field_value
        return default
    elif field_type == 'url_list':
        if not isinstance(field_value, list):
            return default

        if len(field_value) < 1:
            return field_value

        composition = validation.get('composition') if validation is not None else None

        title_test = composition.get('title') \
            if composition and isinstance(composition.get('title'), dict) \
            else None

        url_test = composition.get('url') \
            if composition and isinstance(composition.get('url'), dict) \
            else None

        valid = True
        for val in field_value:
            if not isinstance(val, dict):
                valid = False
                break

            if title_test is not None:
                title = try_value_as_type(val.get('title'), 'string', title_test, default=None)
                if title is None:
                    valid = False
                    break
            else:
                title = sanitise_utils.sanitise_value(val.get('title'), method='strict', default=None)
                if not title or not isinstance(title, str) or is_empty_string(title):
                    valid = False
                    break

            if url_test is not None:
                url = try_value_as_type(val.get('url'), 'string', url_test, default=None)
                if url is None:
                    valid = False
                    break
            else:
                url = sanitise_utils.sanitise_value(val.get('url'), method='strict', default=None)
                if url is not None and not isinstance(url, str):
                    valid = False
                    break

        return field_value if valid else default
    elif field_type == 'publication':
        if not isinstance(field_value, list):
            return default

        if len(field_value) < 1:
            return field_value

        valid = True
        for val in field_value:
            if not isinstance(val, dict):
                valid = False
                break

            details = val.get('details')
            empty = is_empty_string(details)

            details = sanitise_utils.sanitise_value(details, method='strict', default=None)
            if not details or not isinstance(details, str) or (is_empty_string(details) and empty):
                valid = False
                break

            doi = sanitise_utils.sanitise_value(val.get('doi'), method='strict', default=None)
            if doi is not None and not isinstance(doi, str):
                valid = False
                break

            if 'primary' in val:
                primary = val.get('primary')
                if not isinstance(primary, int) and primary not in (0, 1):
                    valid = False
                    break

        return field_value if valid else default

    return field_value


def cache_resultset(
    cache_age=3600,
    cache_params=False,
    cache_key=None,
    cache_prefix='rs__',
    cache_suffix='__ctrg',
    debug_metrics=False
):
    """
        Tries to parse a value as a given type, otherwise returns default

        .. Note::
            - The `debug_metrics` parameter will only log _perf._ metrics if global `DEBUG` setting is active;
            - Cache prefixes & suffixes are ignored if the `cache_key` param is specified;
            - Returned values will not be cached if the optionally specified `cache_age` param is less than `1s`;
            - Cache results are _NOT_ varied by arguments unless the `cache_params` param is flagged `True`.

        Args:
            cache_age      (int): optionally specify the max age, in seconds, of the callable's cached result; defaults to `3600`
            cache_params  (bool): optionally specify whether to vary the cache key by the given parameters; defaults to `False`
            cache_key      (str): optionally specify the key pair name; defaults to `None` - non-string type cache keys are built using the `cache_prefix` and `cache_suffix` args unless specified
            cache_prefix   (str): optionally specify the cache key prefix; defaults to `rs__`
            cache_suffix   (str): optionally specify the cache key suffix; defautls to `__ctrg`
            debug_metrics (bool): optionally specify whether to log performance metrics; defaults to `False`

        Returns:
            The cached value, if applicable
    """
    cache_age = max(cache_age if isinstance(cache_age, int) else 0, 0)
    has_cache_key = isinstance(cache_key, str) and not is_empty_string(cache_key)
    debug_metrics = debug_metrics and settings.DEBUG

    def _cache_resultset(func):
        """
        Cache resultset decorator

        Args:
            func (Callable): some callable function to decorate

        Returns:
            A (Callable) decorator
        """
        if not has_cache_key:
            cache_key = f'{cache_prefix}{func.__name__}'

        @wraps(func)
        def wrapper(*args, **kwargs):
            if cache_age < 1:
                return func(*args, **kwargs)

            perf_start = None
            perf_hashed = None
            perf_duration = None
            if debug_metrics:
                perf_start = time.time()

            if cache_params:
                key = hashlib.md5(repr([args, kwargs]).encode('utf-8'), usedforsecurity=False).hexdigest()
                key = '%s__%s%s' % (cache_key, key, '' if has_cache_key else cache_suffix)

                perf_hashed = time.time() if debug_metrics else None
            else:
                key = cache_key

            resultset = cache.get(key)
            if not isinstance(resultset, dict):
                resultset = func(*args, **kwargs)
                resultset = { 'value': resultset, 'timepoint': time.time() }
                cache.set(key, resultset, cache_age)

            resultset = resultset.get('value')

            if debug_metrics:
                perf_duration = (time.time() - perf_start)*1000
                if perf_hashed:
                    perf_hashed = (perf_hashed - perf_start)*1000
                    logger.info(
                        ('CachedCallable<func: \'%s\', max-age: %ds> {\n' + \
                        '  - Key: \'%s\'\n' + \
                        '  - Perf:\n' + \
                        '    - Hashed: %.2f ms\n' + \
                        '    - Duration: %.2f ms\n' + \
                        '}') % (func.__name__, cache_age, key, perf_hashed, perf_duration)
                    )
                else:
                    logger.info(
                        ('CachedCallable<func: \'%s\', max-age: %ds> {\n' + \
                        '  - Key: \'%s\'\n' + \
                        '  - Duration: %.2f ms\n' + \
                        '}') % (func.__name__, cache_age, key, perf_duration)
                    )

            return resultset

        return wrapper
    return _cache_resultset


def measure_perf(func):
    """
        Helper decorator to estimate view execution time

        Args:
            func (Callable): some callable function to decorate

        Returns:
            A (Callable) decorator
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.DEBUG:
            start = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            logger.info('View<name: \'%s\', duration: %.2f ms> {\n  1. args: %s\n  2. kwargs: %s\n}\n' % (func.__name__, duration, args, kwargs))
            return result
        return func(*args, **kwargs)

    return wrapper


class ModelEncoder(JSONEncoder):
    """
        Encoder class to override behaviour of the JSON encoder to allow
        encoding of datetime objects - used to JSONify instances of a model
    """

    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
