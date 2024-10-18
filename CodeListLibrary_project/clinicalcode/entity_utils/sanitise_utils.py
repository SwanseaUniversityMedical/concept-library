from functools import partial
from django.conf import settings
from urllib.parse import urlparse

import bleach
import markdown
import pyhtml2md

SANITISE_METHODS = ['strict', 'markdown']

SANITISE_STRICT = {
	'tags': {},
	'attributes': {},
	'protocols': ['http', 'https'],
	'strip': True,
	'strip_comments': True
}

def is_external_ref(url):
	"""
	Compares the given URL string to the allowed hosts defined within settings.py

	Args:
		url (string|any): some input string

	Returns:
		A boolean specifying whether the given URL is an external host or not
	"""
	if not isinstance(url, str):
		return False

	url = str(url).strip()
	if len(url) < 1 or url.isspace():
		return False

	url = urlparse(url)
	if not url.hostname in settings.ALLOWED_HOSTS.split(','):
		return True
	return False

def sanitise_markdown_html(text):
	"""
	Parses markdown as html and then sanitises it before reinterpreting it
	as a markdown string

	> [!NOTE]  
	> We'll need to revert this behaviour in the future; we should just  
	> store the result as HTML but our current HTML Markdown component  
	> doesn't support HTML nodes.  

	Args:
		text (string|any): some input string

	Returns:
		The sanitised output
	"""
	if not isinstance(text, str):
		return text

	text = str(text).strip()
	if len(text) < 1 or text.isspace():
		return text

	markdown_settings = settings.MARKDOWNIFY.get('default')

	whitelist_tags = markdown_settings.get('WHITELIST_TAGS', bleach.sanitizer.ALLOWED_TAGS)
	whitelist_attrs = markdown_settings.get('WHITELIST_ATTRS', bleach.sanitizer.ALLOWED_ATTRIBUTES)
	whitelist_styles = markdown_settings.get('WHITELIST_STYLES', bleach.css_sanitizer.ALLOWED_CSS_PROPERTIES)
	whitelist_protocols = markdown_settings.get('WHITELIST_PROTOCOLS', bleach.sanitizer.ALLOWED_PROTOCOLS)

	strip = markdown_settings.get('STRIP', True)
	extensions = markdown_settings.get('MARKDOWN_EXTENSIONS', [])
	extension_configs = markdown_settings.get('MARKDOWN_EXTENSION_CONFIGS', {})

	linkify = None
	linkify_text = markdown_settings.get('LINKIFY_TEXT', {'PARSE_URLS': True})
	if linkify_text.get('PARSE_URLS'):
		linkify_parse_email = linkify_text.get('PARSE_EMAIL', False)
		linkify_callbacks = linkify_text.get('CALLBACKS', [])
		linkify_skip_tags = linkify_text.get('SKIP_TAGS', [])
		linkifyfilter = bleach.linkifier.LinkifyFilter

		linkify = [partial(linkifyfilter,
			callbacks=linkify_callbacks,
			skip_tags=linkify_skip_tags,
			parse_email=linkify_parse_email
		)]

	html = markdown.markdown(text, extensions=extensions, extension_configs=extension_configs)

	css_sanitizer = bleach.css_sanitizer.CSSSanitizer(allowed_css_properties=whitelist_styles)
	cleaner = bleach.Cleaner(tags=whitelist_tags,
		attributes=whitelist_attrs,
		css_sanitizer=css_sanitizer,
		protocols=whitelist_protocols,
		strip=strip,
		filters=linkify,
	)

	# See [!note] above for why we're doing this...
	text = cleaner.clean(html)
	if isinstance(text, str) and len(str(text).strip()) > 0 and not text.isspace():
		return pyhtml2md.convert(text)
	return text

def sanitise_value(value, method='strict', default=None):
	"""
	Attempts to sanitise a string of HTML/SVG XSS attack vectors using bleach

	Args:
		value (string|any): some input string to sanitise
		method (string): the type of sanitisation to apply; defaults to `strict`
		default (any): some default return value on failure

	Returns:
		The sanitised string
	"""
	if not isinstance(value, str):
		return default

	value = str(value).strip()
	if len(value) < 1 or value.isspace():
		return value

	if not isinstance(method, str):
		method = 'strict'
	else:
		method = method.lower()
		if not method in SANITISE_METHODS:
			method = 'strict'

	try:
		if method == 'strict':
			value = bleach.clean(value, **SANITISE_STRICT)
		elif method == 'markdown':
			value = sanitise_markdown_html(value)
	except:
		return default

	return value

def apply_anchor_rel_attr(attrs, new=False):
	"""
	Method used to apply HTML attributes to anchors parsed by django-markdownify;
	intention is to apply the `noreferrer` and `external` attributes where appropriate

	See the following for more details: https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel

	Args:
		attrs (dict): a dictionary describing the anchor's attributes
		new (boolean): ignore

	Returns:
		A dictionary object with the 
	"""
	rel = [u'noreferrer'] # Or would we prefer the less strict noopener?
	try:
		external = is_external_ref(attrs[(None, u'href')])
	except:
		external = True

	if external:
		rel.append(u'external')

	attrs[(None, u'rel')] = ' '.join(rel)
	return attrs
