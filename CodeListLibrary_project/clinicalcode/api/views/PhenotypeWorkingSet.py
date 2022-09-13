import json
import string
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
from django.utils.timezone import make_aware

from ...db_utils import *
from ...models import *
from ...permissions import *
from ...utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ..serializers import *
from .View import *

from drf_yasg.utils import swagger_auto_schema

#------------------ phenotype working sets --------------------------------
@swagger_auto_schema(method='get', auto_schema=None)
@api_view(['GET'])
def phenotypeworkingsets(request, pk=None):
    '''
        Get the API output for the list of my Phenotype Working Sets.
    '''
    search = request.query_params.get('search', None)

    if pk is not None:
        workingset_id = pk
    else:
        workingset_id = request.query_params.get('id', None)

    tag_ids = request.query_params.get('tag_ids', '')
    collection_ids = request.query_params.get('collection_ids', '')
    owner = request.query_params.get('owner_username', '')
    author = request.query_params.get('author', '')
    show_only_my_workingsets = request.query_params.get('show_my_ph_workingsets', "0")
    show_deleted_workingsets = request.query_params.get('show_deleted_ph_workingsets', "0")
    ws_brand = request.query_params.get('brand', "")
    do_not_show_versions = request.query_params.get('do_not_show_versions', "0")

    data_sources = request.query_params.get('data_source_ids', '')
    start_date_range = request.query_params.get('start_date', '')
    end_date_range = request.query_params.get('end_date', '')
    
    start_date_query, end_date_query = False, False
    try:
        start_date_query = make_aware(datetime.datetime.strptime(start_date_range, '%Y-%m-%d'))
        end_date_query = make_aware(datetime.datetime.strptime(end_date_range, '%Y-%m-%d'))
    except ValueError:
        start_date_query = False
        end_date_query = False
    
    # ensure that user is only allowed to view/edit the relevant workingsets
    workingsets = get_visible_phenotypeworkingsets(request.user)

    if workingset_id is not None:
        if workingset_id != '':
            workingsets = workingsets.filter(pk=workingset_id)

    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            workingsets = workingsets.filter(name__icontains=search.strip())

    if author is not None:
        if author != '':
            workingsets = workingsets.filter(author__icontains=author.strip())

    if tag_ids.strip() != '':
        # split tag ids into list
        new_tag_list = [int(i) for i in tag_ids.split(",")]
        workingsets = workingsets.filter(tags__overlap=new_tag_list)

    if collection_ids.strip() != '':
        new_collection_list = [int(i) for i in collection_ids.split(',')]
        workingsets = workingsets.filter(collections__overlap=new_collection_list)
    
    if data_sources.strip() != '':
        new_data_sources_list = [int(i) for i in data_sources.split(',')]
        workingsets = workingsets.filter(data_sources__overlap=new_data_sources_list)
    
    if start_date_query and end_date_query:
        workingsets = workingsets.filter(created__range=[start_date_range, end_date_range])

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                workingsets = workingsets.filter(owner_id=owner_id)
            else:
                workingsets = workingsets.filter(owner_id=-1)

    # show only workingsets created by the current user
    if show_only_my_workingsets == "1":
        workingsets = workingsets.filter(owner_id=request.user.id)

    # if show deleted workingsets is 1 then show deleted workingsets
    if show_deleted_workingsets != "1":
        workingsets = workingsets.exclude(is_deleted=True)

    # show workingsets for a specific brand
    if ws_brand != "":
        current_brand = Brand.objects.all().filter(name__iexact=ws_brand)
        workingsets = workingsets.filter(
            group__id__in=list(current_brand.values_list('groups', flat=True)))

    # order by id
    workingsets = workingsets.order_by('id')

    rows_to_return = []
    titles = [
        'phenotypeworkingset_id', 'phenotypeworkingset_name', 'latest_version_id', 'author',
        'owner', 'created_by', 'created_date', 'modified_by', 'modified_date',
        'is_deleted', 'deleted_by', 'deleted_date'
    ]
    if do_not_show_versions != "1":
        titles += ['versions']

    for c in workingsets:
        ret = [
            c.id,
            c.name.encode('ascii', 'ignore').decode('ascii'),
            PhenotypeWorkingset.objects.get(pk=c.id).history.latest().history_id,
            c.author,
            c.owner.username,
            c.created_by.username,
            c.created,
        ]

        if (c.updated_by):
            ret += [c.updated_by.username]
        else:
            ret += [None]

        ret += [
            c.modified,
            c.is_deleted,
        ]

        if (c.is_deleted == True):
            ret += [c.deleted_by.username]
        else:
            ret += [None]

        ret += [c.deleted]

        if do_not_show_versions != "1":
            ret += [
                get_visible_versions_list(request,
                                          PhenotypeWorkingset,
                                          c.id,
                                          is_authenticated_user=True)
            ]

        rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)


