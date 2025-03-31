import datetime

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from .BaseTarget import BaseEndpoint, BaseSerializer
from .HDRNSiteTarget import HDRNSiteSerializer
from .HDRNCategoryTarget import HDRNCategorySerializer
from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNDataAsset import HDRNDataAsset


class HDRNDataAssetSerializer(BaseSerializer):
    """
    Serializer for HDRN Data Asset.
    """

    # Fields
    site = HDRNSiteSerializer(many=False)
    data_categories = HDRNCategorySerializer(many=True)

    # Appearance
    _str_display = 'name'
    _list_fields = ['id', 'name']

    # Metadata
    class Meta:
        model = HDRNDataAsset
        exclude = ['created', 'modified']
        extra_kwargs = {
            # RO
            'id': { 'read_only': True, 'required': False },
            # WO
			'created': { 'write_only': True, 'read_only': False, 'required': False },
			'modified': { 'write_only': True, 'read_only': False, 'required': False },
            # RO | WO
            'site': { 'required': False },
            'data_categories': { 'required': False },
        }

    # GET
    def resolve_options(self):
        return list(self.Meta.model.objects.all().values('name', 'pk'))

    # POST / PUT
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

    # Instance & Field validation
    @staticmethod
    def validate(data):
        """
        Custom validation method for `HDRNDataAsset` fields.
        """

        # Validate `data_categories` field (should be a list of integers)
        data_categories = data.get('data_categories', [])
        if not all(isinstance(i, int) for i in data_categories):
            raise serializers.ValidationError('data_categories must be a list of integers.')

        site = data.get('site', None)
        if site is not None and not isinstance(site, int):
            raise serializers.ValidationError('site must be a `pk` value.')

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
