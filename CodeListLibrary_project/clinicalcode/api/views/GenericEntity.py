from rest_framework import status
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q

from ...models import *
from ...entity_utils import permission_utils
from ...entity_utils import search_utils
from ...entity_utils import api_utils

#TODO: FIX AUTHENTICATION FUNCTION
#TODO: REMOVE ENTITY_PREFIX AND ENTITY_ID

''' Create/Update GenericEntity '''

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
def create_generic_entity(request):
    '''
    
    '''
    #TODO
    return Response(data=data,
        content_type="text/json-comment-filtered",
        status=status.HTTP_201_CREATED)

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
def update_generic_entity(request):
    '''
    
    '''
    #TODO
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

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(primary_key)
    if isinstance(entity_response, Response):
        return entity_response
    
    return Response(
        api_utils.get_entity_version_history(request, primary_key), 
        status=status.HTTP_200_OK
    )

''' Get GenericEntities '''

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_generic_entities(request):
    '''
    
    '''
    if request.user:
        user_authed = True

    # Build query from searchable metadata fields
    metadata_query = api_utils.build_query_from_template(request, user_authed)
    if metadata_query:
        entities = GenericEntity.objects.filter(Q(**metadata_query))

        # Exit early if metadata queries do not match
        if not entities:
            return Response([], status=status.HTTP_200_OK)
    else:
        entities = GenericEntity.objects.all()

    # Build query from searchable GenericEntity template fields
    templates = Template.objects.all()
    for template in templates:
        template_query = api_utils.build_query_from_template(
            request, user_authed, template=template.definition['fields']
        )

        if template_query:
            entities = entities.filter(Q(**template_query))

    # Search terms
    search = request.query_params.get('search', None)
    if search:
        entities = search_utils.search_entities(
            entities, search, fuzzy=False, order_by_relevance=False
        )

    #TODO: This should really be paginated or limited if no search/filters used...
    
    # Only display GenericEntities that are accessible to the user
    result = []
    for entity in entities:
        historical_entity_response = api_utils.exists_historical_entity(
            entity.id, user_authed, historical_id=None
        )
        if isinstance(historical_entity_response, Response):
            return historical_entity_response
        historical_entity = historical_entity_response

        user_can_access = permission_utils.has_entity_view_permissions(
            request, historical_entity
        )
        if user_can_access:
            result.append({
                'id': historical_entity.id,
                'version_id': historical_entity.history_id,
                'name': historical_entity.name
            })

    return Response(
        data=result,
        content_type='json',
        status=status.HTTP_200_OK
    )

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

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(primary_key)
    if isinstance(entity_response, Response):
        return entity_response
    
    # Find latest historical id if not provided, and get first matching historical entity
    historical_entity_response = api_utils.exists_historical_entity(
        primary_key, user_authed, historical_id=historical_id
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
