"""Brand Dashboard: API endpoints relating to Template model"""
import datetime

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from .BaseTarget import BaseSerializer, BaseEndpoint
from clinicalcode.models.Tag import Tag
from clinicalcode.models.Brand import Brand
from clinicalcode.entity_utils import gen_utils


class TagSerializer(BaseSerializer):
    """Responsible for serialising the `Brand` model and to handle PUT/POST validation"""

    # Fields
    display = serializers.ChoiceField(choices=[*Tag.DISPLAY_CHOICES])
    tag_type = serializers.ChoiceField(choices=[*Tag.TAG_TYPES])

    # Appearance
    _str_display = 'name'
    _list_fields = ['id', 'description', 'tag_type']
    _item_fields = ['id', 'description', 'tag_type', 'display']

	# Metadata
    class Meta:
        model = Tag
        exclude = ['collection_brand', 'created_by', 'updated_by', 'created', 'modified']
        extra_kwargs = {
            # RO
            'id': { 'read_only': True, 'required': False },
            # WO
			'created': { 'write_only': True, 'read_only': False, 'required': False },
			'modified': { 'write_only': True, 'read_only': False, 'required': False },
            'created_by': { 'write_only': True, 'required': False },
            'updated_by': { 'write_only': True, 'required': False },
        }

    # GET
    def to_representation(self, instance):
        data = super(TagSerializer, self).to_representation(instance)
        return data

    def resolve_options(self):
        return list(self.Meta.model.get_brand_assoc_queryset(self._get_brand(), 'all').values('name', 'pk', 'tag_type'))

    # POST / PUTx
    def create(self, validated_data):
        user = self._get_user()
        validated_data.update({
            'created_by': user,
            'updated_by': user,
        })
        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        instance = self._update(instance, validated_data)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.updated_by = self._get_user()
        instance.save()
        return instance

    # Instance & Field validation
    def validate(self, data):
        current_brand = self._get_brand()
        instance = getattr(self, 'instance') if hasattr(self, 'instance') else None

        data_brand = data.get('collection_brand')
        tag_type = data.get('tag_type')
        display = data.get('display')

        if current_brand is not None:
            if isinstance(data_brand, Brand) and data_brand.id != current_brand.id:
                raise serializers.ValidationError("Invalid Brand")
            elif isinstance(data_brand, int) and data_brand != current_brand.id:
                raise serializers.ValidationError("Invalid Brand")
            elif instance is not None:
                data_brand = instance.brand if instance.brand is not None else current_brand.id
            else:
                data_brand = current_brand.id
        elif not isinstance(data_brand, (Brand, int)):
            data_brand = instance.brand if instance.brand is not None else None

        data.update(collection_brand=data_brand)

        if display is not None and display not in dict(self.model.DISPLAY_CHOICES).keys():
            raise serializers.ValidationError("Invalid display choice.")
        if tag_type not in dict(self.model.TAG_TYPES).keys():
            raise serializers.ValidationError("Invalid Tag Type")
        return data


class TagEndpoint(BaseEndpoint):
    """Responsible for API views relating to `Template` model accessed via Brand dashboard"""

    # QuerySet kwargs
    filter = { 'all_tags': True }

    # Metadata
    model = Tag
    fields = []
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    # View behaviour
    reverse_name_default = 'brand_tag_target'
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
        return self.update(request, partial=True, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
