"""Assorted RedirectView targets"""
from django.conf import settings
from django.http.response import Http404
from django.views.generic.base import RedirectView

import enum

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.GenericEntity import GenericEntity

class ResourceEndpoints(str, enum.Enum):
	"""
	URL templates for resource target(s), used to build final redirect URL
	"""
	CURRENT   = '%(url)s/%(res)s/detail/'
	VERSIONED = '%(url)s/%(res)s/version/%(ver)s/detail/'

class ResourceRedirectView(RedirectView):
	"""
	A `RedirectView` to redirect the requestor to the assoc. resource; used to redirect DOI URL resource(s)
	"""
	permanent = False
	query_string = False

	def get(self, request, *args, **kwargs):
		"""
		Handle GET requests

		Note:
			- Responsible for appending the `HttpRequest`'s `host` and `scheme` properties to the `kwargs`

		Kwargs:
			target          (str): appended by the url handler - denotes the request type, one of `doi` | `rel`
			pk              (str): the resource ID
			history_id (str|None): optionally specify the resource's version ID; defaults to `None`
			brand      (str|None): optionally specify the resource's desired :model:`Brand` to vary host resolution; defaults to `None`
		"""
		kwargs.update({ 'host': '%s://%s' % (request.scheme, request.get_host()) })
		return super().get(request, *args, **kwargs)

	def get_redirect_url(self, *args, **kwargs):
		"""
		Generates the redirect URL

		Kwargs:
			host            (str): the hostname _assoc._ with this request
			target          (str): appended by the url handler - denotes the request type, one of `doi` | `rel`
			pk              (str): the resource ID
			history_id (str|None): optionally specify the resource's version ID; defaults to `None`
			brand      (str|None): optionally specify the resource's desired :model:`Brand` to vary host resolution; defaults to `None`

		Returns:
			(str): the constructed URL

		Raises:
			Http404: raised if either (a) the target is not recognised or (b) if the parameters are invalid
		"""
		host = kwargs.get('host', None)
		target = kwargs.get('target', None)

		res = self.__resolve_resource(**kwargs)
		brand = res.get('brand', None)

		url = self.__resolve_url(host, brand=brand)
		entity_id = res.get('entity_id', None)
		entity_version = res.get('entity_version', None)

		match target:
			case 'doi':
				if entity_version is None:
					raise Http404

				return ResourceEndpoints.VERSIONED.value % {
					'url': url,
					'res': entity_id,
					'ver': entity_version,
				}

			case 'rel':
				return ResourceEndpoints.CURRENT.value % {
					'url': url,
					'res': entity_id,
				}

			case _:
				raise Http404

	def __resolve_url(self, host, brand=None):
		"""
		Attempts to construct the hostname & root path as a single `str` unit

		Args:
			host         (str): the hostname resolved from the `HttpRequest`
			brand (Model|None): optionally specify the desired :model:`Brand` context
		
		Returns:
			(str): the constructed hostname & root path
		"""
		is_demo = settings.DEBUG or settings.IS_DEMO or settings.IS_DEVELOPMENT_PC
		is_readonly = not settings.IS_DEVELOPMENT_PC and (settings.IS_DEMO or settings.CLL_READ_ONLY or settings.IS_INSIDE_GATEWAY)

		root = self.__resolve_root(brand)
		if isinstance(brand, Brand):
			if not is_demo and not is_readonly:
				match brand.name.upper():
					case 'HDRUK':
						url = 'https://phenotypes.healthdatagateway.org'
					case _:
						url = '%s/%s' % (host, brand.name)
			else:
				url = '%s/%s' % (host, brand.name)
		else:
			url = host
		return '%s/%s' % (url, root)

	def __resolve_root(self, brand=None):
		"""
		Attempts to construct the root path name per the :model:`Brand` rule(s)

		Args:
			brand (Model|None): optionally specify the desired :model:`Brand` context
		
		Returns:
			(str): the root path name
		"""
		if not isinstance(brand, Brand):
			urls = settings.BRAND_VAR_REFERENCE.get('default')
		else:
			urls = settings.BRAND_VAR_REFERENCE.get(brand.name, None)
			urls = urls.get('urls') if isinstance(urls, dict) and isinstance(urls.get('urls'), dict) else settings.BRAND_VAR_REFERENCE.get('default')
		return urls.get('phenotypes', 'phenotypes')

	def __resolve_resource(self, **kwargs):
		"""
		Attempts to resolve the resource & properties assoc. with the request
		
		Returns:
			(Dict[Str,Any]|None): if resolved, the associated resource; otherwise returns a `NoneType` value
		"""
		pk = kwargs.get('pk', None)
		if not isinstance(pk, str) or gen_utils.is_empty_string(pk):
			return None

		entity = GenericEntity.objects.filter(id=pk)
		if not entity.exists():
			return None

		entity = entity.first()
		history_id = kwargs.get('history_id', None)
		history_id = gen_utils.parse_int(history_id)

		brand = kwargs.get('brand', None)
		if isinstance(brand, str) and not gen_utils.is_empty_string(brand):
			brand = brand.upper()
			brand = next((x for x in Brand.all_instances() if x.name.upper() == brand), None)

		if brand is None:
			brand = entity.brands if isinstance(entity.brands, list) else []
			brand = Brand.objects.filter(pk=brand[0]) if len(brand) > 0 else None
			if brand is not None and brand.exists():
				brand = brand.first()
			else:
				brand = None

		return {
			'brand': brand,
			'entity': entity,
			'entity_id': pk,
			'entity_version': history_id,
		}
