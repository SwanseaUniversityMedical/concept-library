"""Brand Dashboard: Base extensible/abstract classes"""
from django.http import Http404
from rest_framework import status, generics, mixins, serializers, fields
from django.db.models import Model
from django.core.exceptions import BadRequest
from rest_framework.response import Response
from django.utils.functional import classproperty, cached_property
from django.core.serializers.json import DjangoJSONEncoder

import json
import inspect
import builtins

from clinicalcode.entity_utils import permission_utils, model_utils, gen_utils


""""""
DEFAULT_LOOKUP_FIELD = 'pk'


class BaseSerializer(serializers.Serializer):
	"""Extensible serializer class for Target(s)"""

	# Getters
	@property
	def form_fields(self):
		instance = getattr(self, 'instance') if hasattr(self, 'instance') else None

		form = {}
		for name, field in self.fields.items():
			group = None
			for k, v in vars(field).items():
				if k.startswith('_'):
					continue

				value = v
				if v == fields.empty or isinstance(v, fields.empty):
					value = None
				elif v is not None and (type(v).__name__ == 'type' or ((hasattr(v, '__name__') or hasattr(v, '__class__') or inspect.isclass(v)) and not type(v).__name__ in dir(builtins))):
					value = type(v).__name__

				if group is None:
					group = {}
				group.update({ k: value })

			src = group.get('source')
			if instance is not None and isinstance(src, str) and hasattr(instance, src):
				group.update({ 'value': getattr(instance, src) })
			form.update({ name: group })
		return form

	# Private utility methods
	def _get_user(self):
		request = self.context.get('request')
		if request and hasattr(request, 'user'):
			return request.user
		return None

	def _get_brand(self):
		request = self.context.get('request')
		if request:
			return model_utils.try_get_brand(request)
		return None


class BaseEndpoint(
	generics.GenericAPIView,
	mixins.RetrieveModelMixin,
	mixins.UpdateModelMixin,
	mixins.ListModelMixin,
	mixins.CreateModelMixin
):
	"""Extensible endpoint class for TargetEndpoint(s)"""

	# View behaviour
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	# Exclude endpoint(s) from swagger
	swagger_schema = None

	# Properties
	@classproperty
	def lookup_field(cls):
		if hasattr(cls, '_lookup_field'):
			lookup = getattr(cls, '_lookup_field')
			if isinstance(lookup, str) and not gen_utils.is_empty_string(lookup):
				return lookup
		elif hasattr(cls, 'model'):
			model = getattr(cls, 'model', None)
			if inspect.isclass(model) or not issubclass(model, Model):
				return model._meta.pk.name
		return DEFAULT_LOOKUP_FIELD

	# Mixin views
	def retrieve(self, request, *args, **kwargs):
		try:
			instance = self.get_object(*args, *kwargs)
		except Exception as e:
			return Response(
				data={ 'detail': str(e) },
				status=status.HTTP_400_BAD_REQUEST
			)
		else:
			serializer = self.get_serializer(instance)
			return Response(serializer.data)

	def list(self, request, *args, **kwargs):
		page_obj = self.model.get_brand_paginated_records_by_request(request)

		results = self.serializer_class(page_obj.object_list, many=True)
		results = results.data
		return Response({
			'detail': {
				'page': min(page_obj.number, page_obj.paginator.num_pages),
				'total_pages': page_obj.paginator.num_pages,
				'page_size': page_obj.paginator.per_page,
				'has_previous': page_obj.has_previous(),
				'has_next': page_obj.has_next(),
				'max_results': page_obj.paginator.count,
			},
			'results': results,
		})

	# Mixin methods
	def get_queryset(self, *args, **kwargs):
		return self.model.get_brand_records_by_request(self.request, params=kwargs)

	def get_object(self, *args, **kwargs):
		pk = kwargs.get('pk', self.kwargs.get('pk'))
		if pk is None:
			raise BadRequest('Expected `pk` parameter')

		inst = self.get_queryset().filter(pk=pk)
		if not inst.exists():
			raise Http404(f'{self.model._meta.model_name} of PK `{pk}` does not exist')

		return inst.first()
