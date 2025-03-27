"""Brand Dashboard: API endpoints relating to Template model"""
import datetime
import json

from django.utils.timezone import make_aware
from rest_framework import status, serializers
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNSite import HDRNSite
from .BaseTarget import BaseSerializer, BaseEndpoint


class HDRNSiteSerializer(BaseSerializer):
    model = HDRNSite

    id = serializers.IntegerField(label='Id', read_only=True)
    name = serializers.CharField(label='Name', required=True, max_length=512)
    description = serializers.CharField(label='Description', required=False, allow_blank=True)
    metadata = serializers.JSONField(label='Metadata', required=False, allow_null=True)

    def to_representation(self, instance):
        data = super(HDRNSiteSerializer, self).to_representation(instance)
        return data

    def create(self, validated_data):
        return self.model.objects.create(**validated_data)

    @staticmethod
    def update(instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.modified = make_aware(datetime.datetime.now())
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



class HDRNSiteEndpoint(BaseEndpoint):
    """API views for the `HDRNSite` model"""
    model = HDRNSite
    fields = []
    queryset = HDRNSite.objects.all()
    serializer_class = HDRNSiteSerializer

    reverse_name_default = 'hdrn_site'
    reverse_name_retrieve = 'hdrn_site_with_id'

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




