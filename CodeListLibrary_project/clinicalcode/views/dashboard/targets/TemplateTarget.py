"""Brand Dashboard: API endpoints relating to Template model"""
from rest_framework import status, serializers
from django.utils.timezone import make_aware
from rest_framework.response import Response

import json
import datetime

from .BaseTarget import BaseSerializer, BaseEndpoint
from clinicalcode.entity_utils import gen_utils, template_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Template import Template


class TemplateSerializer(BaseSerializer):
	"""Responsible for serialising the `Template` model and to handle PUT/POST validation"""

	# Metadata
	model = Template

	# Appearance
	_list_fields = ['id', 'name', 'template_version']

	# Fields
	id = serializers.IntegerField(label='Id', read_only=True, required=False)
	name = serializers.CharField(label='Name', read_only=True, required=False)
	description = serializers.CharField(label='Description', read_only=True, required=False)
	brands = serializers.ListField(label='Brands', child=serializers.IntegerField(), required=False, allow_null=True, read_only=False)
	definition = serializers.JSONField(label='Definition', binary=False, encoder=gen_utils.PrettyPrintOrderedDefinition, required=True, read_only=False)
	template_version = serializers.IntegerField(label='Version', read_only=True, required=False)

	# GET
	def to_representation(self, instance):
		data = super(TemplateSerializer, self).to_representation(instance)
		definition = data.get('definition')
		if not instance or not hasattr(instance, 'pk') or not isinstance(definition, dict):
			return data

		details = definition.get('template_details')
		if isinstance(details, dict):
			details['name'] = details.get('name', '')
			details['description'] = details.get('description', '')

		data['definition'] = template_utils.get_ordered_definition(definition, clean_fields=True)
		return data

	# POST / PUT
	def create(self, validated_data):
		user = self._get_user()
		current_brand = self._get_brand()

		brands = validated_data.get('brands')
		if isinstance(brands, Brand):
			brands = [brands]
		elif isinstance(brands, int):
			brands = [brands]

		if isinstance(brands, list):
			brands = [x.id if isinstance(x, Brand) else x for x in brands if isinstance(x, (Brand, int))]
			if current_brand and not current_brand.id in brands:
				brands.append(current_brand.id)
		elif current_brand:
			brands = [current_brand.id]
		else:
			brands = None

		definition = self.__apply_def_ordering(validated_data.get('definition'))
		validated_data.update({
			'definition': definition,
			'brands': brands,
			'created_by': user,
			'updated_by': user,
		})

		return Template.objects.create(**validated_data)

	def update(self, instance, validated_data):
		current_brand = self._get_brand()

		brands = validated_data.get('brands')
		if isinstance(brands, Brand):
			brands = [brands]
		elif isinstance(brands, int):
			brands = [brands]

		if isinstance(brands, list):
			brands = [x.id if isinstance(x, Brand) else x for x in brands if isinstance(x, (Brand, int))]
			if current_brand and not current_brand.id in brands:
				brands.append(current_brand.id)

			brands = list(set(brands + instance.brands if isinstance(instance.brands, list) else brands))
		elif current_brand:
			brands = [current_brand.id]
		else:
			brands = None

		if instance is not None:
			definition = validated_data.get('definition', instance.definition)
		else:
			definition = validated_data.get('definition')

		instance.brands = brands
		instance.definition = self.__apply_def_ordering(definition)
		instance.updated_by = self._get_user()
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
	def __apply_def_ordering(self, definition):
		order = []
		for field in definition['fields']:
			definition['fields'][field]['order'] = len(order)
			order.append(field)

		definition['layout_order'] = order
		return definition


class TemplateEndpoint(BaseEndpoint):
	"""Responsible for API views relating to `Template` model accessed via Brand dashboard"""

	# Metadata
	model = Template
	fields = []
	queryset = Template.objects.all()
	serializer_class = TemplateSerializer

	# View behaviour
	reverse_name_default = 'brand_template_target'
	reverse_name_retrieve = 'brand_template_target_with_id'

	# Endpoint methods
	def get(self, request, *args, **kwargs):
		inst_id = kwargs.get('pk', None)
		if inst_id:
			inst_id = gen_utils.try_value_as_type(inst_id, 'int')
			if inst_id is None:
				return Response(
					data={ 'detail': 'Expected int-like `pk` parameter' },
					status=status.HTTP_400_BAD_REQUEST
        )

			kwargs.update(pk=inst_id)
			return self.retrieve(request, *args, **kwargs)

		return self.list(request, *args, **kwargs)

	def put(self, request, *args, **kwargs):
		return self.update(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)
