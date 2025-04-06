"""Custom EasyAudit request handling."""
from importlib import import_module
from ipaddress import ip_address as validate_ip
from easyaudit import settings as EasySettings
from django.conf import settings as AppSettings
from django.utils import timezone
from django.http.cookie import SimpleCookie
from django.contrib.auth import get_user_model, SESSION_KEY
from django.http.request import HttpRequest, split_domain_port, validate_host
from django.core.handlers.wsgi import WSGIHandler
from django.utils.regex_helper import _lazy_re_compile
from django.utils.module_loading import import_string
from django.contrib.sessions.models import Session

import re
import inspect

from clinicalcode.models import Brand


audit_logger = import_string(EasySettings.LOGGING_BACKEND)()
session_engine = import_module(AppSettings.SESSION_ENGINE)


def validate_ip_addr(addr):
	"""
	Attempts to validate the given IP address

	Args:
		default (str): the IP address to evaluate

	Returns:
		A (bool) reflecting the validity of the specified IP address

	"""
	try:
		validate_ip(addr)
	except ValueError:
		return False
	else:
		return True


def resolve_ip_addr(request, validate_ip=False, default='10.0.0.1'):
	"""
	Resolves the IP address assoc. with some request / the sender's _environ_

	Args:
		request (HttpRequest|Dict[string, Any]): either (a) a :class:`HttpRequest` assoc. with the signal or (b) a `Dict[str, Any]` describing its _environ_
		validate_ip                      (bool): optionally specify whether to validate the IP address; defaults to `False`
		default                           (Any): optionally specify the return value; defaults to `10.0.0.1` to represent an empty IP, likely from a proxy hiding the client

	Returns:
		A (str) specifying the IP if applicable; otherwise returns the given `default` parameter

	"""
	addr = None
	if isinstance(request, HttpRequest):
		if isinstance(request.headers.get('X-Forwarded-For'), str):
			addr = request.headers.get('X-Forwarded-For')

		if addr is None:
			request = request.META

	if isinstance(request, dict):
		for x in ['HTTP_X_FORWARDED_FOR', EasySettings.REMOTE_ADDR_HEADER, 'REMOTE_ADDR']:
			var = request.get(x)
			if isinstance(var, str):
				addr = var
				break

	if validate_ip and addr is not None and not validate_ip_addr(addr):
		addr = default
	elif addr is None:
		addr = default

	return addr


def match_url_patterns(url, patterns, flags=re.MULTILINE | re.IGNORECASE):
	"""
	Tests a variadic number of patterns against the given URL. 

	Args:
		url                (str): the URL to evaluate
		patterns (list[Pattern]): specifies the patterns to be matched against the URL test case
		flags              (int): optionally specify the regex flags to be used across all patterns; defaults to `MULTILINE` and `IGNORECASE`

	Returns:
		A (bool) specifying whether the URL test case has been successfully matched against one of the given pattern(s).

	"""
	if not isinstance(url, str) or not isinstance(patterns, list):
		return False

	for target in patterns:
		pattern = _lazy_re_compile(target, flags=flags)
		if pattern.match(url):
			return True

	return False


def get_request_info(sender, params):
	"""
	Attempts to resolve to resolve RequestContext data from the given WSGIRequest event kwargs.

	Args:
		sender (WSGIHandler|Any): the sender assoc. with this request
		params  (Dict[str, Any]): the kwargs associated with a request event

	Returns:
		A (Dict[str, Any]) specifying the request information if resolved; otherwise returns a (None) value

	"""
	scope = params.get('scope')
	environ = params.get('environ')

	# Resolve header
	info = None
	if environ:
		info = environ
		path = environ['PATH_INFO']
		cookie_string = environ.get('HTTP_COOKIE')
		method = environ['REQUEST_METHOD']
		query_string = environ['QUERY_STRING']

		remote_ip = None
		if isinstance(sender, WSGIHandler) or (inspect.isclass(sender) and issubclass(sender, WSGIHandler)):
			try:
				request = sender.request_class(environ)
				remote_ip = resolve_ip_addr(request, validate_ip=True, default=None)
			except:
				pass

		if remote_ip is None:
			remote_ip = resolve_ip_addr(environ)
	else:
		info = scope
		path = scope.get('path')
		method = scope.get('method')
		headers = dict(scope.get('headers'))
		cookie_string = headers.get(b'cookie')
		if isinstance(cookie_string, bytes):
			cookie_string = cookie_string.decode('utf-8')

		remote_ip = next(iter(scope.get('client', ('0.0.0.0', 0))))
		query_string = scope.get('query_string')

	# Resolve protocol
	protocol = None
	if AppSettings.SECURE_PROXY_SSL_HEADER:
		try:
			header, secure_value = AppSettings.SECURE_PROXY_SSL_HEADER
		except ValueError:
			header = None

		if header is not None:
			header_value = info.get(header)
			if header_value is not None:
				header_value, *_ = header_value.split(',', 1)
				protocol = 'https' if header_value.strip() == secure_value else 'http'

	if protocol is None:
		protocol = info.get('wsgi.url_scheme', 'http')

	# Resolve raw port
	if AppSettings.USE_X_FORWARDED_PORT and 'HTTP_X_FORWARDED_HOST' in info:
		rport = str(info.get('HTTP_X_FORWARDED_HOST'))
	else:
		rport = str(info.get('SERVER_PORT'))

	# Resolve raw host
	host = None
	if AppSettings.USE_X_FORWARDED_HOST and 'HTTP_X_FORWARDED_HOST' in info:
		host = info.get('HTTP_X_FORWARDED_HOST')
	elif 'HTTP_HOST' in info:
		host = info.get('HTTP_HOST')
	else:
		host = info.get('SERVER_NAME')
		if rport != ('443' if protocol == 'https' else '80'):
			host = '%s:%s' % (host, rport)

	# Attempt host validation
	allowed_hosts = AppSettings.ALLOWED_HOSTS
	if not isinstance(allowed_hosts, list) and AppSettings.DEBUG:
		allowed_hosts = ['.localhost', '127.0.0.1', '[::1]']

	domain, port = split_domain_port(host)
	if domain and not validate_host(domain, allowed_hosts):
		return None

	return {
		'method': method,
		'protocol': protocol,
		'host': host,
		'domain': domain,
		'port': port,
		'request_port': rport,
		'path': path,
		'remote_ip': remote_ip,
		'query_string': query_string,
		'cookie_string': cookie_string,
	}


