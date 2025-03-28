"""Brand Dashboard: API endpoints relating to Template model"""
import datetime

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.Tag import Tag
from .BaseTarget import BaseSerializer, BaseEndpoint


class TagSerializer(BaseSerializer):
    """Responsible for serialising the `Brand` model and to handle PUT/POST validation"""
    class Meta:
        model = Tag
        fields = [
            'id',
            'description',
            'display',
            'tag_type',
            'collection_brand_id',
        ]

    # GET
    def to_representation(self, instance):

        data = super(TagSerializer, self).to_representation(instance)

        return data

    def create(self, validated_data):
        user = self._get_user()
        validated_data.update({
            'created_by': user,
            'updated_by': user,
        })
        return self.Meta.model.objects.create(**validated_data)
    # POST / PUTx
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self._get_user()
        instance.modified = make_aware(datetime.datetime.now())
        instance.save()
        return instance

    # Instance & Field validation
    def validate(self, data):
        current_brand = self._get_brand(),
        data_brand = data.get('collection_brand_id')
        tag_type = data.get('tag_type')
        display = data.get('display')

        if isinstance(data_brand, Brand):
            if data_brand.id != current_brand.id:
                raise serializers.ValidationError("Invalid Brand")
        elif data_brand != current_brand.id:
            raise serializers.ValidationError("Invalid Brand")

        if display not in dict(self.model.DISPLAY_CHOICES).keys():
            raise serializers.ValidationError("Invalid display choice.")
        if tag_type not in dict(self.model.TAG_TYPES).keys():
            raise serializers.ValidationError("Invalid Tag Type")
        return data


class TagEndpoint(BaseEndpoint):
    """Responsible for API views relating to `Template` model accessed via Brand dashboard"""

    # Metadata
    model = Tag
    fields = []
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    # View behaviour
    reverse_name_default = 'brand_tag_target'
    # View behaviour
    reverse_name_retrieve = 'brand_tag_target_with_id'

    # Endpoint methods
    def get(self, request, *args, **kwargs):
        inst_id = kwargs.get('pk', None)
        if inst_id:
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
        return self.update(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