#------------------ phenotype working set detail --------------------------
@swagger_auto_schema(method='get', auto_schema=None)
@api_view(['GET'])
def phenotypeworkingset_detail(request,
                      pk,
                      workingset_history_id=None,
                      get_versions_only=None):
    ''' 
        Display the detail of a phenotype working set at a point in time.
    '''


    # validate access
    if not allowed_to_view(request, PhenotypeWorkingset, pk):
        raise PermissionDenied

    if workingset_history_id is not None:
        ws_ver = PhenotypeWorkingset.history.filter(id=pk,
                                           history_id=workingset_history_id)
        if ws_ver.count() == 0: raise Http404

    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = PhenotypeWorkingset.objects.get(
            pk=pk).history.latest().history_id

    # here, check live version
    current_ws = PhenotypeWorkingset.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = chk_children_permission_and_deletion(
        request, PhenotypeWorkingset, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied

    #------------------------
    if get_versions_only is not None:
        if get_versions_only == '1':
            titles = ['versions']
            ret = [
                get_visible_versions_list(request,
                                          PhenotypeWorkingset,
                                          pk,
                                          is_authenticated_user=True)
            ]
            rows_to_return = []
            rows_to_return.append(ordr(list(zip(titles, ret))))
            return Response(rows_to_return, status=status.HTTP_200_OK)
    #--------------------------

    ws = getHistoryPhenotypeWorkingset(workingset_history_id)
    # The history ws contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the ws.
    ws['owner'] = None
    if ws['owner_id'] is not None:
        ws['owner'] = User.objects.get(pk=ws['owner_id']).username

    ws['group'] = None
    if ws['group_id'] is not None:
        ws['group'] = Group.objects.get(pk=ws['group_id']).name

    ws_history_date = ws['history_date']

    tags = []
    tags_comp = ws['tags']
    if tags_comp:
        tags = list(
            Tag.objects.filter(pk__in=tags_comp).values('description', 'id', 'collection_brand'))
    
    collections = []
    collections_comp = ws['collections']
    if collections_comp:
        collections = list(
            Tag.objects.filter(pk__in=collections_comp).values('description', 'id', 'collection_brand'))

    rows_to_return = []
    titles = [
        'phenotypeworkingset_id',
        'phenotypeworkingset_name',
        'version_id',
        'tags',
        'collections',
        'author',
        'description',
        'publication',
        'created_by',
        'created_date',
        'modified_by',
        'modified_date',
        'citation_requirements',
        'owner',
        'owner_access',
        'group',
        'group_access',
        'world_access',
        'is_deleted'  # may come from ws live version / or history
        # , 'deleted_by', 'deleted_date' # no need here
        ,
        'concepts',
        'versions'
    ]
    
    ret = [
        ws['id'],
        ws['name'].encode('ascii', 'ignore').decode('ascii'),
        ws['history_id'],
        tags,
        collections,
        ws['author'],
        ws['description'],
        ws['publications'],
        ws['created_by_username'],
        ws['created'],
        ws['modified_by_username'],
        ws['modified'],
        ws['citation_requirements'],
        ws['owner'],
        dict(Permissions.PERMISSION_CHOICES)[ws['owner_access']],
        ws['group'],
        dict(Permissions.PERMISSION_CHOICES)[ws['group_access']],
        dict(Permissions.PERMISSION_CHOICES)[ws['world_access']],
    ]

    # may come from ws live version / or history
    if (ws['is_deleted'] == True
            or PhenotypeWorkingset.objects.get(pk=pk).is_deleted == True):
        ret += [True]
    else:
        ret += [None]

    # concepts
    ret += [get_phenotypeworkingset_concepts(request, pk, workingset_history_id)]

    # list
    ret += [
        get_visible_versions_list(request,
                                  PhenotypeWorkingset,
                                  pk,
                                  is_authenticated_user=True)
    ]

    rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)

#--------------------------------------------------------------------------
def parse_ident(item):
    item = str(item)
    return int(item.strip(string.ascii_letters))

def get_phenotypeworkingset_concepts(request, pk, workingset_history_id):
    # validate access
    validate_access_to_view(request, PhenotypeWorkingset, pk)


    # here, check live version
    current_ws = PhenotypeWorkingset.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = chk_children_permission_and_deletion(
        request, PhenotypeWorkingset, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied
    

    titles = ['concept_name', 'concept_id', 'concept_version_id',
            'phenotype_name', 'phenotype_id', 'phenotype_version_id',
            'attributes']

    rows_to_return = []
    for element in current_ws.phenotypes_concepts_data:
        attributes = element["Attributes"]

        concept_id = parse_ident(element["concept_id"])
        concept_version = parse_ident(element["concept_version_id"])
        concept = Concept.history.get(id=concept_id, history_id=concept_version)
        
        phenotype_id = parse_ident(element["phenotype_id"])
        phenotype_version = parse_ident(element["phenotype_version_id"])
        phenotype = Phenotype.history.get(id=phenotype_id, history_id=phenotype_version)

        ret = ([concept.name, concept_id, concept_version]
            + [phenotype.name, phenotype_id, phenotype_version]
            + [attributes]
        )

        rows_to_return.append(ordr(list(zip(titles, ret))))
    
    return rows_to_return

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
        Return the codes for a phenotype working set for a specific historical version.
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



