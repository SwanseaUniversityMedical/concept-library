'''
    ---------------------------------------------------------------------------
    API VIEW
    API access to the data to list the various data types (if access is
    permitted) and to access the data structure and components of groups of
    data types.
    ---------------------------------------------------------------------------
'''
import json
#from ...permissions import Permissions
import re
from collections import OrderedDict
from collections import OrderedDict as ordr
from datetime import datetime

from clinicalcode.context_processors import clinicalcode
from clinicalcode.permissions import get_visible_concepts_live
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import PermissionDenied
# from snippets.models import Snippet
# from snippets.serializers import SnippetSerializer
from django.core.validators import URLValidator
from django.db.models import Q
from django.db.models.aggregates import Max
from django.http.response import Http404
from django.views.defaults import permission_denied
from numpy.distutils.fcompiler import none
from rest_framework import status, viewsets
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.utils.timezone import make_aware

from ...db_utils import *
from ...models import *

#from django.forms.models import model_to_dict
from ...permissions import *
from ...utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ..serializers import *
from .View import *

from drf_yasg.utils import swagger_auto_schema
# from rest_framework.parsers import MultiPartParser#, FormParser
# from rest_framework.decorators import parser_classes


#--------------------------------------------------------------------------
'''
    ---------------------------------------------------------------------------
    View sets (see http://www.django-rest-framework.org/api-guide/viewsets).
    ---------------------------------------------------------------------------
'''

# /api/v1/concepts-live
class ConceptViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of concepts.
    '''
    # Don't show in Swagger
    swagger_schema = None
    
    queryset = Concept.objects.none()
    serializer_class = ConceptSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Restrict this to just those concepts that are visible to the user.
        '''
        queryset = get_visible_concepts_live(self.request.user)
        search = self.request.query_params.get('search', None)
        concept_id_to_exclude = self.request.query_params.get('concept_id_to_exclude')
        if search is not None:
            queryset = queryset.filter(name__icontains=search).exclude(id=concept_id_to_exclude).exclude(is_deleted=True)
        return queryset

    def filter_queryset(self, queryset):
        '''
            Override the default filtering.
            By default we get concepts ordered by creation date even if
            we provide sorted data from get_queryset(). We have to sort the
            data here.
        '''
        queryset = super(ConceptViewSet, self).filter_queryset(queryset)
        return queryset.order_by('id')


#--------------------------------------------------------------------------
# /api/v1/concepts_live_and_published
# Don't show in Swagger
@swagger_auto_schema(method='get', auto_schema=None)
@api_view(['GET'])
def concepts_live_and_published(request):

    search = request.query_params.get('search', "")
    concept_id_to_exclude = utils.get_int_value(request.query_params.get('concept_id_to_exclude', 0), 0)

    rows_to_return = get_visible_live_or_published_concept_versions(
                                                                    request,
                                                                    search=search,
                                                                    concept_id_to_exclude=concept_id_to_exclude,
                                                                    exclude_deleted=True,
                                                                    do_not_use_FTS = True)

    return Response(rows_to_return, status=status.HTTP_200_OK)


#--------------------------------------------------------------------------
# /api/v1/codes/?code_list_id=123
class CodeViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of codes.
        For the specified code_list_id.
        (work only on live version since it is used in edit form)
    '''
    # Don't show in Swagger
    swagger_schema = None
    
    queryset = Code.objects.none()
    serializer_class = CodeSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Restrict this to just those codes that are visible to the user.
        '''
        # must have querystring of code_list_id
        code_list_id = self.request.query_params.get('code_list_id', None)
        if code_list_id is None:
            raise Http404

        queryset = get_visible_codes(self.request.user, code_list_id)
        return queryset

    def filter_queryset(self, queryset):
        '''
            Override the default filtering.
            By default we get codes ordered by creation date even if
            we provide sorted data from get_queryset(). We have to sort the
            data here.
        '''
        queryset = super(CodeViewSet, self).filter_queryset(queryset)
        return queryset.order_by('code')

''' Updated API '''

from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models.expressions import RawSQL
from django.db.models import Q

from ...models import *
from ...entity_utils import api_utils
from ...entity_utils import permission_utils
from ...entity_utils import concept_utils
from ...entity_utils import gen_utils

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_concepts(request):
    '''
    
    '''
    # Get all concepts accesible to the user
    concepts = permission_utils.get_accessible_concepts(
        request, 
        consider_user_perms=False
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

        result.append(
            concept_data
        )
    
    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concept_detail(request, concept_id, version_id=None, export_codes=False):
    '''
    
    '''
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    # Get historical concept
    historical_concept_response = api_utils.exists_historical_concept(
        concept_id, request.user, historical_id=version_id
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
        concept_data = concept_utils.get_clinical_concept_data(
            historical_concept.id,
            historical_concept.history_id,
            aggregate_component_codes=True,
            include_component_codes=False,
            include_attributes=True,
            format_for_api=True
        )
        concept_codes = concept_data.get('aggregated_component_codes')
        attribute_headers = concept_data.get('code_attribute_headers')

        # Format the codelist for legacy API
        concept_codes = api_utils.get_formatted_concept_codes(
            historical_concept, concept_codes, headers=attribute_headers
        )
        
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
    '''
    
    '''
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    return Response(
        data=api_utils.get_concept_version_history(request, concept_id), 
        status=status.HTTP_200_OK
    )
