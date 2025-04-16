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
from django.utils.translation import gettext_lazy as _
from django.http.multipartparser import MultiPartParser

import re
import time
import json
import uuid
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
    if x is None:
        return False
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
    """Attempts to parse multipart/form-data from the request body"""
    try:
        parser = MultiPartParser(request.META, request.body, request.upload_handlers)
        post, files = parser.parse()
    except:
        return None
    else:
        return post, files


def get_request_body(request):
    """Decodes the body of a request and attempts to load it as JSON"""
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
            value (str): the value to check
        
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
    """Parses the X-Target header to determine which GET method to respond with"""
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
            value (str): the value to decode
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
            code    (int): the status code
            status  (str): the status response
            message (str): the message response
        
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
        Validates value as a `UUID`

        Args:
            value (Any): some value to evaluate

        Returns:
            A (bool) value specifying whether this value is a valid `UUID`
    """
    if isinstance(value, uuid.UUID):
        return True
    elif value is None or not isinstance(value, (str, int)):
        return False

    typed = 'int' if isinstance(value, int) else 'hex'
    try:
        uid = uuid.UUID(**{typed: value})
    except ValueError:
        return False

    return getattr(uid, typed, None) == value


def parse_uuid(value, default=None):
    """
        Attempts to parse a `UUID` from a value, if it fails to do so, returns the default value

        Args:
            value   (Any): some value to parse
            default (Any): optionally specify the default return value if the given value is both (1) not an `UUID` and (2) cannot be cast (or coerced) to a `UUID`; defaults to `None`

        Returns:
            A (uuid.UUID) value, if applicable; otherwise returns the specified default value
    """
    if isinstance(value, uuid.UUID):
        return value
    elif value is None or not isinstance(value, (str, int)):
        return default

    typed = 'int' if isinstance(value, int) else 'hex'
    try:
        uid = uuid.UUID(**{typed: value})
    except ValueError:
        return default

    return value if getattr(uid, typed, None) == value else default


def parse_int(value, default=None):
    """
        Attempts to parse an `int` from a value, if it fails to do so, returns the default value

        Args:
            value   (Any): some value to parse
            default (Any): optionally specify the default return value if the given value is both (1) not an `int` and (2) cannot be cast to a `int`; defaults to `None`

        Returns:
            A (int) value, if applicable; otherwise returns the specified default value
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


