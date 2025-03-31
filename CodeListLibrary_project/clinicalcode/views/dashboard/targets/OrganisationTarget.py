"""Brand Dashboard: API endpoints relating to Organisation model"""
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
			'fields': {
				'brand': 'ForeignKey',
				'can_post': 'BooleanField',
				'can_moderate': 'BooleanField',
			}
		}

	def resolve_options(self):
		return list(Brand.objects.all().values('name', 'pk'))


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
		}

	# GET
	def resolve_format(self):
		return {
			'type': 'through',
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
				if isinstance(allowed_brands, list) and isinstance(allow_null, bool):
					records = User.objects.filter(Q(accessible_brands__id__in=allowed_brands) | Q(accessible_brands__id__isnull=allow_null))
				elif isinstance(allowed_brands, list):
					records = User.objects.filter(accessible_brands__id__in=allowed_brands)
				elif isinstance(allow_null, bool) and allow_null:
					records = User.objects.filter(accessible_brands__id__isnull=True)

			if records is None:
				records = User.objects.filter(accessible_brands__id=brand.id)
		else:
			records = User.objects.all()

		res = {
			'role': [{ 'name': e.name, 'pk': e.value } for e in constants.ORGANISATION_ROLES],
		}

		if records is not None:
			res.update(user=list(records.annotate(name=F('username')).values('name', 'pk')))
		
		return res


class OrganisationSerializer(BaseSerializer):
	"""Responsible for serialising the `Organisation` model and to handle PUT/POST validation"""

	# Fields
	owner = UserSerializer(many=False)
	brands = OrganisationAuthoritySerializer(source='organisationauthority_set', many=True)
	members = OrganisationMembershipSerializer(source='organisationmembership_set', many=True)

	# Appearance
	_str_display = 'name'
	_list_fields = ['id', 'name', 'owner']
	_item_fields = ['id', 'slug', 'name', 'website', 'email', 'description']

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
		}


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
		return self.update(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		return self.create(request, *args, **kwargs)

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
				if isinstance(allowed_brands, list) and isinstance(allow_null, bool):
					records = Organisation.objects.filter(
						Q(brands__in=allowed_brands) | \
						Q(brands__isnull=allow_null)
					)
				elif isinstance(allowed_brands, list):
					records = Organisation.objects.filter(brands__in=allowed_brands)
				elif isinstance(allow_null, bool) and allow_null:
					records = Organisation.objects.filter(brands__isnull=True)

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
