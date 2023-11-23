from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models.expressions import RawSQL
from django.db.models import Q

from ...models import *
from ...entity_utils import api_utils
from ...entity_utils import permission_utils
from ...entity_utils import concept_utils
from ...entity_utils import gen_utils
from ...entity_utils.constants import CLINICAL_RULE_TYPE

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concepts(request):
    """
        Get all concepts accessible to the user, optionally, provide parameters to filter by
    """
    # Get all concepts accesible to the user
    concepts = permission_utils.get_accessible_concepts(
        request
    )
    if not concepts.exists():
        return Response([], status=status.HTTP_200_OK)
    
    # Handle valid query parameters
    tags = request.query_params.get('tags')
    if tags is not None:
        tags = gen_utils.parse_as_int_list(tags)
        concepts = concepts.filter(Q(tags__overlap=tags))

    collections = request.query_params.get('collections')
    if collections is not None:
        collections = gen_utils.parse_as_int_list(collections)
        concepts = concepts.filter(Q(collections__overlap=collections))

    coding_system = request.query_params.get('coding_system')
    if coding_system is not None:
        coding_system = gen_utils.parse_as_int_list(coding_system)
        concepts = concepts.filter(Q(coding_system__id__in=coding_system))

    owner = request.query_params.get('owner')
    if owner is not None:
        concepts = concepts.filter(Q(owner__username=owner))

    phenotype_id = request.query_params.get('phenotype_id')
    if phenotype_id is not None:
        phenotype_id = phenotype_id.split(',')
        concepts = concepts.filter(Q(phenotype_owner__id__in=phenotype_id))
    
    # Handle searching
    search = request.query_params.get('search')
    if search is not None:
        concepts = concepts.filter(
            id__in=RawSQL(
                """
                select id
                from clinicalcode_historicalconcept
                where id = ANY(%s)
                  and history_id = ANY(%s)
                  and (
                    setweight(to_tsvector('pg_catalog.english', coalesce(friendly_id,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(name,'')), 'A') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(author,'')), 'B') ||
                    setweight(to_tsvector('pg_catalog.english', coalesce(description,'')), 'B')
                  ) @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', %s)::text || ':*', '<->', '|'))
                """,
                [
                    list(concepts.values_list('id', flat=True)), 
                    list(concepts.values_list('history_id', flat=True)), 
                    search
                ]
            )
        )

    # Exit early if queries do not match
    if not concepts.exists():
        return Response([], status=status.HTTP_200_OK)
    
    # Format concepts
    result = []
    for concept in concepts:
        concept_data = concept_utils.get_minimal_concept_data(concept)

        # Append concept version information
        concept_data['version_history'] = api_utils.get_concept_version_history(
            request, concept.id
        )

        result.append(concept_data)
    
    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concept_detail(request, concept_id, version_id=None, export_codes=False):
    """
        Get the detail of specified concept by concept_id, optionally target a specific
            version using version_id and/or export the concept codelist
    """
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    # Get historical concept
    historical_concept_response = api_utils.exists_historical_concept(
        request, concept_id, historical_id=version_id
    )
    if isinstance(historical_concept_response, Response):
        return historical_concept_response
    historical_concept = historical_concept_response

    # Check if the user has the permissions to view this concept version
    user_can_access = permission_utils.can_user_view_concept(request, historical_concept)
    if not user_can_access:
        return Response(
            data={
                'message': 'Concept version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )

    if export_codes:
        # Build only the codelist
        concept_codes = concept_utils.get_concept_codelist(
            historical_concept.id,
            historical_concept.history_id,
            incl_attributes=True
        )
        for code in concept_codes:
            attributes = code.get('attributes')
            headers = historical_concept.code_attribute_header
            if attributes is not None and headers is not None:
                code['attributes'] = dict(zip(
                    headers, attributes
                ))
        
        return Response(
            data=concept_codes,
            status=status.HTTP_200_OK
        )
    
    # Build the whole concept detail
    concept_data = concept_utils.get_clinical_concept_data(
        historical_concept.id,
        historical_concept.history_id,
        include_attributes=True,
        format_for_api=True
    )

    # Append concept version information
    concept_data['version_history'] = api_utils.get_concept_version_history(
        request, concept_id
    )

    return Response(
        data=concept_data,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concept_version_history(request, concept_id):
    """
        Get version history of a specific concept, using concept_id
    """
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    return Response(
        data=api_utils.get_concept_version_history(request, concept_id), 
        status=status.HTTP_200_OK
    )
