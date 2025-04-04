import datetime

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from .BaseTarget import BaseEndpoint, BaseSerializer
from .HDRNSiteTarget import HDRNSiteSerializer
from .HDRNCategoryTarget import HDRNCategorySerializer
from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNSite import HDRNSite
from clinicalcode.models.HDRNDataAsset import HDRNDataAsset
from clinicalcode.models.HDRNDataCategory import HDRNDataCategory


class HDRNDataAssetSerializer(BaseSerializer):
    """
    Serializer for HDRN Data Asset.
    """

    # Fields
    site = HDRNSiteSerializer(many=False, required=False)
    data_categories = HDRNCategorySerializer(many=True, required=False)

    # Appearance
    _str_display = 'name'
    _list_fields = ['id', 'name']
    _item_fields = ['id', 'name', 'description']

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
            'name': { 'min_length': 3, 'required': True },
            'site': { 'required': False },
            'data_categories': { 'required': False },
            'scope': { 'style': { 'as_type': 'TextField' } },
            'purpose': { 'style': { 'as_type': 'TextField' } },
            'description': { 'style': { 'as_type': 'TextField' } },
            'collection_period': { 'style': { 'as_type': 'TextField' } },
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
    def validate(self, data):
        """
        Custom validation method for `HDRNDataAsset` fields.
        """
        # Validate `data_categories` field (should be a list of integers)
        data_categories = data.get('data_categories', [])
        if isinstance(data_categories, list) and not all(isinstance(i, int) for i in data_categories):
            raise serializers.ValidationError({
                'data_categories': 'Data Categories, if provided, must be a list of pk.'
            })
        elif isinstance(data_categories, list):
            data_categories = HDRNDataCategory.objects.filter(pk__in=data_categories)
            if data_categories is None or not data_categories.exists():
                raise serializers.ValidationError({
                    'data_categories': 'Failed to find specified `data_categories`'
                })
            data_categories = list(data_categories.values_list('id', flat=True))
        else:
            data_categories = None

        site = data.get('site', None)
        if site is not None and not isinstance(site, int):
            raise serializers.ValidationError({
                'site': 'Site, if provided, must be a valid `pk` value'
            })
        elif isinstance(site, int):
            site = HDRNSite.objects.filter(pk=site)
            if site is None or not site.exists():
                raise serializers.ValidationError({
                    'site': 'Found no existing object at specified `site` pk'
                })
            site = site.first()
        else:
            site = None

        uuid = data.get('hdrn_uuid')
        if not gen_utils.is_valid_uuid(uuid):
            uuid = None

        data.update({ 'data_categories': data_categories, 'site': site, 'hdrn_uuid': uuid })
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
        partial = kwargs.pop('partial', False)
        instance = self.get_object(*args, **kwargs)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            if isinstance(e.detail, dict):
                detail = {k: v for k, v in e.detail.items() if k not in ('site', 'data_categories')}
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
        Handle POST requests to create a new HDRNDataAsset instance.
        """
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            if isinstance(e.detail, dict):
                detail = {k: v for k, v in e.detail.items() if k not in ('site', 'data_categories')}
                if len(detail) > 0:
                    raise serializers.ValidationError(detail=detail)
        except Exception as e:
            raise e

        data = serializer.data
        data = self.get_serializer().validate(data)

        instance, _ = self.model.objects.get_or_create(**data)
        return Response(self.get_serializer(instance).data)
