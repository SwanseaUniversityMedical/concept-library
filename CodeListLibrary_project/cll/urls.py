"""
	CLL URL Configuration for Brands

	The `urlpatterns` list routes URLs to views. For more information please see:
		- https://docs.djangoproject.com/en/1.10/topics/http/urls/
	
	Examples:
		Function views
			1. Add an import:  from my_app import views
			2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
		
		Class-based views
			1. Add an import:  from other_app.views import Home
			2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
		
		Including another URLconf
			1. Import the include() function: from django.conf.urls import url, include
			2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))

"""
from django.apps import apps
from django.conf import settings
from django.urls import re_path as url
from django.urls import include
from django.contrib import admin
from django.core.cache import cache
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.views.decorators.cache import cache_control
from django.contrib.staticfiles.views import serve

import re
import logging

from clinicalcode.views import (GenericEntity, Publish, Decline)

#--------------------------------------------------------------------
# Const
"""Default URL transform reference"""
DEFAULT_TRGT = settings.BRAND_VAR_REFERENCE.get('default')

"""Variable URL target(s): Route varies by Brand context"""
URL_VARIANTS = [
	# GenericEntity/Phenotype variants
	## Search
	{ 'route': r'%(base)s{phenotypes}/$', 'view': GenericEntity.EntitySearchView.as_view(), 'name': 'search_entities' },

	## Support legacy Concept redirects
	{ 'route': r'%(base)s{concepts}/C(?P<pk>\d+)/detail/$', 'view': GenericEntity.RedirectConceptView.as_view(), 'name': 'redirect_concept_detail' },
	{ 'route': r'%(base)s{concepts}/C(?P<pk>\d+)/version/(?P<history_id>\d+)/detail/$', 'view': GenericEntity.RedirectConceptView.as_view(), 'name': 'redirect_concept_detail_with_version' },

	## Detail
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/$', 'view': RedirectView.as_view(pattern_name='entity_detail'), 'name': 'entity_detail_shortcut' },
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/detail/$', 'view': GenericEntity.generic_entity_detail, 'name': 'entity_detail' },
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$', 'view': GenericEntity.generic_entity_detail, 'name': 'entity_history_detail' },

	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/export/codes/$', 'view': GenericEntity.export_entity_codes_to_csv, 'name': 'export_entity_latest_version_codes_to_csv' },
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$', 'view': GenericEntity.export_entity_codes_to_csv, 'name': 'export_entity_version_codes_to_csv' },   

	## Publication
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/(?P<history_id>\d+)/publish/$', 'view': Publish.Publish.as_view(), 'name': 'generic_entity_publish' },
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/(?P<history_id>\d+)/decline/$', 'view': Decline.EntityDecline.as_view(), 'name': 'generic_entity_decline' },
	{ 'route': r'%(base)s{phenotypes}/(?P<pk>\w+)/(?P<history_id>\d+)/submit/$', 'view': Publish.RequestPublish.as_view(), 'name': 'generic_entity_request_publish' },
]

#--------------------------------------------------------------------
# Resolvers
"""Resulting URL configuration"""
urlpatterns = []

#--------------------------------------------------------------------
# Utilities
def get_brand_ctx_transform(urls):
	"""
		Build the brand context replace Callable, used as a lambda in a `re.sub` operation

		Args:
			urls (Dict[str, Any]): a (dict) containing the replace targets, keyed by the `{(\w+)}` match groups

		Returns:
			A (Callable) to be used in a `re.sub` operation
	"""
	def replace(match):
		"""Replaces matched regex groups with the route target"""
		m = match.group(1)
		r = urls.get(m)
		return r if isinstance(r, str) else m

	return replace

def append_branded_urls(brand=None, variants=[], patterns=[]):
	"""
		Method decorator to raise a 403 if a view isn't accessed by a Brand Administrator

		Args:
			brand                (Any|None): optionally specify the assoc. Brand context; defaults to using the `DEFAULT_TRGT` if not specified
			variants (List[Dict[str, Any]]): optionally specify the URL resolver variants; defaults to an empty list
			patterns    (List[URLResolver]): optionally specify the URL patterns, i.e. a list of URLResolvers, in which we will append the transformed routes; defaults to an empty list

		Returns:
			The specified `patterns`, or (List[URLResolver]), updated in place
	"""
	try:
		if brand is None:
			trgt = 'default'
			urls = DEFAULT_TRGT
			base = '^'
		else:
			trgt = brand.name
			urls = settings.BRAND_VAR_REFERENCE.get(trgt, None)
			urls = urls.get('urls') if isinstance(urls, dict) and isinstance(urls.get('urls'), dict) else DEFAULT_TRGT.get('urls')
			base = f'^{brand.name}/'

		if not isinstance(urls, dict):
			logging.warning(f'Expected URL ref dict for Target<name: {trgt}> but got typeof "{type(urls)}"')
			return patterns

		tx_ctx = get_brand_ctx_transform(urls)
		for var in variants:
			if not isinstance(var, dict):
				logging.warning(f'Failed to process variant, expected dict but got "{type(var)}<{str(var)}>"')
				continue

			name = var.get('name')
			view = var.get('view')
			route = var.get('route')
			kwargs = var.get('kwargs') if isinstance(var.get('kwargs'), dict) else None

			if not isinstance(name, str) or view is None or not isinstance(route, str):
				logging.warning((
					f'Failed to validate variant, expected members {{ "name": str, "view": Any, "route": str, "kwargs": Any|None }} but got:\n'
					f'  -> "name" as Value<type: {type(name)}, data: {str(name)}>\n'
					f'  -> "view" as Value<type: {type(view)}, data: {str(view)}>\n'
					f'  -> "route" as Value<type: {type(route)}, data: {str(route)}>\n'
				))
				continue

			route = route % { 'base': base }
			route = re.sub(r'{([^{}]+)}', tx_ctx, route)
			patterns.append(url(route=route, view=view, kwargs=kwargs, name=name))
	except Exception as e:
		logging.exception(f'Failed to create URL variants on Target<name: {trgt}> with err:\n\n{str(e)}')

	return patterns

#--------------------------------------------------------------------
# Brands
current_brand = f'{settings.CURRENT_BRAND}/' if isinstance(settings.CURRENT_BRAND, str) and settings.CURRENT_BRAND != '' else ''
if settings.IS_HDRUK_EXT == '1':
	current_brand = ''

#--------------------------------------------------------------------
# Urls
urlpatterns += [
	# api
	url(r'^' + current_brand + 'api/v1/', include(('clinicalcode.api.urls', 'cll'), namespace='api')),

	# account management
	url(r'^' + current_brand + 'account/', include('clinicalcode.urls_account')),

	# app urls
	url(r'^' + current_brand + '', include('clinicalcode.urls')),
]

# Media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Static files
if settings.DEBUG:
	urlpatterns += static(settings.STATIC_URL, view=cache_control(no_cache=True, must_revalidate=True)(serve))

# Admin system
if not settings.CLL_READ_ONLY:
	urlpatterns += [
		url(r'^' + current_brand + 'admin/', admin.site.urls),
	]

# Variant URL resolvers
try:
	if settings.IS_HDRUK_EXT != '1':
		brands = apps.get_model(app_label='clinicalcode', model_name='Brand')
		brands = brands.all_instances()

		target = next((x for x in brands if x.name == settings.CURRENT_BRAND), None)
	else:
		target = None

	append_branded_urls(brand=target, variants=URL_VARIANTS, patterns=urlpatterns)
except Exception as e:
	logging.exception(f'Failed to create branded URL variants with err:\n\n{str(e)}')
