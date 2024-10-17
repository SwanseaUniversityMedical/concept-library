from django.conf import settings
from urllib.parse import urlparse

def is_external_ref(url):
	if not isinstance(url, str):
		return False

	url = str(url).strip()
	if len(url) < 1 or url.isspace():
		return False

	url = urlparse(url)
	if not url.hostname in settings.ALLOWED_HOSTS.split(','):
		return True
	return False

def apply_anchor_rel_attr(attrs, new=False):
	rel = [u'noreferrer'] # Or would we prefer the less strict noopener?
	try:
		external = is_external_ref(attrs[(None, u'href')])
	except:
		external = True

	if external:
		rel.append(u'external')

	attrs[(None, u'rel')] = ' '.join(rel)
	return attrs
