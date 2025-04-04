"""Brand Dashboard: API endpoints relating to Template model"""
from rest_framework import status, serializers
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from rest_framework.response import Response

import json
import datetime

from .BaseTarget import BaseSerializer, BaseEndpoint
from .BrandTarget import BrandSerializer
from clinicalcode.entity_utils import gen_utils, template_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Template import Template
from clinicalcode.models.EntityClass import EntityClass


User = get_user_model()


# Const
TEMPLATE_NOTE_DESC = (
	'Please note that a Template\'s name, description, version and other metadata are defined by a Template\'s definition.'
	' These attributes can be specified within a Template\'s definition field, specifically its `template_details` property'
	' - please see the Template documentation for more information.'
)


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
	def resolve_format(self):
		return { 'type': 'ForeignKey' }

	def resolve_options(self):
		return list(self.Meta.model.objects.all().values('name', 'pk'))


class TemplateSerializer(BaseSerializer):
	"""Responsible for serialising the `Template` model and to handle PUT/POST validation"""

	# Fields
	brands = BrandSerializer(many=True, help_text='Specifies which Brands can use & interact with this Template and its descendants.')
	entity_class = EntityClassSerializer(help_text='Specifies how to categorise this Template & determines entity behaviour.')

	# Appearance
	_str_display = 'name'
	_list_fields = ['id', 'name', 'template_version']
	_item_fields = ['id', 'definition', 'entity_class', 'brands']
	_features = {
		'create': {
			'note': TEMPLATE_NOTE_DESC
		},
		'update': {
			'note': TEMPLATE_NOTE_DESC
		},
	}

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
			# WO | RO
			'definition': { 'required': True, 'help_text': 'Specifies the fields, datatypes, and features associated with this Template.' },
			'hide_on_create': { 'required': False, 'help_text': 'Specifies whether to hide this Template from the Create interface.' },
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

	# Instance & Field validation
	def validate(self, data):
		user = self._get_user()
		instance = getattr(self, 'instance') if hasattr(self, 'instance') else None
		current_brand = self._get_brand()

		entity_class = data.get('entity_class', instance.entity_class if instance else None)
		if entity_class is not None:
			if isinstance(entity_class, int):
				entity_class = EntityClass.objects.filter(pk=entity_class)
				if entity_class is None or not entity_class.exists():
					raise serializers.ValidationError({
						'entity_class': 'Found no existing object at specified `entity_class` pk.'
					})
				entity_class = entity_class.first()
			elif not isinstance(entity_class, EntityClass):
				entity_class = None

		if entity_class is None:
			raise serializers.ValidationError({
				'entity_class': 'Required `entity_class` field of `pk` type is invalid JSON, or is missing.'
			})

		if instance is not None:
			definition = data.get('definition', instance.definition)
		else:
			definition = data.get('definition')

		if isinstance(definition, str):
			try:
				definition = json.loads(definition)
			except:
				raise serializers.ValidationError({
					'definition': 'Required JSONField `definition` is invalid'
				})

		if not isinstance(definition, dict):
			raise serializers.ValidationError({
				'definition': 'Required JSONField `definition` is missing'
			})

		try:
			json.dumps(definition)
		except:
			raise serializers.ValidationError({
				'definition': 'Template definition is not valid JSON'
			})

		definition = template_utils.get_ordered_definition(definition, clean_fields=True)

		template_fields = definition.get('fields')
		template_details = definition.get('template_details')
		template_sections = definition.get('sections')
		if not isinstance(template_fields, dict):
			raise serializers.ValidationError({
				'definition': 'Template `definition` field requires a `fields` key-value pair of type `dict`'
			})
		elif not isinstance(template_details, dict):
			raise serializers.ValidationError({
				'definition': 'Template `definition` field requires a `template_details` key-value pair of type `dict`'
			})
			raise serializers.ValidationError()
		elif not isinstance(template_sections, list):
			raise serializers.ValidationError({
				'definition': 'Template `definition` field requires a `sections` key-value pair of type `list`'
			})

		name = template_details.get('name')
		if not isinstance(name, str) or gen_utils.is_empty_string(name):
			raise serializers.ValidationError({
				'definition': 'Template requires that the `definition->template_details.name` field be a non-empty string'
			})

		brands = data.get('brands')
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

		data.update({
			'name': template_details.get('name', instance.name if instance else ''),
			'description': template_details.get('description', instance.name if instance else ''),
			'template_version': template_details.get('version', instance.template_version if instance else 1),
			'brands': brands,
			'definition': self.__apply_def_ordering(definition),
			'description': template_details.get('description', ''),
			'created_by': instance.user if instance is not None else user,
			'updated_by': user,
			'entity_class': entity_class,
			'modified': make_aware(datetime.datetime.now()),
		})

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
		"""
		Handle PUT requests to update a Template instance.
		"""
		partial = kwargs.pop('partial', False)
		instance = self.get_object(*args, **kwargs)

		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		try:
			serializer.is_valid(raise_exception=True)
		except serializers.ValidationError as e:
			if isinstance(e.detail, dict):
				detail = {k: v for k, v in e.detail.items() if k not in ('brands', 'entity_class')}
				if len(detail) > 0:
					raise serializers.ValidationError(detail=detail)
		except Exception as e:
			raise e

		data = serializer.data
		data = self.get_serializer().validate(data)
		instance.__dict__.update(**data)
		instance.save()

		return Response(self.get_serializer(instance).data)

	def post(self, request, *args, **kwargs):
		"""
		Handle POST requests to create a new Template instance.
		"""
		serializer = self.get_serializer(data=request.data)
		try:
			serializer.is_valid(raise_exception=True)
		except serializers.ValidationError as e:
			if isinstance(e.detail, dict):
				detail = {k: v for k, v in e.detail.items() if k not in ('brands', 'entity_class')}
				if len(detail) > 0:
					raise serializers.ValidationError(detail=detail)
		except Exception as e:
			raise e

		data = serializer.data
		data = self.get_serializer().validate(data)

		instance, _ = self.model.objects.get_or_create(**data)
		return Response(self.get_serializer(instance).data)
