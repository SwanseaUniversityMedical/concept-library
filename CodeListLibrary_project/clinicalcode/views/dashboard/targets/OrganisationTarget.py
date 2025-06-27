"""Brand Dashboard: API endpoints relating to Organisation model"""
from django.db import transaction
from rest_framework import status, serializers
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.response import Response

from .UserTarget import UserSerializer
from .BaseTarget import BaseSerializer, BaseEndpoint
from .BrandTarget import BrandSerializer
from clinicalcode.entity_utils import constants, gen_utils, model_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Organisation import Organisation, OrganisationAuthority, OrganisationMembership


User = get_user_model()


class OrganisationAuthoritySerializer(BaseSerializer):
	"""Responsible for serialising the `Organisation.brands` through-field model and to handle PUT/POST validation"""

	# Fields
	brand = BrandSerializer(many=False)

	# Appearance
	_str_display = 'id'

	# Metadata
	class Meta:
		model = OrganisationAuthority
		fields = '__all__'
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
		}

	# GET
	def resolve_format(self):
		return {
			'type': 'through',
			'component': 'OrgAuthoritySelector',
			'fields': {
				'brand': 'ForeignKey',
				'can_post': 'BooleanField',
				'can_moderate': 'BooleanField',
			}
		}

	def resolve_options(self):
		return {
			'brand': list(Brand.objects.all().values('name', 'pk')),
		}


class OrganisationMembershipSerializer(BaseSerializer):
	"""Responsible for serialising the `Organisation.members` through-field model and to handle PUT/POST validation"""

	# Fields
	user = UserSerializer(many=False)
	role = serializers.ChoiceField(choices=[(e.value, e.name) for e in constants.ORGANISATION_ROLES])

	# Appearance
	_str_display = 'id'

	# Metadata
	class Meta:
		model = OrganisationMembership
		fields = '__all__'
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
			'joined': { 'read_only': True, 'required': False },
			# WO | RO
			'description': { 'style': { 'as_type': 'TextField' } },
		}

	# GET
	def resolve_format(self):
		return {
			'type': 'through',
			'component': 'OrgMemberSelector',
			'fields': {
				'user': 'ForeignKey',
				'role': 'ChoiceField',
			}
		}

	def resolve_options(self):
		brand = self._get_brand()

		records = None
		if brand is not None:
			vis_rules = brand.get_vis_rules()
			if isinstance(vis_rules, dict):
				allow_null = vis_rules.get('allow_null')
				allowed_brands = vis_rules.get('ids')
				if isinstance(allowed_brands, list) and isinstance(allow_null, bool) and allow_null:
					records = User.objects.filter(Q(accessible_brands__id__isnull=True) | Q(accessible_brands__id__in=allowed_brands))
				elif isinstance(allowed_brands, list):
					records = User.objects.filter(accessible_brands__id__in=allowed_brands)
				elif isinstance(allow_null, bool) and allow_null:
					records = User.objects.filter(Q(accessible_brands__id__isnull=True) | Q(accessible_brands__id__in=[brand.id]))

			if records is None:
				records = User.objects.filter(accessible_brands__id=brand.id)
		else:
			records = User.objects.all()

		return {
			'role': [{ 'name': e.name, 'pk': e.value } for e in constants.ORGANISATION_ROLES],
			'user': list(records.annotate(name=F('username')).values('name', 'pk')) if records is not None else [],
		}


