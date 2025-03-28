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


class BaseSerializer(serializers.ModelSerializer):
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

			if isinstance(field, serializers.ListField):
				group.update({ 'type': type(field).__qualname__, 'subtype': type(field.child).__qualname__ })
			else:
				group.update({ 'type': type(field).__qualname__, 'subtype': None })

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

	@staticmethod
	def _update( instance, validated_data):
		"""
		Dynamically updates a model instance, setting Many-to-Many fields first if present.
		@param instance:
		@param validated_data:
		@return:
		"""

		# Handle ManyToMany fields
		# Loop through fields and set values dynamically
		for field in instance._meta.get_fields():
			field_name = field.name

			# Skip fields not in validated_data
			if field_name not in validated_data:
				continue

			value = validated_data.pop(field_name)

			# Handle ManyToMany relationships dynamically
			if field.many_to_many:
				getattr(instance, field_name).set(value)
			else:
				setattr(instance, field_name, value)
		return instance

	@staticmethod
	def _create(model_class, validated_data):
		"""
        Dynamically create a new model instance, setting Many-to-Many fields first if present.

        Args:
            model_class (Model): The Django model class to create an instance for.
            validated_data (dict): The validated data for creation.

        Returns:
            Model: The newly created instance.
		"""
		# Step 1: Extract Many-to-Many fields
		m2m_data = {
			field.name: validated_data.pop(field.name)
			for field in model_class._meta.get_fields()
			if field.many_to_many and field.name in validated_data
		}

		# Step 2: Create the instance with remaining fields
		instance = model_class.objects.create(**validated_data)

		# Step 3: Set Many-to-Many fields
		for field_name, value in m2m_data.items():
			getattr(instance, field_name).set(value)

		return instance



class BaseEndpoint(
	generics.GenericAPIView,
	mixins.RetrieveModelMixin,
	mixins.UpdateModelMixin,
	mixins.ListModelMixin,
	mixins.CreateModelMixin
):
	"""Extensible endpoint class for TargetEndpoint(s)"""

	# View behaviour
	permission_classes = [permission_utils.IsBrandAdmin]

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
			instance = self.get_object(*args, **kwargs)
		except Exception as e:
			return Response(
				data={ 'detail': str(e) },
				status=status.HTTP_400_BAD_REQUEST
			)
		else:
			serializer = self.get_serializer(instance)
			response = { 'data': serializer.data }
			self.__format_item_data(response, serializer=serializer)
			return Response(response)

	def list(self, request, *args, **kwargs):
		page_obj = self.model.get_brand_paginated_records_by_request(request)

		results = self.serializer_class(page_obj.object_list, many=True)
		response = {
			'detail': {
				'page': min(page_obj.number, page_obj.paginator.num_pages),
				'total_pages': page_obj.paginator.num_pages,
				'page_size': page_obj.paginator.per_page,
				'has_previous': page_obj.has_previous(),
				'has_next': page_obj.has_next(),
				'max_results': page_obj.paginator.count,
			},
			'results': results.data,
		}

		self.__format_list_data(response)
		return Response(response)

	# Mixin methods
	def get_queryset(self, *args, **kwargs):
		return self.model.get_brand_records_by_request(self.request, params=kwargs)

	def get_object(self, *args, **kwargs):
		kwargs |= (self.kwargs if isinstance(self.kwargs, dict) else {})

		inst = self.get_queryset().filter(*args, **kwargs)
		if not inst.exists():
			raise Http404(f'A {self.model._meta.model_name} matching the given parameters does not exist.')

		return inst.first()

	def update(self, request, *args, **kwargs):
		"""Overrides the update mixin"""
		partial = kwargs.pop('partial', False)
		instance = self.get_object(*args, **kwargs)  # Now uses kwargs dynamically
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.is_valid(raise_exception=True)
		self.perform_update(serializer)
		return Response(serializer.data)

	# Private methods
	def __format_item_data(self, response, serializer=None):
		if serializer is None:
			serializer = self.get_serializer()

		renderable = { 'form': serializer.form_fields }
		show_fields = getattr(serializer, '_item_fields', None) if hasattr(serializer, '_item_fields') else None
		if not isinstance(show_fields, list):
			show_fields = [
				k
				for k, v in renderable.get('form').items()
				if isinstance(v.get('style'), dict) and v.get('style').get('data-itemdisplay', True)
			]

		response.update(renderable=renderable | { 'fields': show_fields })
		return response

	def __format_list_data(self, response, serializer=None):
		if serializer is None:
			serializer = self.get_serializer()

		renderable = { 'form': serializer.form_fields }
		show_fields = getattr(serializer, '_list_fields', None) if hasattr(serializer, '_list_fields') else None
		if not isinstance(show_fields, list):
			show_fields = [self.model._meta.pk.name]

		response.update(renderable=renderable | { 'fields': show_fields })
		return response
