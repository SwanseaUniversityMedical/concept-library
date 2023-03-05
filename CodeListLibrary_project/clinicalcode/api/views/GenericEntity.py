from rest_framework import status
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from .View import robots, robots2
from ...models import *
from ...entity_utils import permission_utils
from ...entity_utils import api_utils

''' Create/Update GenericEntity '''

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
def create_generic_entity(request):
    '''
    
    '''


    return Response(data=data,
        content_type="text/json-comment-filtered",
        status=status.HTTP_201_CREATED)

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
def update_generic_entity(request):
    '''
    
    '''

    return Response(
        data=data,
        content_type="text/json-comment-filtered",
        status=status.HTTP_201_CREATED
    )

''' Get GenericEntity version history '''

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_generic_entity_version_history(request, primary_key=None):
    '''
    
    '''
    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(primary_key)
    if isinstance(entity_id_response, Response):
        return entity_id_response
    entity_prefix, entity_id = entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(entity_prefix, entity_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    return Response(
        api_utils.get_entity_version_history(request, entity_prefix, entity_id), 
        status=status.HTTP_200_OK
    )

''' Get GenericEntities '''

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_generic_entities(request, primary_key=None, user_authed=False):
    '''
    
    '''


    return Response([], status=status.HTTP_200_OK)


''' Get GenericEntity detail '''

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_entity_detail(request, primary_key, historical_id=None, field=None):
    '''

    '''
    if request.user:
        user_authed = True

    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(primary_key)
    if isinstance(entity_id_response, Response):
        return entity_id_response
    entity_prefix, entity_id = entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(entity_prefix, entity_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    # Find latest historical id if not provided, and get first matching historical entity
    historical_entity_response = api_utils.exists_historical_entity(
        entity_prefix, entity_id, user_authed, historical_id=historical_id
    )
    if isinstance(historical_entity_response, Response):
        return historical_entity_response
    historical_entity = historical_entity_response

    # Check if the user has the permissions to view this entity version
    user_can_access = permission_utils.has_entity_view_permissions(
        request, historical_entity
    )
    if not user_can_access:
        return Response(
            data={
                'message': 'Entity version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )

    if field:
        return api_utils.export_field(historical_entity, field, user_authed)

    return api_utils.get_entity_json_detail(
        request, primary_key, historical_entity, user_authed
    )
