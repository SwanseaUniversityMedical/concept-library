from functools import partial
from django.conf import settings

import re
import bleach
import logging
import markdown
import pyhtml2md

from clinicalcode.entity_utils.markdown import utils as md_utils

logger = logging.getLogger(__name__)

"""Available sanitisation methods"""
SANITISE_METHODS = ['strict', 'markdown']

"""Default `strict` sanitisation properties"""
SANITISE_STRICT = {
	'tags': {},
	'attributes': {},
	'protocols': ['http', 'https'],
	'strip': True,
	'strip_comments': True
}

def nl_transform(match):
	m =  match.group(0)
	return m + '\n'

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

	text = re.sub(r'(.+\S)\n(?!\n)', nl_transform, text, flags=re.MULTILINE | re.IGNORECASE)
	text = text.strip()

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
	if isinstance(text, str) and len(text) > 0 and not text.isspace():
		text = pyhtml2md.convert(text)
	else:
		text = ''

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

def apply_anchor_props(attrs, new=False):
	"""
	Method used to apply HTML attributes to anchors parsed by django-markdownify;
	intention is to:

		- URL references: prefix URLs with protocol, apply rel attributes if external & apply other props
		- Email references: apply the `mailto` prefix

	See the following for more details:

		- Rel attributes found [here](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel)
		- Bleach / Markdown callbacks found [here](https://pythonhosted.org/bleach/linkify.html#callbacks-for-adjusting-attributes-callbacks)

	Args:
		attrs (dict): a dictionary describing the anchor's attributes
		new (boolean): ignore

	Returns:
		The processed `attr` dict
	"""
	text = attrs.get('_text', None)
	try:
		href = attrs[(None, u'href')].strip()
	except:
		href = None

	# Early exit & disable if no valid href / text props
	has_href = isinstance(href, str) and len(href) > 0 and not href.isspace()
	has_text = isinstance(text, str) and len(text) > 0 and not text.isspace()
	if not has_href and not has_text:
		attrs[(None, u'disabled')] = ''
		return attrs

	try:
		if email := md_utils.EmailValidator.get_components(href):
			# Apply email props
			attrs.update({ (None, u'href'): 'mailto:' + email.get('address') })
		elif url := md_utils.get_valid_url(href):
			# Apply URL props
			address = url.get('address')
			attrs.update({ (None, u'href'): address })

			# Apply rel attributes if external URL
			if url.get('is_external'):
				attrs[(None, u'rel')] = u'noopener noreferrer'

			# Open in new window
			attrs[(None, u'target')] = u'_blank'

			# Update title/text dependent on source value
			text_ref = md_utils.get_valid_url(text)
			if text_ref and text_ref.get('address') == address:
				attrs.update({ '_text': address })
			else:
				attrs[(None, u'title')] = text
		else:
			# Disable if no match
			attrs[(None, u'disabled')] = ''
	except Exception as e:
		# Disable if invalid
		logger.warning(f'Failed to process anchor<href: {href}, text: {text}> with err: {e}')
		attrs[(None, u'disabled')] = ''
	finally:
		return attrs
