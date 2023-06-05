from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.conf import settings

from ...models import *
from ...entity_utils import permission_utils
from ...entity_utils import template_utils
from ...entity_utils import search_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

''' Create/Update GenericEntity '''

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_generic_entity(request):
    '''
    
    '''
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.CREATE.value
    )
    if isinstance(form, Response):
        return form
        
    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully created entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_generic_entity(request):
    '''
    
    '''
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.UPDATE.value
    )
    if isinstance(form, Response):
        return form

    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully updated entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

''' Get GenericEntity version history '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entity_version_history(request, phenotype_id=None):
    '''
    
    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True
    
    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(phenotype_id)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(phenotype_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    return Response(
        data=api_utils.get_entity_version_history(request, phenotype_id), 
        status=status.HTTP_200_OK
    )

''' Get GenericEntities '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entities(request, should_paginate=False):
    '''
    
    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True

    # Get all accessible entities for this user
    entities = permission_utils.get_accessible_entities(
        request, 
        consider_user_perms=False, 
        status=[constants.APPROVAL_STATUS.ANY]
    )
    if not entities.exists():
        return Response([], status=status.HTTP_200_OK)
    
    # Filter by template id and version
    template_id = request.query_params.get('template_id', None)
    template_version_id = request.query_params.get('template_version_id', None)
    if template_id:
        template = Template.objects.filter(id=template_id)
        if not template.exists():
            return Response(
                data={
                    'message': 'Template with specified id does not exist'
                },
                content_type='json',
                status=status.HTTP_404_NOT_FOUND
            )
        
        template = template.first()
        if template_version_id:
            template = template.history.filter(template_version=template_version_id)
            if not template.exists():
                return Response(
                    data={
                        'message': 'Template with specified version id does not exist'
                    },
                    content_type='json',
                    status=status.HTTP_404_NOT_FOUND
                )
            
            template = template.latest()
            entities = entities.filter(
                template__id=template.id, template_version=template.template_version
            )
        else:
            entities = entities.filter(
                template__id=template.id
            )

    # Build query from searchable GenericEntity template fields
    templates = Template.objects.all()
    for template in templates:
        template_query, where_clause = api_utils.build_query_from_template(
            request, user_authed, template=template.definition['fields']
        )

        entities = entities.filter(Q(**template_query))
        entities = entities.extra(where=where_clause)

    # Search terms
    search = request.query_params.get('search', None)
    if search:
        entities = search_utils.search_entities(
            entities, search, fuzzy=False, order_by_relevance=False
        )

    # Exit early if queries do not match
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
    if should_paginate:
        page = gen_utils.parse_int(request.query_params.get('page', 1), default=1)
        entities = search_utils.try_get_paginated_results(
            request, entities, page, page_size=50
        )
    
    # Get details of each entity
    formatted_entities = []
    for entity in entities:
        entity_detail = api_utils.get_entity_detail(
            request, 
            entity.id, 
            entity, 
            user_authed, 
            fields_to_ignore=constants.ENTITY_LIST_API_HIDDEN_FIELDS, 
            return_data=True
        )

        if not isinstance(entity_detail, Response):
            formatted_entities.append(entity_detail)

    if should_paginate:
        result = {
            'page': page,
            'num_pages': entities.paginator.num_pages,
            'data': formatted_entities
        }
    else:
        result = formatted_entities

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

''' Get GenericEntity detail '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_entity_detail(request, phenotype_id, version_id=None, field=None):
    '''

    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True

    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(phenotype_id)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(phenotype_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    # Find latest historical id if not provided, and get first matching historical entity
    historical_entity_response = api_utils.exists_historical_entity(
        phenotype_id, request.user, historical_id=version_id
    )
    if isinstance(historical_entity_response, Response):
        return historical_entity_response
    historical_entity = historical_entity_response

    # Check if the user has the permissions to view this entity version
    user_can_access = permission_utils.can_user_view_entity(
        request, historical_entity.id, historical_entity.history_id
    )
    if not user_can_access:
        return Response(
            data={
                'message': 'Entity version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if field is not None:
        if template_utils.is_valid_field(historical_entity, field):
            return api_utils.get_entity_detail(
                request, 
                phenotype_id, 
                historical_entity, 
                user_authed, 
                target_field=field, 
                return_data=True
            )
        
        if field == 'codes':
            return api_utils.get_codelist_from_entity(historical_entity)
        
        return Response(
            data={
                'message': 'Field does not exist'
            }, 
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return api_utils.get_entity_detail(
        request, phenotype_id, historical_entity, user_authed
    )
