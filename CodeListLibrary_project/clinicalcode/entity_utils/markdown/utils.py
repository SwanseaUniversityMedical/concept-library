from urllib.parse import urlparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.regex_helper import _lazy_re_compile

import re

def is_external_ref(url):
	"""
	Compares the given URL string to the allowed hosts defined within settings.py

	Args:
		url (string|any): some input string

	Returns:
		A boolean specifying whether the given URL is an external host or not
	"""
	if not isinstance(url, str) or len(url) < 1 or url.isspace():
		return False

	try:
		url = urlparse(url.strip())
		return not url.hostname in settings.ALLOWED_HOSTS
	except:
		return True

def get_valid_url(url, default=None):
	"""
	Attempts to derive a valid URL and related properties from the specified input

	Args:
		url (string|any): some input string
		default (any): some default value to return if the URL is invalid

	Returns:
		A dict containing the valid URL's properties; otherwise returns the specified default value
	"""
	if not isinstance(url, str) or len(url) < 1 or url.isspace():
		return default

	try:
		url = urlparse(url.strip())
	except:
		return default
	else:
		address = url.geturl()
		if not isinstance(url.scheme, str) or len(url.scheme) < 1:
			address = 'http://' + address

		return {
			'host': url.hostname,
			'address': address,
			'is_external': not url.hostname in settings.ALLOWED_HOSTS
		}

class EmailValidator:
	"""
	NOTE

	This pattern does not match internationalized e-mail addresses via the `SMTPUTF8` extension
	and it is not fully compliant with RFC 822 because we're not concerned with supporting IP address
	domains and/or unusual email addresses.

	This means that the following valid e-mail addresses such as the following would fail:

			- UTF8: `ツ.com`
			- IPv4: `some.email.user@[192.168.1.1]`
			- IPv6: `some.email.user@[IPv6:2001:db8::1]`
			- Misc. characters: `!$%@:@email.com`
			- Quoted address with spaces: `"unusual.email address @ name132342"@email.com`

	See the following references for more information:

			- Fully compliant regex pattern is available [here](https://pdw.ex-parrot.com/Mail-RFC822-Address.html)
			- Maximum email address length is available [here](https://www.rfc-editor.org/rfc/rfc3696#section-3)
			- `SMTPUTF8` reference is available [here](https://www.rfc-editor.org/rfc/rfc6532#section-3.2)

	"""
	# Email link prefix
	prefix = 'mailto:'
	# Email regex
	pattern = _lazy_re_compile(r'\b([^\s\/@:"]+)(?<=[\w])@(\S+)\.([\w]+)\b', re.MULTILINE | re.IGNORECASE)

	@classmethod
	def validate(cls, value, allow_prefix=True, allow_multiple=False):
		"""
		Attempts to validate the specified value as a valid e-mail address

		Args:
			value (string|any): some input value
			allow_prefix (boolean|any): specifies whether the `mailto:` prefix is allowed (defaults to `True`)
			allow_multiple (boolean|any): specifies whether multiple e-mail addresses are allowed per input (defaults to `False`)

		Returns:
			A boolean reflecting the successful validation of the input value; otherwise raises a `ValidationError`
		"""
		value = cls._validate_input(value, allow_prefix)

		matched = cls.pattern.findall(value)
		matches = len(matched) if isinstance(matched, list) else 0
		if allow_multiple and matches < 1:
			raise ValidationError('Specified value is not a valid e-mail address')
		elif not allow_multiple:
			if matches < 1:
				raise ValidationError('Specified value is not a valid e-mail address')
			elif matches > 1:
				raise ValidationError('Specified value describes more than one valid e-mail address')

		for item in matched:
			(localpart, domainpart, tld) = item
			if len(localpart) > 64:
				raise ValidationError('Localpart of specified value exceeds 64 characters in length')
			elif len(domainpart) + len(tld) > 255:
				raise ValidationError('Domainpart & TLD of specified value exceeds 255 characters in length')

		return True

	@classmethod
	def get_components(cls, value, allow_prefix=True, take_first=True, default=None):
		"""
		Attempts to derive the e-mail-related components of the specified input

		Args:
			value (string|any): some input value
			allow_prefix (boolean|any): specifies whether the `mailto:` prefix is allowed (defaults to `True`)
			take_first (boolean|any): whether to take the first e-mail address from the specified input (defaults to `True`)
			default (any): a default value to return if this method fails

		Returns:
			A dict containing the components of the specified input if valid; otherwise returns the default value
		"""
		result = None
		try:
			value = cls._validate_input(value, allow_prefix)

			has_prefix = (cls.prefix in value) if allow_prefix else False
			if has_prefix:
				value = value.replace(cls.prefix, '', 1)

			matched = cls.pattern.findall(value)
			matches = len(matched) if isinstance(matched, list) else 0

			if matches < 1:
				raise ValidationError('Specified input does not contain a valid e-mail address')

			if not take_first and matches > 1:
				raise ValidationError('Specified input contains more than one valid e-mail address')

			(localpart, domainpart, tld) = matched.pop()
			if len(localpart) > 64 or len(domainpart) + len(tld) > 255:
				raise ValidationError('Invalid e-mail component length')

			result = {
				'has_prefix': has_prefix,
				'address': value,
				'localpart': localpart,
				'domain': '%s.%s' % (domainpart, tld,),
			}
		except ValidationError:
			result = default
		except Exception as e:
			raise e
		finally:
			return result

	@classmethod
	def _validate_input(cls, value, allow_prefix=True):
		"""
		Base validation of the given input

		Args:
			value (string|any): some input value
			allow_prefix (boolean|any): specifies whether the `mailto:` prefix is allowed (defaults to `True`)

		Returns:
			The a stripped & ASCII encoded copy of the input value; otherwise raises a `ValidationError`
		"""
		if not isinstance(value, str):
			raise ValidationError('Specified value is non-string type')

		value = bytes(value, 'utf-8').decode('ascii', 'ignore').strip()
		if not allow_prefix and cls.prefix in value:
			raise ValidationError('Specified value was disallowed prefix of %s' % (cls.prefix,))

		length = len(value)
		if length < 1 or value.isspace():
			raise ValidationError('Specified value is an empty string')
		elif length > 320:
			raise ValidationError('Specified value length exceeds 320 characters')
		return value
