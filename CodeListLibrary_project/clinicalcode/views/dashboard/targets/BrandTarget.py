"""Brand Dashboard: API endpoints relating to Template model"""
import datetime
import json

from django.utils.timezone import make_aware
from rest_framework import status, serializers

from clinicalcode.entity_utils import model_utils
from clinicalcode.models.Brand import Brand
from .BaseTarget import BaseSerializer, BaseEndpoint


class BrandSerializer(BaseSerializer):
    """
    Serializer for the `Brand` model. This serializer handles serialization, validation, and
    creation/updating of Brand objects. It is used to manage the Brand data when making API
    requests (GET, PUT).
    """

    class Meta:
        model = Brand
        # Fields that should be included in the serialized output
        fields = [
            'id', 'name', 'description', 'website', 'site_title', 'site_description',
            'admins', 'overrides', 'logo_path', 'index_path', 'is_administrable',
            'org_user_managed', 'about_menu', 'allowed_tabs',
            'footer_images',
            'collections_excluded_from_filters'
        ]

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
        data = super(BrandSerializer, self).to_representation(instance)

        if instance is None:
            return data

        # Ensure collections_excluded_from_filters is always a list
        data["collections_excluded_from_filters"] = data.get("collections_excluded_from_filters") or []

        return data

    def create(self, validated_data):
        """
        Create and save a new Brand instance using the validated data.

        Args:
            validated_data (dict): The validated data for creating the Brand.

        Returns:
            Brand: The newly created Brand instance.
        """
        return self.Meta.model.objects.create(**validated_data)

    @staticmethod
    def update(instance, validated_data):
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
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.save()
        return instance

    def validate(self, data):
        """
        Validate the provided data before creating or updating a Brand.

        Ensures that the provided `id` matches the current brand. If the `id` is
        provided and does not match the current brand, a validation error is raised.

        Args:
            data (dict): The data to validate.

        Raises:
            serializers.ValidationError: If the `id` in the data does not match the current brand.

        Returns:
            dict: The validated data.
        """
        current_brand = self._get_brand()
        if data.get('id') and data['id'] != current_brand.id:
            raise serializers.ValidationError("Invalid Brand ID")

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

        This method allows for more control over the query set if needed.

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
        current_brand = model_utils.try_get_brand(request)
        kwargs.update(pk=current_brand.id)
        return self.update(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

