from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F

from ...entity_utils import tree_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontologies(request):
    """
        Get all ontology categories and their root nodes, incl. associated data
    """
    result = tree_utils.try_get_tree_models_data(constants.KNOWN_ONTOLOGY_SOURCES, default=[])
    return Response(
        data=list(result),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_detail(request, ontology_name):
    """
        Get detail of specified ontology by ontology_name, including associated
        data e.g. root nodes, children etc
    """
    if not isinstance(ontology_name, str) or gen_utils.is_empty_string(ontology_name):
        return Response(
            data={
                'message': 'Invalid name, expected non-empty string'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    ontology_label = next((x.get('label') for x in constants.KNOWN_ONTOLOGY_SOURCES if x.get('source') == ontology_name), None)
    result = tree_utils.try_get_tree_data(ontology_name, ontology_label, default=None)

    if not isinstance(result, dict):
        ontology_name = ontology_name if isinstance(ontology_name, str) else 'NULL'
        return Response(
            data={
                'message': f'Ontology of name {ontology_name} does not exist'
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
def get_ontology_node(request, ontology_name, ontology_id):
    """
        Get the element details of the specified ontology element by its
        ontology_id and its source ontology_name, including associated data
        e.g. tree-related information
    """
    if not isinstance(ontology_name, str) or gen_utils.is_empty_string(ontology_name):
        return Response(
            data={
                'message': 'Invalid name, expected non-empty string'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    ontology_id = gen_utils.parse_int(ontology_id, default=None)
    if ontology_id is None:
        return Response(
            data={
                'message': 'Invalid id, expected parseable integer'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    ontology_label = next((x.get('label') for x in constants.KNOWN_ONTOLOGY_SOURCES if x.get('source') == ontology_name), None)
    result = tree_utils.try_get_tree_node_data(ontology_name, ontology_id, model_label=ontology_label, default=None)

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )
