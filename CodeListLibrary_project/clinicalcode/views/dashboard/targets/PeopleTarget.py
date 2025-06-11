from functools import partial

from rest_framework import status, serializers
from rest_framework.response import Response

from clinicalcode.entity_utils import gen_utils, constants
from clinicalcode.models.Organisation import OrganisationMembership
from .BaseTarget import BaseSerializer, BaseEndpoint


class OrganisationMembershipSerializer(BaseSerializer):

    class Meta:
        model = OrganisationMembership
        fields = ['id', 'user', 'organisation', 'role', 'joined']

    def to_representation(self, instance):
        data = super(OrganisationMembershipSerializer, self).to_representation(instance)
        return data

    def create(self, validated_data):

        return self._create(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        instance = self._update(instance, validated_data)
        instance.save()
        return instance


    def validate(self, data):
        role = data.get('role')
        if role not in [e.value for e in constants.ORGANISATION_ROLES]:
            raise serializers.ValidationError(f"Invalid role.")

        return data

class PeopleEndpoint(BaseEndpoint):
    """Responsible for API views relating to `Template` model accessed via Brand dashboard"""

    model = OrganisationMembership
    fields = []
    queryset = OrganisationMembership.objects.all()
    serializer_class = OrganisationMembershipSerializer

    # View behaviour
    reverse_name_default = 'brand_people_target'
    # View behaviour
    reverse_name_retrieve = 'brand_people_target_with_id'

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