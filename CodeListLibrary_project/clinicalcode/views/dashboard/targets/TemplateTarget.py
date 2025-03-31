"""Brand Dashboard: API endpoints relating to Template model"""
import datetime
import json

from rest_framework import status, serializers
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from rest_framework.response import Response

from .BaseTarget import BaseSerializer, BaseEndpoint
from .BrandTarget import BrandSerializer
from clinicalcode.entity_utils import gen_utils, template_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Template import Template
from clinicalcode.models.EntityClass import EntityClass


User = get_user_model()


class EntityClassSerializer(BaseSerializer):
	""""""

	# Appearance
	_str_display = 'name'
	_list_fields = ['id', 'name']
	_item_fields = ['id', 'name', 'description']

	# Metadata
	class Meta:
		model = EntityClass
		exclude = ['created_by', 'modified_by', 'created', 'modified', 'entity_count']
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
			'entity_prefix': { 'read_only': True, 'required': False },
			# WO
			'created': { 'write_only': True, 'read_only': False, 'required': False },
			'modified': { 'write_only': True, 'read_only': False, 'required': False },
			'created_by': { 'write_only': True, 'read_only': False, 'required': False },
			'modified_by': { 'write_only': True, 'read_only': False, 'required': False },
		}

	# GET
	def resolve_options(self):
		return list(self.Meta.model.objects.all().values('name', 'pk'))


class TemplateSerializer(BaseSerializer):
	"""Responsible for serialising the `Template` model and to handle PUT/POST validation"""

	# Fields
	brands = BrandSerializer(many=True)
	entity_class = EntityClassSerializer()

	# Appearance
	_str_display = 'name'
	_list_fields = ['id', 'name', 'template_version']
	_item_fields = ['id', 'name', 'template_version', 'description', 'brands']

	# Metadata
	class Meta:
		model = Template
		exclude = ['created_by', 'updated_by', 'created', 'modified']
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
			'name': { 'read_only': True, 'required': False },
			'description': { 'read_only': True, 'required': False },
			# WO
			'created': { 'write_only': True, 'read_only': False, 'required': False },
			'modified': { 'write_only': True, 'read_only': False, 'required': False },
			'created_by': { 'write_only': True, 'read_only': False, 'required': False },
			'updated_by': { 'write_only': True, 'read_only': False, 'required': False },
			'entity_class': { 'write_only': True, 'read_only': False, 'required': False },
			'hide_on_create': { 'write_only': True, 'read_only': False, 'required': False },
		}

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
			'brands': brands,
			'definition': definition,
			'created_by': user,
			'updated_by': user,
		})

		return self.Meta.model.objects.create(**validated_data)

	def update(self, instance, validated_data):
		current_brand = self._get_brand()

		brands = validated_data.get('brands')
		if isinstance(brands, Brand):
			brands = [brands.id]
		elif isinstance(brands, int):
			brands = [brands]

		if isinstance(brands, list):
			brands = [x.id if isinstance(x, Brand) else x for x in brands if isinstance(x, (Brand, int))]
			if current_brand and not current_brand.id in brands:
				brands.append(current_brand.id)
		elif current_brand:
			brands = instance.brands if isinstance(instance.brands, list) else []
			if current_brand and not current_brand.id in brands:
				brands.append(current_brand.id)
		else:
			brands = instance.brands

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
		instance = getattr(self, 'instance') if hasattr(self, 'instance') else None

		entity_class = data.get('entity_class')
		if instance is None and not isinstance(entity_class, int):
			raise serializers.ValidationError('Required `entity_class` field of `pk` type is missing')

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
