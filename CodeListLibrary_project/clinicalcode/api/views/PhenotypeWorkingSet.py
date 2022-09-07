import json
from collections import OrderedDict
from collections import OrderedDict as ordr
from datetime import datetime

from clinicalcode.context_processors import clinicalcode
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.core.validators import URLValidator
from django.db.models import Q
from django.db.models.aggregates import Max
from django.http.response import Http404
from numpy.distutils.fcompiler import none
from rest_framework import status, viewsets
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from django.db.models.functions import Lower

from ...db_utils import *
from ...models import *
from ...permissions import *
from ...utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ..serializers import *
from .View import *

from drf_yasg.utils import swagger_auto_schema


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
@robots()
def export_published_phenotypeworkingset_codes(request, pk, workingset_history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        working set (pk),
        for a specific historical working set version (workingset_history_id).
    '''

    if not PhenotypeWorkingset.objects.filter(id=pk).exists():
        raise PermissionDenied
    
    if workingset_history_id is None:
        # get the latest published version
        latest_published_version = PublishedWorkingset.objects.filter(workingset_id=pk, approval_status=2).order_by('-workingset_history_id').first()
        if latest_published_version:
            workingset_history_id = latest_published_version.workingset_history_id

    if not PhenotypeWorkingset.history.filter(id=pk, history_id=workingset_history_id).exists():
        raise PermissionDenied

    is_published = checkIfPublished(PhenotypeWorkingset, pk, workingset_history_id)

    # check if the working set version is published
    if not is_published:
        raise PermissionDenied

    #----------------------------------------------------------------------
    if request.method == 'GET':
        rows_to_return = get_working_set_codes_by_version(request, pk, workingset_history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)


#--------------------------------------------------------------------------
@api_view(['GET'])
def export_phenotypeworkingset_codes_byVersionID(request, pk, workingset_history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        working set  (pk),
        for a specific historical working set  version (workingset_history_id).
    '''
        
    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = PhenotypeWorkingset.objects.get(pk=pk).history.latest().history_id
        
    # Require that the user has access to the base working set.
    # validate access for login site
    validate_access_to_view(request,
                            PhenotypeWorkingset,
                            pk,
                            set_history_id=workingset_history_id)

    #----------------------------------------------------------------------

    current_phenotypeworkingset = PhenotypeWorkingset.objects.get(pk=pk)

    user_can_export = (allowed_to_view_children(request, PhenotypeWorkingset, pk, set_history_id=workingset_history_id)
                       and chk_deleted_children(request, PhenotypeWorkingset, pk, returnErrors=False, set_history_id=workingset_history_id)
                       and not current_phenotypeworkingset.is_deleted
                       )

    if not user_can_export:
        raise PermissionDenied
    #----------------------------------------------------------------------

    if request.method == 'GET':
        rows_to_return = get_working_set_codes_by_version(request, pk, workingset_history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)
    
    
def get_working_set_codes_by_version(request, pk, workingset_history_id):
    '''
        Return the codes for a working set for a specific historical version.
    '''
    # here, check live version is not deleted
    if PhenotypeWorkingset.objects.get(pk=pk).is_deleted == True:
        raise PermissionDenied
    #--------------------------------------------------
    
    current_ws_version = PhenotypeWorkingset.history.get(id=pk, history_id=workingset_history_id)

    phenotypes_concepts_data = current_ws_version.phenotypes_concepts_data
    
    attributes_titles = []
    if phenotypes_concepts_data:
        attr_sample = phenotypes_concepts_data[0]["Attributes"]
        attributes_titles = [x["name"] for x in attr_sample]

    titles = ( ['code', 'description', 'coding_system']
             + ['concept_id', 'concept_version_id' , 'concept_name']
             + ['phenotype_id', 'phenotype_version_id', 'phenotype_name']
             + ['workingset_id', 'workingset_version_id', 'workingset_name']
             + attributes_titles
            )

    codes = []
    for concept in phenotypes_concepts_data:
        concept_id = int(concept["concept_id"].replace("C", ""))
        concept_version_id = concept["concept_version_id"]
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name
        concept_name = Concept.history.get(id=concept_id, history_id=concept_version_id).name
              
        phenotype_id = int(concept["phenotype_id"].replace("PH", ""))
        phenotype_version_id = concept["phenotype_version_id"]
        phenotype_name = Phenotype.history.get(id=phenotype_id, history_id=phenotype_version_id).name
                        
        attributes_values = []
        if attributes_titles:
            attributes_values = [x["value"] for x in concept["Attributes"]]
            
               
        rows_no = 0
        concept_codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        for cc in concept_codes:
            rows_no += 1
            codes.append(
                    ordr(
                        list(
                            zip(titles, [ cc['code']
                                        , cc['description'].encode('ascii', 'ignore').decode('ascii')
                                        , concept_coding_system
                                        , 'C' + str(concept_id)
                                        , concept_version_id
                                        , concept_name
                                        , 'PH' + str(phenotype_id)
                                        , phenotype_version_id
                                        , phenotype_name                
                                        , current_ws_version.id
                                        , current_ws_version.history_id
                                        , current_ws_version.name
                                        ]
                                        + attributes_values
                                        )
                            )
                        )
                    )

                  

        if rows_no == 0:
            codes.append(
                    ordr(
                        list(
                            zip(titles, [ '' 
                                        , '' 
                                        , concept_coding_system 
                                        , 'C' + str(concept_id)
                                        , concept_version_id
                                        , concept_name
                                        , 'PH' + str(phenotype_id)
                                        , phenotype_version_id
                                        , phenotype_name                
                                        , current_ws_version.id
                                        , current_ws_version.history_id
                                        , current_ws_version.name
                                        ]
                                        + attributes_values 
                                        )
                            )
                        )
                    )

    return codes




