from uuid import UUID
from json import JSONEncoder
from functools import wraps
from typing import Pattern
from dateutil import parser as dateparser
from django.conf import settings
from django.http.response import JsonResponse
from django.core.exceptions import BadRequest
from django.http.multipartparser import MultiPartParser

import re
import time
import json
import datetime
import logging
import urllib

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


def is_empty_string(value):
    """
        Checks whether a string is empty or contains only spaces

        Args:
            value (string): the value to check
        
        Returns:
            boolean
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
                cleaned.append(result)

        if not strict_elements:
            return cleaned
        return cleaned if valid else default
    elif field_type == 'concept':
        if not isinstance(field_value, list):
            return default
        return field_value
    elif field_type == 'group': # [!] CHANGE
        if isinstance(field_value, str) and not is_empty_string(field_value):
            group = Group.objects.filter(name__iexact=field_value)
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


def measure_perf(func, show_args=False):
    """
        Helper function to estimate view execution time

        Ref @ https://stackoverflow.com/posts/62522469/revisions
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if settings.DEBUG:
            start = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            if show_args:
                print('view {} takes {:.2f} ms... \n  1. args: {}\n  2.kwargs:{}'.format(func.__name__, duration, args, kwargs))
            else:
                print('view {} takes {:.2f} ms'.format(func.__name__, duration))
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
