"""Brand Dashboard: Base extensible/abstract classes"""
from django.http import Http404
from rest_framework import status, generics, mixins, serializers
from django.core.exceptions import BadRequest
from rest_framework.response import Response

from clinicalcode.entity_utils import permission_utils, model_utils


class BaseSerializer(serializers.Serializer):
	"""Extensible serializer class for Target(s)"""

	# Public methods
	def get_form_data(self):
		return {
			k: {
				'field': v.field_name,
				'initial': v.initial,
				'required': v.required,
				'allow_null': v.allow_null,
				'read_only': v.read_only,
				'label': v.label,
				'help_text': v.help_text,
				'style': v.style,
			} for k, v in self.fields.items()
		}

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

	# Metadata
	lookup_field = 'id'

	# View behaviour
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	# Exclude endpoint(s) from swagger
	swagger_schema = None

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
