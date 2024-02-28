from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F

from ...entity_utils import ontology_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontologies(request):
    """
        Get all ontology categories and their root nodes, incl. associated data
    """
    result = ontology_utils.try_get_ontology_model_data([x.value for x in constants.ONTOLOGY_TYPES], default=[])
    return Response(
        data=list(result),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_detail(request, ontology_id):
    """
        Get detail of specified ontology by ontology_id, including associated
        data e.g. root nodes, children etc
    """
    ontology_id = gen_utils.parse_int(ontology_id, default=None)
    if not isinstance(ontology_id, int):
        return Response(
            data={
                'message': 'Invalid ontology id, expected valid integer'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    result = ontology_utils.try_get_ontology_data(ontology_id, default=None)

    if not isinstance(result, dict):
        return Response(
            data={
                'message': f'Ontology of id {ontology_id} does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_node(request, ontology_id, node_id):
    """
        Get the element details of the specified ontology element by its
        ontology_id and its source ontology_name, including associated data
        e.g. tree-related information
    """
    ontology_id = gen_utils.parse_int(ontology_id, default=None)
    if not isinstance(ontology_id, int):
        return Response(
            data={
                'message': 'Invalid ontology id, expected valid integer'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    node_id = gen_utils.parse_int(node_id, default=None)
    if not isinstance(node_id, int):
        return Response(
            data={
                'message': 'Invalid node id, expected valid integer'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    result = ontology_utils.try_get_ontology_node_data(ontology_id, node_id, default=None)
    return Response(
        data=result,
        status=status.HTTP_200_OK
    )