class OrganisationSerializer(BaseSerializer):
	"""Responsible for serialising the `Organisation` model and to handle PUT/POST validation"""

	# Fields
	owner = UserSerializer(
		required=True,
		many=False,
		help_text=(
			'The owner of an organisation is automatically given administrative privileges '
			'within an Organisation and does not need to be included as a Member.'
		)
	)
	brands = OrganisationAuthoritySerializer(
		source='organisationauthority_set',
		many=True,
		help_text=(
			'Specifies the visibility & the control this Organisation has on different Brands.'
		)
	)
	members = OrganisationMembershipSerializer(
		source='organisationmembership_set',
		many=True,
		help_text=(
			'Describes a set of users associated with this Organisation and the role they play within it. '
			'Note that the owner of an Organisation does not need to be included as a member of an Organisation, '
			'they are automatically assigned an Administrative role.'
		)
	)

	# Appearance
	_str_display = 'name'
	_list_fields = ['id', 'name', 'owner']
	_item_fields = [
		'id', 'slug', 'name',
		'description', 'website', 'email',
		'owner', 'members', 'brands',
	]

	# Metadata
	class Meta:
		model = Organisation
		exclude = ['created']
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
			'slug': { 'read_only': True, 'required': False },
			# WO
			'created': { 'write_only': True, 'required': False },
			# WO | RO
			'email': { 'help_text': 'Specifies this Organisation\'s e-mail address (optional).'},
			'website': { 'help_text': 'Specifies this Organisation\'s website (optional).'},
		}

	# Instance & Field validation
	def validate(self, data):
		"""
		Validate the provided data before creating or updating a Brand.

		Args:
				data (dict): The data to validate.

		Returns:
				dict: The validated data.
		"""
		instance = getattr(self, 'instance') if hasattr(self, 'instance') else None
		current_brand = self._get_brand()

		prev_brands = instance.admins.all() if instance is not None else OrganisationAuthority.objects.none()
		prev_members = instance.members.all() if instance is not None else OrganisationMembership.objects.none()

		data_brands = data.get('brands') if isinstance(data.get('brands'), list) else None
		if isinstance(data_brands, list):
			brands = []
			for x in data_brands:
				brand = Brand.objects.filter(id=x.get('brand_id', -1))
				if not brand.exists():
					continue

				brands.append({
					'brand': brand.first(),
					'can_post': not not x.get('can_post', False),
					'can_moderate': not not x.get('can_moderate', False),
				})

			if current_brand and not next((x for x in brands if x.get('brand').id == current_brand.id), None):
				brands.append({
					'brand': current_brand,
					'can_post': False,
					'can_moderate': False,
				})
		else:
			brands = prev_brands

		data_members = data.get('members') if isinstance(data.get('members'), list) else None
		if isinstance(data_members, list):
			members = []
			for x in data_members:
				user = User.objects.filter(id=x.get('user_id', -1))
				if not user.exists():
					continue

				members.append({
					'user': user.first(),
					'role': x.get('role', 0),
				})
		else:
			members = prev_members

		owner = data.get('owner', instance.owner if instance is not None else None)
		if isinstance(owner, int):
			owner = User.objects.filter(id=owner)
			if owner is not None or owner.exists():
				owner = owner.first()

		if not isinstance(owner, User):
			raise serializers.ValidationError({
					'owner': 'The `owner` field must be supplied.'
			})

		data.update({
			'owner': owner,
			'brands': brands,
			'members': members,
		})

		return data

