"""Brand Dashboard: API endpoints relating to Template model"""
from rest_framework import status, serializers
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from rest_framework.response import Response

import datetime

from .UserTarget import UserSerializer
from .BaseTarget import BaseSerializer, BaseEndpoint
from clinicalcode.models.Brand import Brand
from clinicalcode.entity_utils import model_utils


User = get_user_model()


class BrandSerializer(BaseSerializer):
    """
    Serializer for the `Brand` model. This serializer handles serialization, validation, and
    creation/updating of Brand objects. It is used to manage the Brand data when making API
    requests (GET, PUT).
    """

    # Fields
    admins = UserSerializer(
        many=True,
        help_text=(
            'Specifies a set of Users to be designated as administrators, this grants each '
            'of them access to this dashboard.'
        )
    )

    # Appearance
    _str_display = 'name'
    _list_fields = ['id', 'name']
    _item_fields = ['id', 'name', 'website', 'description', 'site_title', 'site_description', 'admins']

    # Metadata
    class Meta:
        model = Brand
        # Fields that should be included in the serialized output
        exclude = [
            'logo_path', 'index_path', 'about_menu',
            'allowed_tabs', 'footer_images', 'is_administrable',
            'collections_excluded_from_filters', 'created', 'modified',
            'org_user_managed', 'users',
        ]
        extra_kwargs = {
            # RO
            'id': { 'read_only': True, 'required': False },
            'name': { 'read_only': True, 'required': False },
            'logo_path': { 'read_only': True, 'required': False },
            'index_path': { 'read_only': True, 'required': False },
            'about_menu': { 'read_only': True, 'required': False },
            'allowed_tabs': { 'read_only': True, 'required': False },
            'footer_images': { 'read_only': True, 'required': False },
            'is_administrable': { 'read_only': True, 'required': False },
            'collections_excluded_from_filters': { 'read_only': True, 'required': False },
            # WO
            'created': { 'write_only': True, 'read_only': False, 'required': False },
            'modified': { 'write_only': True, 'read_only': False, 'required': False },
            'created_by': { 'write_only': True, 'read_only': False, 'required': False },
            'updated_by': { 'write_only': True, 'read_only': False, 'required': False },
            # WO | RO
            'overrides': { 'help_text': 'Overrides website behaviour for this specific Brand, please seek Administrator advice before modifying.' },
            'description': { 'style': { 'as_type': 'TextField' }, 'help_text': 'Human-friendly description of the Brand (appears on the home page)' },
            'website': { 'help_text': 'Specifies the Brand\'s website (used for back-linking)' },
            'site_title': { 'help_text': 'Specifies the title of the website, e.g. as it appears within the browser tab' },
            'site_description': { 'help_text': 'Optionally specify the site description metadata tag, e.g. as it appears on search engines' },
        }

    # GET
    def to_representation(self, instance):
        """
        Convert a Brand instance into a JSON-serializable dictionary.

        Ensures that the `collections_excluded_from_filters` field is always returned
        as a list, even if it is empty or None.

        Args:
            instance (Brand): The Brand instance to serialize.

        Returns:
            dict: The serialized Brand data.
        """
        if isinstance(instance, list):
            instance = self.Meta.model.objects.filter(pk__in=instance)
            instance = instance if instance.exists() else None
        elif isinstance(instance, int):
            instance = self.Meta.model.objects.filter(pk=instance)
            if instance.exists():
                instance = instance.first()
            else:
                instance = None

        if instance is not None:
            data = super(BrandSerializer, self).to_representation(instance)
            return data
        return None

    def resolve_format(self):
        return { 'type': 'ForeignKey' }

    def resolve_options(self):
        return list(self.Meta.model.objects.all().values('name', 'pk'))

    # POST / PUT
    def create(self, validated_data):
        """
        Create and save a new Brand instance using the validated data.

        Args:
            validated_data (dict): The validated data for creating the Brand.

        Returns:
            Brand: The newly created Brand instance.
        """
        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        """
        Update an existing Brand instance with the validated data.

        Updates each field of the instance with the corresponding validated data and
        saves the changes. Additionally, updates the `modified` timestamp to the current time.

        Args:
            instance (Brand): The Brand instance to update.
            validated_data (dict): The validated data to update the Brand with.

        Returns:
            Brand: The updated Brand instance.
        """
        instance = self._update(instance, validated_data)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.save()
        return instance

    # Instance & Field validation
    def validate(self, data):
        """
        Validate the provided data before creating or updating a Brand.

        Args:
            data (dict): The data to validate.

        Returns:
            dict: The validated data.
        """
        user = self._get_user()
        instance = getattr(self, 'instance') if hasattr(self, 'instance') else None

        prev_users = instance.users.all() if instance is not None else User.objects.none()
        prev_admins = instance.admins.all() if instance is not None else User.objects.none()

        users = data.get('users') if isinstance(data.get('users'), list) else prev_users
        users = list(User.objects.filter(id__in=users))
        if user is not None and not next((x for x in users if x.id != user.id), None):
            users.append(user)

        admins = data.get('admins') if isinstance(data.get('admins'), list) else prev_admins
        admins = list(User.objects.filter(id__in=admins))
        if user is not None and not next((x for x in admins if x.id != user.id), None):
            admins.append(user)

        data.update({
            'users': users,
            'admins': admins,
        })

        return data


class BrandEndpoint(BaseEndpoint):
    """
    API endpoint for managing `Brand` resources.

    This view handles API requests related to the `Brand` model, including retrieving,
    updating, and creating Brand instances. It uses the `BrandSerializer` to handle
    serialization and validation.
    """

    model = Brand
    fields = []
    serializer_class = BrandSerializer
    queryset = Brand.objects.all()

    reverse_name_default = 'brand_target'  # Default reverse URL name for this endpoint

    def get_queryset(self, *args, **kwargs):
        """
        Override the `get_queryset` method to return the queryset for the `Brand` model.

        Args:
            *args: Positional arguments passed to the method.
            **kwargs: Keyword arguments passed to the method.

        Returns:
            QuerySet: A queryset of all Brand objects.
        """
        return self.queryset

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to retrieve the current brand.

        This method retrieves the current brand associated with the request and
        returns its data serialized via `BrandSerializer`.

        Args:
            request (Request): The incoming request.

        Returns:
            Response: The serialized data of the current brand.
        """
        current_brand = model_utils.try_get_brand(request)
        if current_brand is None:
            return Response(
                data={ 'detail': 'Unknown Brand context' },
                status=status.HTTP_400_BAD_REQUEST
            )
        kwargs.update(pk=current_brand.id)
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Handle PUT requests to update the current brand.

        This method retrieves the current brand associated with the request, validates
        the data, and updates the brand's information.

        Args:
            request (Request): The incoming request.
            *args: Positional arguments passed to the method.
            **kwargs: Keyword arguments passed to the method.

        Returns:
            Response: The response containing the updated brand data.
        """
        partial = kwargs.pop('partial', False)
        instance = model_utils.try_get_brand(request)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            if isinstance(e.detail, dict):
                detail = {k: v for k, v in e.detail.items() if k not in ('users', 'admins')}
                if len(detail) > 0:
                    raise serializers.ValidationError(detail=detail)
        except Exception as e:
            raise e

        data = serializer.data
        data = self.get_serializer(instance).validate(data)

        admins = data.pop('admins', [])
        users = data.pop('users', [])

        instance.__dict__.update(**data)
        instance.save()

        instance.admins.set(admins)
        instance.users.set(users)

        return Response(self.get_serializer(instance).data)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to create a new Brand instance.
        """
        raise Response(status=status.HTTP_403_PERMISSION_DENIED)
