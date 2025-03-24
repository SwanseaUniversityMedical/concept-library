""""""
from django.http import Http404
from rest_framework import status, generics, mixins, serializers
from django.utils.timezone import make_aware
from django.core.exceptions import ValidationError, BadRequest
from rest_framework.response import Response

import json
import datetime

from clinicalcode.entity_utils import gen_utils, template_utils, permission_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Template import Template


class TemplateSerializer(serializers.Serializer):
	""""""
	id = serializers.IntegerField(read_only=True, required=False)
	name = serializers.CharField(read_only=True, required=False)
	description = serializers.CharField(read_only=True, required=False)
	definition = serializers.JSONField(binary=False, encoder=gen_utils.PrettyPrintOrderedDefinition, required=True, read_only=False)
	template_version = serializers.IntegerField(read_only=True, required=False)

	# GET
	def to_representation(self, instance):
		data = super(TemplateSerializer, self).to_representation(instance)
		definition = data.get('definition')
		if not instance or not instance.pk or not isinstance(definition, dict):
			return data

		details = definition.get('template_details')
		if isinstance(details, dict):
			details['name'] = details.get('name', '')
			details['description'] = details.get('description', '')

		data['definition'] = template_utils.get_ordered_definition(definition, clean_fields=True)
		return data

	# PUT / POST
	def create(self, validated_data):
		return Template.objects.create(**validated_data)

	def update(self, instance, validated_data):
		definition = validated_data.get('definition', instance.definition)

		order = []
		for field in definition['fields']:
			definition['fields'][field]['order'] = len(order)
			order.append(field)
		definition['layout_order'] = order

		brands = validated_data.get('brands')
		if isinstance(brands, Brand):
			brands = [brands]
		elif isinstance(brands, int):
			brands = [brands]

		if isinstance(brands, list):
			brands = [x.id if isinstance(x, Brand) else x for x in brands if isinstance(x, (Brand, int))]
			brands = list(set(brands + instance.brands if isinstance(instance.brands, list) else brands))
		else:
			brands = instance.brands

		instance.brands = brands
		instance.definition = definition
		instance.updated_by = self.__user()
		instance.modified = make_aware(datetime.datetime.now())
		instance.save()
		return instance

	# Instance & Field validation
	def validate(self, data):
		definition = data.get('definition')
		if not isinstance(definition, dict):
			raise serializers.ValidationError('Required JSONField `definition` is missing')

		try:
			json.dumps(definition)
		except:
			raise serializers.ValidationError('Template definition is not valid JSON')

		template_fields = definition.get('fields')
		template_details = definition.get('template_details')
		template_sections = definition.get('sections')
		if not isinstance(template_fields, dict):
			raise serializers.ValidationError('Template `definition` field requires a `fields` key-value pair of type `dict`')
		elif not isinstance(template_details, dict):
			raise serializers.ValidationError('Template `definition` field requires a `template_details` key-value pair of type `dict`')
		elif not isinstance(template_sections, list):
			raise serializers.ValidationError('Template `definition` field requires a `sections` key-value pair of type `list`')

		name = template_details.get('name')
		if not isinstance(name, str) or gen_utils.is_empty_string(name):
			raise serializers.ValidationError('Template requires that the `definition->template_details.name` field be a non-empty string')

		template_details.update(description=template_details.get('description', ''))
		return data

	# Private utility methods
	def __user(self, obj):
		request = self.context.get('request', None)
		if request:
			return request.user
		return None


class TemplateEndpoint(
	generics.GenericAPIView,
	mixins.RetrieveModelMixin,
	mixins.UpdateModelMixin,
	mixins.ListModelMixin,
	mixins.CreateModelMixin
):
	""""""

	# Metadata
	model = Template
	fields = []
	queryset = Template.objects.all()
	lookup_field = 'id'
	serializer_class = TemplateSerializer

	# View behaviour
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]
	reverse_name_default = 'brand_template_target'
	reverse_name_retrieve = 'brand_template_target_with_id'

	# Exclude endpoint(s) from swagger
	swagger_schema = None

	# Endpoint methods
	def get(self, request, *args, **kwargs):
		inst_id = gen_utils.try_value_as_type(kwargs.get('pk', None), 'int')
		if inst_id is not None:
			kwargs.update(pk=inst_id)
			return self.retrieve(request, *args, **kwargs)
		return Response({ 'list': True })

	def put(self, request, *args, **kwargs):
		return self.update(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)

	# Mixin views
	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object(*args, *kwargs)
		serializer = self.get_serializer(instance)
		return Response(serializer.data)

	def list(self, request, *args, **kwargs):
		return Response({ })

	# Mixin methods
	def get_queryset(self, *args, **kwargs):
		user = self.request.user
		return self.queryset

	def get_object(self, *args, **kwargs):
		pk = kwargs.get('pk', self.kwargs.get('pk'))
		pk = gen_utils.try_value_as_type(pk, 'int')
		if pk is None:
			raise BadRequest('Expected int-like `pk` parameter')

		inst = self.get_queryset().filter(pk=pk)
		if not inst.exists():
			raise Http404(f'Template of ID `{pk}` does not exist')

		return inst.first()
