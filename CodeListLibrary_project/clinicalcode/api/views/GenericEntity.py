from rest_framework import status
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q

from ...models import *
from ...entity_utils import permission_utils
from ...entity_utils import search_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils

''' Create/Update GenericEntity '''

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
def create_generic_entity(request):
    '''
    
    '''
    #TODO
    return Response(
        data=[],
        content_type='json',
        status=status.HTTP_201_CREATED
    )

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
def update_generic_entity(request):
    '''
    
    '''
    #TODO
    return Response(
        data=[],
        content_type='json',
        status=status.HTTP_200_OK
    )

''' Get GenericEntity version history '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
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
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entities(request, verbose=True):
    '''
    
    '''
    if request.user:
        user_authed = True

    # Get all accessible entities for this user
    entities = permission_utils.get_accessible_entities(request)
    if not entities.exists():
        return Response([], status=status.HTTP_200_OK)

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

    # Exit early if metadata queries do not match
    if not entities.exists():
        return Response([], status=status.HTTP_200_OK)
    
    ''' Please note, this looks redundant but is *required* due to varchar entity ID '''
    entities = GenericEntity.history.filter(
        id__in=entities.values_list('id', flat=True),
        history_id__in=entities.values_list('history_id', flat=True)
    )
    entities = entities.extra(
        select={'true_id': """CAST(REGEXP_REPLACE(id, '[a-zA-Z]+', '') AS INTEGER)"""}
    ).order_by('true_id', 'id')

    # Paginate results
    page = gen_utils.parse_int(request.query_params.get('page', 1), default=1)
    entities = search_utils.try_get_paginated_results(
        request, entities, page, page_size=50
    )
    
    # Only display GenericEntities that are accessible to the user
    result = {
        'page': page,
        'num_pages': entities.paginator.num_pages,
        'data': []
    }
    for entity in entities:
        if not verbose: 
            result['data'].append({
                'id': entity.id,
                'version_id': entity.history_id,
                'name': entity.name
            })
        else:
            entity_detail = api_utils.get_entity_json_detail(
                request, entity.id, entity, user_authed, return_data=True
            )

            if not isinstance(entity_detail, Response):
                result['data'].append(entity_detail)

    return Response(
        data=result,
        content_type='json',
        status=status.HTTP_200_OK
    )

''' Get GenericEntity detail '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
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
        primary_key, request.user, historical_id=historical_id
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
