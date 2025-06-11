"""Brand Dashboard: API endpoints relating to Template model"""
import datetime

from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.HDRNSite import HDRNSite
from .BaseTarget import BaseSerializer, BaseEndpoint


class HDRNSiteSerializer(BaseSerializer):
    """"""

    # Appearance
    _str_display = 'name'
    _list_fields = ['id', 'name', 'abbreviation']
    _item_fields = ['id', 'name', 'abbreviation', 'description']

	# Metadata
    class Meta:
        model = HDRNSite
        exclude = ['created', 'modified']
        extra_kwargs = {
            # RO
            'id': { 'read_only': True, 'required': False },
            # WO
			'created': { 'write_only': True, 'read_only': False, 'required': False },
			'modified': { 'write_only': True, 'read_only': False, 'required': False },
            # WO | RO
            'description': { 'style': { 'as_type': 'TextField' } },
            'metadata': { 'help_text': 'Optionally specify a JSON object describing metadata related to this entity.' },
        }

	# GET
    def resolve_format(self):
        return { 'type': 'ForeignKey' }

    def resolve_options(self):
        return list(self.Meta.model.objects.all().values('name', 'pk'))

	# POST / PUT
    def create(self, validated_data):
        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        instance = self._update(instance, validated_data)
        instance.modified = make_aware(datetime.datetime.now())  # Set `modified` timestamp
        instance.save()
        return instance


class HDRNSiteEndpoint(BaseEndpoint):
    """API views for the `HDRNSite` model"""
    model = HDRNSite
    fields = []
    queryset = HDRNSite.objects.all()
    serializer_class = HDRNSiteSerializer

    reverse_name_default = 'hdrn_site_target'
    reverse_name_retrieve = 'hdrn_site_target_with_id'

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
