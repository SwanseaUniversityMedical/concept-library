"""Brand Dashboard: API endpoints relating to default Django User model"""
from rest_framework import status, serializers
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.response import Response
from django.contrib.auth.models import Group

from .BaseTarget import BaseSerializer, BaseEndpoint
from clinicalcode.entity_utils import constants, gen_utils, model_utils


User = get_user_model()


class UserSerializer(BaseSerializer):
	"""Responsible for serialising the `User` model and to handle PUT/POST validation"""

	# Const
	MODERATOR_GROUP = Group.objects.get(name__iexact='Moderators')

	# Fields
	is_moderator = serializers.BooleanField(default=False, initial=False)

	# Appearance
	_str_display = 'username'
	_list_fields = ['id', 'username', 'first_name', 'last_name']
	_item_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login']

	# Metadata
	class Meta:
		model = User
		fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_moderator']
		extra_kwargs = {
			# RO
			'id': { 'read_only': True, 'required': False },
			'last_login': { 'read_only': True, 'required': False },
			'date_joined': { 'read_only': True, 'required': False },
			# WO
			'groups': { 'write_only': True, 'required': False },
			'password': { 'write_only': True },
			'is_superuser': { 'write_only': True, 'required': False },
			'is_staff': { 'write_only': True, 'required': False },
			'is_active': { 'write_only': True, 'required': False },
			'user_permissions': { 'write_only': True, 'required': False },
			# RO | WO
			'email': { 'required': True },
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

		if records is None:
			return list()

		return list(records.annotate(name=F('username')).values('name', 'pk'))

	def create(self, validated_data):
		validated_data.update({
			'is_staff': False,
			'is_active': True,
			'is_superuser': False,
		})

		user = self._create(self.Meta.model, validated_data)
		user.save()

		brand = self._get_brand()
		if brand is not None:
			rel = brand.users.filter(id=user.id)
			if not rel.exists():
				brand.users.add(user)

		is_mod = validated_data.pop('is_moderator', False)
		if isinstance(is_mod, bool) and is_mod:
			user.groups.add(self.MODERATOR_GROUP)

		# TODO:
		# 	1. Create user with randomly seeded pwd
		# 	2. Send invite link via e-mail to avoid pwd sharing
		#

		return user

	def update(self, instance, validated_data):
		brand = self._get_brand()

		user = self._update(instance, validated_data)
		user.save()

		if brand is not None:
			rel = brand.users.filter(id=user.id)
			if not rel.exists():
				brand.users.add(user)

		is_mod = validated_data.pop('is_moderator', False)
		if isinstance(is_mod, bool):
			if is_mod:
				user.groups.add(self.MODERATOR_GROUP)
			elif user.groups.filter(pk=self.MODERATOR_GROUP.pk).exists():
				user.groups.remove(self.MODERATOR_GROUP)

		return user


class UserEndpoint(BaseEndpoint):
	"""Responsible for API views relating to `User` model accessed via Brand dashboard"""

	# Metadata
	model = User
	fields = []
	queryset = User.objects.all()
	serializer_class = UserSerializer

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
			page_obj = Page(User.objects.none(), 0, Paginator([], page_size, allow_empty_first_page=True))
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
					records = User.objects.filter(Q(accessible_brands__id__in=allowed_brands) | Q(accessible_brands__id__isnull=allow_null))
				elif isinstance(allowed_brands, list):
					records = User.objects.filter(accessible_brands__id__in=allowed_brands)
				elif isinstance(allow_null, bool) and allow_null:
					records = User.objects.filter(accessible_brands__id__isnull=True)

			if records is None:
				records = User.objects.filter(accessible_brands__id=brand.id)
		else:
			records = User.objects.all()

		search = params.get('search', None)
		query = gen_utils.parse_model_field_query(User, params, ignored_fields=['password'])

		if query is not None:
			records = records.filter(**query)
		
		if not gen_utils.is_empty_string(search) and len(search) >= 3:
			records = records.filter(
				Q(username__icontains=search) | \
				Q(first_name__icontains=search) | \
				Q(last_name__icontains=search) | \
				Q(email__icontains=search)
			)

		return records
