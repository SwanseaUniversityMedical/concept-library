import datetime

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNDataAsset import HDRNDataAsset
from clinicalcode.models.HDRNSite import HDRNSite
from .BaseTarget import BaseEndpoint


class HDRNDataAssetSerializer(serializers.ModelSerializer):
    """
    Serializer for HDRN Data Asset.
    """

    class Meta:
        model = HDRNDataAsset
        fields = ['id', 'name', 'description', 'hdrn_id', 'hdrn_uuid', 'link', 'site', 'years', 'scope',
                  'region', 'purpose', 'collection_period', 'data_level', 'data_categories']

    def to_representation(self, instance):
        """
        Custom method to convert model instance into JSON representation.
        """
        data = super().to_representation(instance)
        # Ensure collections_excluded_from_filters is always a list
        data["data_categories"] = data.get("data_categories") or []
        return data

    def create(self, validated_data):
        """
        Method to create a new HDRNDataAsset instance.
        """
        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        """
        Update an existing HDRNDataAsset instance.
        """
        instance = self._update(instance, validated_data)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.save()
        return instance

    @staticmethod
    def validate(data):
        """
        Custom validation method for `HDRNDataAsset` fields.
        """

        # Validate `data_categories` field (should be a list of integers)
        data_categories = data.get('data_categories', [])
        if not all(isinstance(i, int) for i in data_categories):
            raise serializers.ValidationError('data_categories must be a list of integers.')

        return data

class HDRNDataAssetEndpoint(BaseEndpoint):
    """API views for the HDRN Data Asset model."""

    model = HDRNDataAsset
    queryset = HDRNDataAsset.objects.all()
    serializer_class = HDRNDataAssetSerializer

    reverse_name_default = 'hdrn_data_asset_target'
    reverse_name_retrieve = 'hdrn_data_asset_target_with_id'

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests.
        Retrieves the list of HDRNDataAsset instances or a single instance by ID.
        """
        inst_id = kwargs.get('pk', None)
        if inst_id:
            # Convert pk to integer and validate
            inst_id = gen_utils.try_value_as_type(inst_id, 'int')
            if inst_id is None:
                return Response(
                    data={'detail': 'Expected int-like `pk` parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            kwargs.update(pk=inst_id)
            return self.retrieve(request, *args, **kwargs)

        return self.list(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Handle PUT requests to update an HDRNDataAsset instance.
        """
        return self.update(request, partial=True,  *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to create a new HDRNDataAsset instance.
        """
        return self.create(request, *args, **kwargs)