def get_brand_from_request_info(info):
	"""
	Attempts to resolve a Brand from the request info, if applicable.

	Args:
		info (Dict[str, Any]): the request information derived from `get_request_info()`

	Returns:
		A (str) describing the name of the Brand associated with this request if applicable, otherwise returns a (None) value.

	"""
	if not isinstance(info, dict):
		return None

	domain = info.get('domain')
	if isinstance(domain, str):
		pattern = _lazy_re_compile(r'^(phenotypes\.healthdatagateway|web\-phenotypes\-hdr)', flags=re.MULTILINE | re.IGNORECASE)
		if pattern.match(domain):
			return 'HDRUK'

	url = info.get('path')
	root = url.lstrip('/').split('/')[0].upper().rstrip('/')
	if root in Brand.all_names():
		return root

	return None


def is_blacklisted_url(url, brand_name=None):
	"""
	Determines whether the requested URL event is blacklisted from being audited, considers Brand context if the Brand is specified.

	Args:
		url             (str): the desired url path, _e.g._ `/api/v1/some-endpoint/`
		brand_name (str|None): optionally specify the Brand context; defaults to `None`

	Returns:
		A (boolean) specifying whether this event's URL is blacklisted

	"""
	if not isinstance(url, str):
		return False

	# Det. whether URL is blacklisted per override rules (if applicable)
	override = AppSettings.OVERRIDE_EASY_AUDIT_IGNORE_URLS \
		if (hasattr(AppSettings, 'OVERRIDE_EASY_AUDIT_IGNORE_URLS') and isinstance(AppSettings.OVERRIDE_EASY_AUDIT_IGNORE_URLS, dict)) \
		else None

	all_override = override.get('all_brands') if override is not None else None
	brand_override = override.get(brand_name) if override is not None and isinstance(brand_name, str) else None
	if all_override or brand_override:
		if all_override and match_url_patterns(url, all_override):
			return True

		if brand_override and match_url_patterns(url, brand_override):
			return True

		return False

	# Otherwise, default to EasyAudit rules if not found
	return match_url_patterns(url, EasySettings.UNREGISTERED_URLS)


def should_log_url(url, brand_name=None):
	"""
	Determines whether the requested URL event should be logged to the audit table, considers Brand context if the Brand is specified.

	Args:
		url             (str): the desired url path, _e.g._ `/api/v1/some-endpoint/`
		brand_name (str|None): optionally specify the Brand context; defaults to `None`

	Returns:
		A (boolean) specifying whether this event should be logged

	"""
	if not isinstance(url, str):
		return False

	# Only include registered URLs if defined
	if brand_name is not None:
		url = url.lstrip('/' + brand_name)

	if not url.startswith('/'):
		url = '/' + url

	if isinstance(EasySettings.REGISTERED_URLS, list) and len(EasySettings.REGISTERED_URLS) > 0:
		for registered_url in EasySettings.REGISTERED_URLS:
			pattern = re.compile(registered_url)
			if pattern.match(url):
				return True
		return False

	# Otherwise, record all except those that are blacklisted
	return not is_blacklisted_url(url, brand_name)


def request_started_watchdog(sender, *args, **kwargs):
	"""A signal handler to observe Django `request_started <https://docs.djangoproject.com/en/5.1/topics/signals/>`__ events"""
	# Reconcile request context
	info = get_request_info(sender, kwargs)
	path = info.get('path')
	brand_name = get_brand_from_request_info(info)
	if not should_log_url(path, brand_name):
		return

	# Resolve the user from the auth cookie if applicable
	user = None
	cookie = info.get('cookie_string')
	if not user and cookie:
		cookie = SimpleCookie()
		cookie.load(cookie)

		session_cookie_name = AppSettings.SESSION_COOKIE_NAME
		if session_cookie_name in cookie:
			session_id = cookie[session_cookie_name].value
			try:
				session = session_engine.SessionStore(session_key=session_id).load()
			except Session.DoesNotExist:
				session = None

			if session and SESSION_KEY in session:
				user_id = session.get(SESSION_KEY)
				try:
					user = get_user_model().objects.get(id=user_id)
				except Exception:
					user = None

	# Log request interaction
	audit_logger.request({
		'url': path,
		'method': info.get('method'),
		'query_string': info.get('query_string'),
		'user_id': getattr(user, 'id', None),
		'remote_ip': info.get('remote_ip'),
		'datetime': timezone.now(),
	})