def parse_float(value, default=None):
    """
        Attempts to parse a `float` from a value, if it fails to do so, returns the default value

        Args:
            value   (Any): some value to parse
            default (Any): optionally specify the default return value if the given value is both (1) not a `float` and (2) cannot be cast to a `float`; defaults to `None`

        Returns:
            A (float) value, if applicable; otherwise returns the specified default value
    """
    if isinstance(value, float):
        return value

    if value is None:
        return default

    try:
        value = float(value)
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

    if (not inspect.isclass(model) or not issubclass(model, Model)) and not isinstance(model, Model):
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
        is_fk = typed == 'ForeignKey' and (field.many_to_one or field.one_to_one)
        if is_fk:
            typed = field.target_field.get_internal_type()

        query = None
        match typed:
            case 'AutoField' | 'SmallAutoField' | 'BigAutoField':
                if isinstance(value, str):
                    if is_empty_string(value):
                        continue

                    value = parse_as_int_list(value, default=None)
                    length = len(value) if isinstance(value, list) else 0
                    if length == 1:
                        value = value[0]
                        query = f'{field_name}'
                    elif length > 1:
                        value = value
                        query = f'{field_name}__in'
                    else:
                        value = None
                elif isinstance(value, (int, float, complex)) and not isinstance(value, bool):
                    try:
                        value = int(value)
                        query = f'{field_name}'
                    except:
                        pass
                elif isinstance(value, list):
                    arr = [int(x) for x in value if is_int(x, default=None)]
                    if isinstance(arr, list) and len(arr) > 1:
                        value = arr
                        query = f'{field_name}__in'

            case 'BooleanField':
                if isinstance(value, str):
                    if is_empty_string(value):
                        continue
                    value = value.lower() in ('y', 'yes', 't', 'true', 'on', '1')

                if isinstance(value, bool):
                    value = value
                    query = f'{field_name}'

            case 'SmallIntegerField' | 'PositiveSmallIntegerField' | \
                 'IntegerField'      | 'PositiveIntegerField'      | \
                 'BigIntegerField'   | 'PositiveBigIntegerField':
                if isinstance(value, str):
                    if is_empty_string(value):
                        continue

                    if value.find(','):
                        arr = [int(x) for x in value.split(',') if parse_int(x, default=None) is not None]
                        if isinstance(arr, list) and len(arr) > 1:
                            value = arr
                            query = f'{field_name}__in'
                    elif value.find(':'):
                        bounds = [int(x) for x in value.split(':') if is_int(x)]
                        if isinstance(bounds, list) and len(bounds) >= 2:
                            value = [min(bounds), max(bounds)]
                            query = f'{field_name}__range'

                    if query is None:
                        value = try_value_as_type(value, 'int')
                        query = f'{field_name}'
                elif isinstance(value, (int, float, complex)) and not isinstance(value, bool):
                    try:
                        value = int(value)
                        query = f'{field_name}'
                    except:
                        pass
                elif isinstance(value, list):
                    arr = [int(x) for x in value if is_int(x, default=None)]
                    if isinstance(arr, list) and len(arr) > 1:
                        value = arr
                        query = f'{field_name}__in'

            case 'FloatField' | 'DecimalField':
                if isinstance(value, str):
                    if is_empty_string(value):
                        continue

                    if value.find(','):
                        arr = [float(x) for x in value.split(',') if is_float(x)]
                        if isinstance(arr, list) and len(arr) > 1:
                            value = arr
                            query = f'{field_name}__in'
                    elif value.find(':'):
                        bounds = [float(x) for x in value.split(':') if is_float(x)]
                        if isinstance(bounds, list) and len(bounds) >= 2:
                            value = [min(bounds), max(bounds)]
                            query = f'{field_name}__range'

                    if query is None:
                        value = float(value) if is_float(value) else None
                        query = f'{field_name}'
                elif isinstance(value, (int, float, complex)) and not isinstance(value, bool):
                    try:
                        value = float(value)
                        query = f'{field_name}'
                    except:
                        pass
                elif isinstance(value, list):
                    arr = [float(x) for x in value if is_float(x, default=None)]
                    if isinstance(arr, list) and len(arr) > 1:
                        value = arr
                        query = f'{field_name}__in'

            case 'SlugField' | 'CharField' | 'TextField':
                value = str(value)
                if is_fk:
                    values = value.split(',')
                    if len(values) > 1:
                        value = values
                        query = f'{field_name}__contained_by'

                if query is None:
                    value = str(value)
                    query = f'{field_name}__icontains'

            case 'UUIDField' | 'EmailField'     | \
                 'URLField'  | 'FilePathField':
                value = str(value)
                if value.find(','):
                    values = value.split(',')
                    if len(values) > 1:
                        value = values
                        query = f'{field_name}__contained_by'

                if query is None:
                    value = value
                    query = f'{field_name}__exact'

            case 'DateField':
                if is_empty_string(value):
                    continue

                try:
                    bounds = [dateparser.parse(x).date() for x in value.split(':')] if value.find(':') else None
                    if bounds and len(bounds) >= 2:
                        value = [min(value), max(value)]
                        query = f'{field_name}__range'

                    if query is None:
                        value = dateparser.parse(value).date()
                        query = f'{field_name}'
                except:
                    value = None

            case 'TimeField':
                if is_empty_string(value):
                    continue

                try:
                    bounds = [dateparser.parse(x).time() for x in value.split(':') if dateparser.parse(x).time()] if value.find(':') else None
                    if bounds and len(bounds) >= 2:
                        value = [min(bounds), max(bounds)]
                        query = f'{field_name}__range'

                    if query is None:
                        value = dateparser.parse(value).time()
                        query = f'{field_name}'
                except:
                    value = None

            case 'DateTimeField':
                if is_empty_string(value):
                    continue

                try:
                    bounds = [dateparser.parse(x) for x in value.split(':')] if value.find(':') else None
                    if bounds and len(bounds) >= 2:
                        value = [datetime.datetime.combine(x, datetime.time(23, 59, 59, 999)) if not x.time() else x for x in bounds]
                        value = [min(value), max(value)]
                        query = f'{field_name}__range'

                    if query is None:
                        value = dateparser.parse(value)
                        value = datetime.datetime.combine(value, datetime.time(23, 59, 59, 999)) if not value.time() else value
                        query = f'{field_name}'
                except:
                    value = None

            case _:
                pass

        if query is not None and value is not None:
            if not isinstance(result, dict):
                result = { }
            result[query] = value

    return result if isinstance(result, dict) else default


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
    elif field_type in constants.NUMERIC_NAMES:
        field_value = parse_float(field_value, default)
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
    elif field_type == 'int_range':
        properties = validation.get('properties') if validation is not None else None

        fmin = None
        fmax = None
        if isinstance(field_value, dict):
            fmin = parse_int(field_value.get('min'), default)
            fmax = parse_int(field_value.get('max'), default)
        elif isinstance(field_value, list) and len(field_value) >= 2 and all(is_int(x) for x in field_value):
            fmin = parse_int(field_value[0], default)
            fmax = parse_int(field_value[1], default)

        if fmin is None or fmax is None:
            return default

        if properties is not None:
            vrange = properties.get('range')
            if isinstance(vrange, list) and len(vrange) >= 2 and all(is_int(x) for x in vrange):
                vmin = min(vrange[0], vrange[1])
                vmax = max(vrange[0], vrange[1])
            else:
                vmin = parse_int(properties.get('min'), default)
                vmax = parse_int(properties.get('max'), default)

        if vmin is not None and vmax is not None:
            min_valid = fmin >= vmin
            max_valid = fmax <= vmax
            if not min_valid or not max_valid:
                return default
        return field_value
    elif field_type.endswith('_range') and field_type.split('_')[0] in constants.NUMERIC_NAMES:
        properties = validation.get('properties') if validation is not None else None

        fmin = None
        fmax = None
        if isinstance(field_value, dict):
            fmin = parse_float(field_value.get('min'), default)
            fmax = parse_float(field_value.get('max'), default)
        elif isinstance(field_value, list) and len(field_value) >= 2 and all(is_float(x) for x in field_value):
            fmin = parse_float(field_value[0], default)
            fmax = parse_float(field_value[1], default)

        if fmin is None or fmax is None:
            return default

        if properties is not None:
            vrange = properties.get('range')
            if isinstance(vrange, list) and len(vrange) >= 2 and all(is_float(x) for x in vrange):
                vmin = min(vrange[0], vrange[1])
                vmax = max(vrange[0], vrange[1])
            else:
                vmin = parse_float(properties.get('min'), default)
                vmax = parse_float(properties.get('max'), default)

        if vmin is not None and vmax is not None:
            min_valid = fmin >= vmin
            max_valid = fmax <= vmax
            if not min_valid or not max_valid:
                return default
        return field_value
    elif field_type == 'ci_interval':
        if not isinstance(field_value, dict):
            return default

        lower = parse_float(field_value.get('lower'), None)
        upper = parse_float(field_value.get('upper'), None)
        probability = parse_float(field_value.get('probability'), None)

        if lower is None or upper is None or probability is None:
            return default

        probability = min(max(probability, 0), 100)
        return {
            'lower': lower,
            'upper': upper,
            'probability': probability,
        }
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
    elif field_type == 'indicator_calculation':
        if not isinstance(field_value, dict):
            return default
        
        keys = set(field_value.keys())
        expected_keys = set(['description', 'numerator', 'denominator'])
        if not keys.issubset(expected_keys):
            return default

        valid = False
        output = { }
        for key, val in field_value.items():
            if not isinstance(val, str) or is_empty_string(val):
                continue

            value = sanitise_utils.sanitise_value(val, method='markdown', default=None)
            if value is None or is_empty_string(value):
                continue
            else:
                output[key] = value
                valid = True

        return output if valid else default
    elif field_type == 'contact':
        if not isinstance(field_value, list):
            default
        
        if len(field_value) < 1:
            return field_value
        
        valid = True
        for val in field_value:
            if not isinstance(val, dict):
                valid = False
                break
            
            name = sanitise_utils.sanitise_value(val.get('name'), method='strict', default=None)
            if not name or not isinstance(name, str) or is_empty_string(name):
                valid = False
                break

            email = sanitise_utils.sanitise_value(val.get('email'), method='strict', default=None)
            if not email or not isinstance(email, str) or is_empty_string(email):
                valid = False
                break
        return field_value if valid else default
    elif field_type == 'var_data':
        if not isinstance(field_value, dict):
            return default

        options = validation.get('options') if validation is not None and isinstance(validation.get('options'), dict) else None
        properties = validation.get('properties') if validation is not None else None
        if isinstance(properties, dict):
            allow_types = properties.get('allow_types', [])
            allow_unknown = properties.get('allow_unknown', False)
            allow_description = properties.get('allow_description', False)
        else:
            allow_types = []
            allow_unknown = False
            allow_description = False

        result = { }
        for key, item in field_value.items():
            if not isinstance(item, dict):
                continue

            out = { 'name': key }
            name = try_value_as_type(item.get('name'), 'string', { 'properties': { 'sanitise': 'strict', 'length': [2, 500] } })
            typed = item.get('type')
            value = None

            props = options.get(key) if options is not None else None
            if isinstance(props, dict) and isinstance(props.get('type'), str):
                name = props.get('name')
                typed = props.get('type')
                value = try_value_as_type(item.get('value'), typed, { 'properties': props })

            if value is None and allow_unknown and isinstance(allow_types, list):
                if not name:
                    continue

                typed = item.get('type')
                if isinstance(typed, str) and typed in allow_types:
                    value = try_value_as_type(item.get('value'), typed, { 'properties': { 'sanitise': 'strict', 'length': 1024 } })

            if value is None or typed is None:
                continue

            if allow_description:
                desc = try_value_as_type(item.get('description'), 'string', { 'properties': { 'sanitise': 'strict', 'length': [2, 500] } })                
                if desc is not None:
                    out.update(description=desc)

            out.update(name=name, type=typed, value=value)
            result.update({ key: out })

        return result
    elif field_type == 'related_entities':
        if not isinstance(field_value, list):
            return default

        if len(field_value) < 1:
            return default

        target = validation.get('target') if validation is not None else None
        tbl_name = target.get('table') if target is not None else None
        selector = target.get('select') if target is not None else None

        properties = validation.get('properties') if validation is not None else None
        storage = properties.get('storage') if properties is not None else None

        if not isinstance(tbl_name, str) or not isinstance(storage, list) or not isinstance(selector, list):
            return default

        valid = True
        result = []
        try:
            model = apps.get_model(app_label='clinicalcode', model_name=tbl_name)
            for item in field_value:
                selection = { k: item.get(k) for k in selector }
                entity = model.objects.filter(**selection)
                if entity is None or not entity.exists():
                    continue

                entity = entity.first()
                result.append({ k: getattr(entity, k) for k in storage })
        except:
            valid = False

        return result if valid and len(result) > 0 else default
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


class PrettyPrintOrderedDefinition(json.JSONEncoder):
    """
        Indents and prettyprints the definition field so that it's readable
        Preserves order that was given by `template_utils.get_ordered_definition`
    """
    def __init__(self, *args, indent, sort_keys, **kwargs):
        super().__init__(*args, indent=2, sort_keys=False, **kwargs)
