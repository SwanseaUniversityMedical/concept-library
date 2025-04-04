"""Brand Dashboard: API endpoints relating to default Django User model"""
from django.conf import settings
from rest_framework import status, serializers, exceptions
from django.db.models import Q, F
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.core.paginator import EmptyPage, Paginator, Page
from django.template.loader import render_to_string
from rest_framework.response import Response
from django.utils.regex_helper import _lazy_re_compile
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator

import re
import uuid

from .BaseTarget import BaseSerializer, BaseEndpoint
from clinicalcode.entity_utils import constants, gen_utils, model_utils, email_utils, permission_utils


User = get_user_model()


class UserSerializer(BaseSerializer):
	"""Responsible for serialising the `User` model and to handle PUT/POST validation"""

	# Const
	MODERATOR_GROUP = Group.objects.get(name__iexact='Moderators')
	EMAIL_PATTERN = _lazy_re_compile(r'\b([^\s\/@:"]+)(?<=[\w])@(\S+)\.([\w]+)\b', re.MULTILINE | re.IGNORECASE)

	# Fields
	is_moderator = serializers.BooleanField(default=False, initial=False, help_text='Specifies whether this User is a global moderator (unrelated to organisations/sites)')

	# Appearance
	_str_display = 'username'
	_list_fields = ['id', 'username', 'first_name', 'last_name']
	_item_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'date_joined', 'last_login']
	_features = {
		'create': {
			'note': (
				'Please note that creating a new User account will send an e-mail to the specified address. '
				'The e-mail will contain a link for the User to follow, prompting them to enter their password.\n\n'
				'Beware that the e-mail might appear in the User\'s spam folder, please recommend this as a resolution if the e-mail cannot be found.'
			)
		},
		'update': {
			'actionbar': ['reset_pwd'], 
		},
	}

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

	# GET
	def to_representation(self, instance):
		data = super(UserSerializer, self).to_representation(instance)
		data.update({ 'is_moderator': permission_utils.is_member(instance, 'Moderators')})
		return data

	def resolve_format(self):
		return { 'type': 'ForeignKey' }

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

	def send_pwd_email(self, request, user):
		if not isinstance(user, User) or not hasattr(user, 'id') or not isinstance(user.id, int):
			raise exceptions.APIException('User model must be saved before sending the reset e-mail.')

		brand = self._get_brand()
		email = getattr(user, 'email')
		username = getattr(user, 'username')
		if not isinstance(email, str) or gen_utils.is_empty_string(email) or not self.EMAIL_PATTERN.match(email):
			raise exceptions.APIException(f'Failed to match e-mail pattern for User\'s known e-mail: {email}')

		user_pk_bytes = force_bytes(User._meta.pk.value_to_string(user))
		brand_title = model_utils.try_get_brand_string(brand, 'site_title', default='Concept Library')

		email_subject = f'{brand_title} - Organisation Invite'
		email_content = render_to_string(
			'clinicalcode/email/account_inv_email.html',
			{
				'uid': urlsafe_base64_encode(user_pk_bytes),
				'token': default_token_generator.make_token(user),
				'username': username,
			},
			request=request
		)

		if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE: 
			try:
				branded_imgs = email_utils.get_branded_email_images(brand)

				msg = EmailMultiAlternatives(
					email_subject,
					email_content,
					settings.DEFAULT_FROM_EMAIL,
					to=[email]
				)
				msg.content_subtype = 'related'
				msg.attach_alternative(email_content, 'text/html')

				msg.attach(email_utils.attach_image_to_email(branded_imgs.get('apple', 'img/email_images/apple-touch-icon.jpg'), 'mainlogo'))
				msg.attach(email_utils.attach_image_to_email(branded_imgs.get('logo', 'img/email_images/combine.jpg'), 'sponsors'))
				msg.send()
				return True
			except BadHeaderError as error:
				raise exceptions.APIException(f'Failed to send emails to:\n- Targets: {email}\n-Error: {str(error)}')
		# else:
		# 	print(email, '->', email_content)

	# POST / PUT
	def create(self, validated_data):
		request = self.context.get('request')

		validated_data.update({
			'is_staff': False,
			'is_active': True,
			'is_superuser': False,
			'password': uuid.uuid4(),
		})

		is_mod = validated_data.pop('is_moderator', False)
		user = self._create(self.Meta.model, validated_data)
		user.save()

		brand = self._get_brand()
		if brand is not None:
			rel = brand.users.filter(id=user.id)
			if not rel.exists():
				brand.users.add(user)

		if isinstance(is_mod, bool) and is_mod:
			user.groups.add(self.MODERATOR_GROUP)

		self.send_pwd_email(request, user)
		return user

	def update(self, instance, validated_data):
		brand = self._get_brand()

		is_mod = validated_data.pop('is_moderator', False)
		user = self._update(instance, validated_data)
		user.save()

		if brand is not None:
			rel = brand.users.filter(id=user.id)
			if not rel.exists():
				brand.users.add(user)

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
		target = request.headers.get('X-Target', None)
		if isinstance(target, str) and target.lower() == 'reset_pwd':
			instance = self.get_object(*args, **kwargs)
			if isinstance(instance, User):
				self.get_serializer().send_pwd_email(request, instance)
				return Response({ 'sent': True, 'user_id': instance.id })

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
