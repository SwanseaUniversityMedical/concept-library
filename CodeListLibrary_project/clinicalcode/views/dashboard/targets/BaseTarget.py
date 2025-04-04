"""Brand Dashboard: Base extensible/abstract classes"""
from django.http import Http404
from django.http import HttpRequest
from rest_framework import status, generics, mixins, serializers, fields
from django.db.models import Model
from rest_framework.request import Request
from rest_framework.response import Response
from django.utils.functional import classproperty

import inspect
import builtins

from clinicalcode.entity_utils import permission_utils, model_utils, gen_utils


"""Default Model `pk` field filter, _e.g._ the `ID` integer primary key"""
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
				elif v is not None and type(v).__name__ != '__proxy__' and (type(v).__name__ == 'type' or ((hasattr(v, '__name__') or hasattr(v, '__class__') or inspect.isclass(v)) and not type(v).__name__ in dir(builtins))):
					value = type(v).__name__

				if group is None:
					group = {}
				group.update({ k: value })

			trg = field
			if isinstance(trg, serializers.ListSerializer):
				trg = trg.child

			disp = getattr(trg, '_str_display') if hasattr(trg, '_str_display') else None
			if isinstance(disp, str) and not gen_utils.is_empty_string(disp):
				group.update({ 'str_display': disp })

			if hasattr(trg, 'resolve_options') and callable(getattr(trg, 'resolve_options', None)):
				group.update({ 'value_options': trg.resolve_options() })
			elif hasattr(trg, 'get_choices') and callable(getattr(trg, 'get_choices', None)):
				group.update({ 'value_options': trg.get_choices() })

			if hasattr(trg, 'resolve_format') and callable(getattr(trg, 'resolve_format', None)):
				group.update({ 'value_format': trg.resolve_format() })

			if isinstance(field, (serializers.ListField, serializers.ListSerializer)):
				group.update({ 'type': type(field.child).__qualname__, 'subtype': type(field).__qualname__ })
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
	def _update(instance, validated_data):
		"""
		Dynamically updates a model instance, setting Many-to-Many fields first if present.
		@param instance:
		@param validated_data:
		@return:
		"""

		# Handle ManyToMany fields
		# Loop through fields and set values dynamically
		for field in instance._meta.get_fields(include_parents=True):
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
			for field in model_class._meta.get_fields(include_parents=True)
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

	# QuerySet kwargs
	filter = None

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
			serializer = self.get_serializer(instance)
			response = { 'data': serializer.data }
			self._format_list_data(response, serializer=serializer)
		except Exception as e:
			return Response(
				data={ 'detail': str(e) },
				status=status.HTTP_400_BAD_REQUEST
			)
		else:
			return Response(response)

	def list(self, request, *args, **kwargs):
		params = getattr(self, 'filter', None)
		params = params if isinstance(params, dict) else None

		page_obj = self.model.get_brand_paginated_records_by_request(request, params=params)

		results = self.serializer_class(page_obj.object_list, many=True)
		response = self._format_list_data({
			'detail': self._format_page_details(page_obj),
			'results': results.data,
		})

		return Response(response)

	# Mixin methods
	def get_queryset(self, *args, **kwargs):
		params = getattr(self, 'filter', None)
		if isinstance(params, dict):
			params = kwargs | params
		else:
			params = kwargs

		return self.model.get_brand_records_by_request(self.request, params=params)

	def get_object(self, *args, **kwargs):
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
	def _get_query_params(self, request, kwargs=None):
		params = getattr(self, 'filter', None)
		params = params if isinstance(params, dict) else { }
		if not isinstance(kwargs, dict):
			kwargs = { }

		if isinstance(request, Request) and hasattr(request, 'query_params'):
			params = { key: value for key, value in request.query_params.items() } | kwargs | params
		elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
			params = { key: value for key, value in request.GET.dict().items() } | kwargs | params

		return params

	def _format_list_data(self, response, serializer=None):
		if serializer is None:
			serializer = self.get_serializer()

		renderable = { 'form': serializer.form_fields }
		show_fields = getattr(serializer, '_list_fields', None) if hasattr(serializer, '_list_fields') else None
		show_fields = show_fields if isinstance(show_fields, list) else None
		if not isinstance(show_fields, list):
			show_fields = [self.model._meta.pk.name]

		item_fields = getattr(serializer, '_item_fields', None) if hasattr(serializer, '_item_fields') else None
		if not isinstance(item_fields, list):
			item_fields = [
				k
				for k, v in renderable.get('form').items()
				if isinstance(v.get('style'), dict) and v.get('style').get('data-itemdisplay', True)
			]

		features = getattr(serializer, '_features', None) if hasattr(serializer, '_features') else None
		if not isinstance(features, dict):
			features = None

		response.update(renderable=renderable | { 'fields': show_fields, 'order': item_fields, 'features': features })
		return response

	def _format_page_details(self, page_obj):
		num_pages = page_obj.paginator.num_pages
		page = min(page_obj.number, num_pages)

		detail = {
			'page': page,
			'total_pages': num_pages,
			'page_size': page_obj.paginator.per_page,
			'has_previous': page_obj.has_previous(),
			'has_next': page_obj.has_next(),
			'max_results': page_obj.paginator.count,
		}

		if num_pages <= 9:
			detail.update(pages=set(range(1, num_pages + 1)))
		else:
			page_items = []
			min_page = page - 1
			max_page = page + 1
			if min_page <= 1:
				min_page = 1
				max_page = min(page + 2, num_pages)
			else:
				page_items += [1, 'divider']

			if max_page > num_pages:
				min_page = max(page - 2, 1)
				max_page = min(page, num_pages)

			page_items += list(range(min_page, max_page + 1))
			if num_pages not in page_items:
				page_items += ['divider', num_pages]
			detail.update(pages=page_items)

		return detail
