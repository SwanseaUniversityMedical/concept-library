"""Brand Dashboard: API endpoints relating to Template model"""
import datetime
import json

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNDataCategory import HDRNDataCategory
from .BaseTarget import BaseSerializer, BaseEndpoint


class HDRNCategorySerializer(BaseSerializer):

    class Meta:
        model = HDRNDataCategory
        fields =  ['id', 'title', 'description', 'metadata']

    def to_representation(self, instance):
        data = super(HDRNCategorySerializer, self).to_representation(instance)
        return data

    def create(self, validated_data):
        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        instance = self._update(instance, validated_data)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.save()
        return instance

    @staticmethod
    def validate(data):
        definition = data.get('definition')
        if not isinstance(definition, dict):
            raise serializers.ValidationError('Required JSONField `definition` is missing')

        try:
            json.dumps(definition)
        except:
            raise serializers.ValidationError('Template definition is not valid JSON')
        return data



class HDRNCategoryEndpoint(BaseEndpoint):
    """API views for the `HDRNSite` model"""
    model = HDRNDataCategory
    fields = []
    queryset = HDRNDataCategory.objects.all()
    serializer_class = HDRNCategorySerializer

    reverse_name_default = 'hdrn_category_target'
    reverse_name_retrieve = 'hdrn_category_target_with_id'

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