class OrganisationEndpoint(BaseEndpoint):
	"""Responsible for API views relating to `Organisation` model accessed via Brand dashboard"""

	# Metadata
	model = Organisation
	fields = []
	queryset = Organisation.objects.all()
	serializer_class = OrganisationSerializer

	# View behaviour
	reverse_name_default = 'brand_user_target'
	reverse_name_retrieve = 'brand_user_target_with_id'

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
		Handle PUT requests to update an Organisation instance.
		"""
		partial = kwargs.pop('partial', False)
		instance = self.get_object(*args, **kwargs)

		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		try:
			serializer.is_valid(raise_exception=True)
		except serializers.ValidationError as e:
			if isinstance(e.detail, dict):
				detail = {k: v for k, v in e.detail.items() if k not in ('owner', 'brands', 'members')}
				if len(detail) > 0:
					raise serializers.ValidationError(detail=detail)
		except Exception as e:
			raise e

		try:
			data = serializer.data
			data = self.get_serializer().validate(data)

			brands = data.pop('brands', None)
			members = data.pop('members', None)

			with transaction.atomic():
				instance.__dict__.update(**data)
				instance.owner = data.get('owner')
				instance.save()

				if isinstance(brands, list):
					instance.brands.clear()

					brands = Organisation.brands.through.objects.bulk_create([
						Organisation.brands.through(**({ 'organisation': instance } | obj)) for obj in brands
					])
				elif not brands is None:
					instance.brands.set(brands)
				else:
					instance.brands.set([])

				if isinstance(members, list):
					instance.members.clear()

					members = Organisation.members.through.objects.bulk_create([
						Organisation.members.through(**({ 'organisation': instance } | obj)) for obj in members
					])
				elif not members is None:
					instance.members.set(members)
				else:
					instance.members.set([])
		except Exception as e:
			raise e
		else:
			return Response(self.get_serializer(instance).data)

	def post(self, request, *args, **kwargs):
		"""
		Handle POST requests to create a new Organisation instance.
		"""
		serializer = self.get_serializer(data=request.data)
		try:
			serializer.is_valid(raise_exception=True)
		except serializers.ValidationError as e:
			if isinstance(e.detail, dict):
				detail = {k: v for k, v in e.detail.items() if k not in ('owner', 'brands', 'members')}
				if len(detail) > 0:
					raise serializers.ValidationError(detail=detail)
		except Exception as e:
			raise e

		try:
			data = serializer.data
			data = self.get_serializer().validate(data)

			brands = data.pop('brands', None)
			members = data.pop('members', None)

			with transaction.atomic():
				instance, created = self.model.objects.get_or_create(**data)
				if created:
					if isinstance(brands, list):
						instance.brands.clear()

						brands = Organisation.brands.through.objects.bulk_create([
							Organisation.brands.through(**({ 'organisation': instance } | obj)) for obj in brands
						])
					elif not brands is None:
						instance.brands.set(brands)
					else:
						instance.brands.set([])

				if isinstance(members, list):
					instance.members.clear()

					members = Organisation.members.through.objects.bulk_create([
						Organisation.members.through(**({ 'organisation': instance } | obj)) for obj in members
					])
				elif not members is None:
					instance.members.set(members)
				else:
					instance.members.set([])
		except Exception as e:
			raise e
		else:
			return Response(self.get_serializer(instance).data)

	# Override queryset
	def list(self, request, *args, **kwargs):
		params = self._get_query_params(request)

		page = gen_utils.try_value_as_type(params.get('page'), 'int', default=1)
		page = max(page, 1)

		page_size = params.get('page_size', '1')
		if page_size not in constants.PAGE_RESULTS_SIZE:
			page_size = constants.PAGE_RESULTS_SIZE.get('1')
		else:
			page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

		records = self.get_queryset(request, **params)
		if records is None:
			page_obj = Page(Organisation.objects.none(), 0, Paginator([], page_size, allow_empty_first_page=True))
		else:
			records = records.order_by('id')
			pagination = Paginator(records, page_size, allow_empty_first_page=True)
			try:
				page_obj = pagination.page(page)
			except EmptyPage:
				page_obj = pagination.page(pagination.num_pages)

		results = self.serializer_class(page_obj.object_list, many=True)
		response = self._format_list_data({
			'detail': self._format_page_details(page_obj),
			'results': results.data,
		})

		self._format_list_data(response)
		return Response(response)

	def get_queryset(self, *args, **kwargs):
		request = self.request

		params = getattr(self, 'filter', None)
		if isinstance(params, dict):
			params = kwargs | params
		else:
			params = kwargs

		brand = model_utils.try_get_brand(request)
		records = None
		if brand is not None:
			vis_rules = brand.get_vis_rules()
			if isinstance(vis_rules, dict):
				allow_null = vis_rules.get('allow_null')
				allowed_brands = vis_rules.get('ids')
				if isinstance(allowed_brands, list) and isinstance(allow_null, bool) and allow_null:
					records = Organisation.objects.filter(
						Q(brands__isnull=allow_null) | \
						Q(brands__in=allowed_brands)
					)
				elif isinstance(allowed_brands, list):
					records = Organisation.objects.filter(brands__in=allowed_brands)
				elif isinstance(allow_null, bool) and allow_null:
					records = Organisation.objects.filter(Q(brands__isnull=True) | Q(brands__in=[brand.id]))

			if records is None:
				records = Organisation.objects.filter(brands__id__contains=brand.id)
		else:
			records = Organisation.objects.all()

		page = gen_utils.try_value_as_type(params.get('page'), 'int', default=1)
		page = max(page, 1)

		search = params.get('search', None)
		query = gen_utils.parse_model_field_query(Organisation, params, ignored_fields=['description'])

		if query is not None:
			records = records.filter(**query)

		if not gen_utils.is_empty_string(search) and len(search) >= 3:
			records = records.filter(
				Q(name__icontains=search) | \
				Q(email__icontains=search) | \
				Q(description__icontains=search)
			)

		return records
