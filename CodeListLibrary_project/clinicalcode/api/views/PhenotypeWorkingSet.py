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

def parse_ident(item):
    item = str(item)
    return int(item.strip(string.ascii_letters))

#------------------ phenotype working sets api --------------------------------
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def published_phenotypeworkingsets(request, pk=None):
    return getPhenotypeWorkingSets(request, is_authenticated=False, pk=pk)

@api_view(['GET'])
def phenotypeworkingsets(request, pk=None):
    return getPhenotypeWorkingSets(request, is_authenticated=True, pk=pk)

#------------------ phenotype working sets --------------------------------
@robots2()
def getPhenotypeWorkingSets(request, is_authenticated=False, pk=None):
    '''
        Get the API output for the list of my Phenotype Working Sets.
    '''
    search = request.query_params.get('search', '')

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
    selected_phenotype_types = request.query_params.get('selected_workingset_types', '')

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
    
    search = re.sub(' +', ' ', search.strip())
    owner = re.sub(' +', ' ', owner.strip())
    author = re.sub(' +', ' ', author.strip())
    selected_phenotype_types = selected_phenotype_types.strip().lower()

    filter_cond = " 1=1 "
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published
    show_top_version_only = True

    ph_workingset_types_list, ph_workingset_types_order = get_brand_associated_workingset_types(request, brand=None)
    ph_workingset_selected_types_list = {ph_workingset_types_order[k]: v for k, v in enumerate(ph_workingset_types_list)}
    
    search_by_id = False
    id_match = re.search(r"(?i)^PH\d+$", search)
    if id_match:
        if id_match.group() == id_match.string:
            is_valid_id, err, ret_int_id = chk_valid_id(request, set_class=PhenotypeWorkingset, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id =" + str(ret_int_id) + " ) "    

    collections, filter_cond = apply_filter_condition(query='collections', selected=collection_ids, conditions=filter_cond)
    tags, filter_cond = apply_filter_condition(query='tags', selected=tag_ids, conditions=filter_cond)
    sources, filter_cond = apply_filter_condition(query='data_sources', selected=data_sources, conditions=filter_cond)
    selected_phenotype_types_list, filter_cond = apply_filter_condition(query='workingset_type', selected=selected_phenotype_types, conditions=filter_cond, data=ph_workingset_types_list)
    daterange, filter_cond = apply_filter_condition(query='daterange', selected={'start': [start_date_query, start_date_range], 'end': [end_date_query, end_date_range]}, conditions=filter_cond)

    # show working set for a specific brand
    force_brand = None
    if ws_brand != "":
        force_brand = "-xzy"  # an invalid brand name
        if Brand.objects.all().filter(name__iexact=ws_brand.strip()).exists():
            current_brand = Brand.objects.get(name__iexact=ws_brand.strip())
            force_brand = current_brand.name
    
    if is_authenticated:
        # my working sets
        if show_only_my_workingsets == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)

        # show deleted
        if show_deleted_workingsets != "1":
            exclude_deleted = True
        else:
            exclude_deleted = False

        # by owner
        if owner is not None:
            if owner != '':
                if User.objects.filter(username__iexact=owner.strip()).exists():
                    owner_id = User.objects.get(username__iexact=owner.strip()).id
                    filter_cond += " AND owner_id=" + str(owner_id)
                else:
                    # username not found
                    filter_cond += " AND owner_id= -1 "

    # by id
    if workingset_id is not None:
        workingset_id = str(parse_ident(workingset_id))
        if workingset_id != '':
            filter_cond += " AND id=" + workingset_id

    # show my workingsets
    workingsets = get_visible_live_or_published_phenotype_workingset_versions(
                                                            request,
                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                            search=[search, ''][search_by_id],
                                                            author=author,
                                                            exclude_deleted=exclude_deleted,
                                                            filter_cond=filter_cond,
                                                            show_top_version_only=show_top_version_only,
                                                            force_brand=force_brand,
                                                            search_name_only = False
                                                            )

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
            c['id'],
            c['name'].encode('ascii', 'ignore').decode('ascii'),
            PhenotypeWorkingset.objects.get(pk=c['id']).history.latest().history_id,
            c['author'],
            c['owner_name'],
            c['created_by_username'],
            c['created'],
        ]

        if (c['updated_by_id']):
            ret += [c['modified_by_username']]
        else:
            ret += [None]

        ret += [
            c['modified'],
            c['is_deleted'],
        ]

        if (c['is_deleted'] == True):
            ret += [c['deleted_by_username']]
        else:
            ret += [None]

        ret += [c['deleted']]

        if do_not_show_versions != "1":
            ret += [
                get_visible_versions_list(request,
                                          PhenotypeWorkingset,
                                          c['id'],
                                          is_authenticated_user=is_authenticated)
            ]

        rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)


#------------------ phenotype working set detail --------------------------
@swagger_auto_schema(method='get', auto_schema=None)
@api_view(['GET'])
def phenotypeworkingset_detail(request, pk, workingset_history_id=None):
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

    return getPhenotypeWorkingSetDetail(request,
                              pk=pk,
                              is_authenticated=True,
                              workingset_history_id=workingset_history_id)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def phenotypeworkingset_detail_PUBLIC(request, pk, workingset_history_id=None):
    ''' 
        Display the published detail(s) of a phenotype working set
    '''
    if PhenotypeWorkingset.objects.filter(id=pk).count() == 0:
        raise Http404

    if workingset_history_id is not None:
        ws_ver = PhenotypeWorkingset.history.filter(id=pk,
                                           history_id=workingset_history_id)
        if ws_ver.count() == 0: raise Http404

    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = PhenotypeWorkingset.objects.get(
            pk=pk).history.latest().history_id

    is_published = checkIfPublished(PhenotypeWorkingset, pk, workingset_history_id)

    if not is_published:
        raise PermissionDenied

    return getPhenotypeWorkingSetDetail(request,
                              pk=pk,
                              is_authenticated=False,
                              workingset_history_id=workingset_history_id)


def getPhenotypeWorkingSetDetail(request, pk, is_authenticated=False, workingset_history_id=None, get_versions_only=None):
    if get_versions_only is not None:
        if get_versions_only == '1':
            titles = ['versions']
            ret = [
                get_visible_versions_list(request,
                                          PhenotypeWorkingset,
                                          pk,
                                          is_authenticated_user=is_authenticated)
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
    titles = ([
        'phenotypeworkingset_id',
        'phenotypeworkingset_name',
        'version_id',
        'tags',
        'collections',
        'author',
        'description',
        'publication',
        'citation_requirements']
        + 
        (['created_by', 'created_date', 'modified_by', 'modified_date',
          'owner', 'owner_access', 'group', 'group_access', 'world_access', 'is_deleted'] 
            if is_authenticated else [])
        + [
        'concepts',
        'versions'
    ])
    
    ret = [
        ws['id'],
        ws['name'].encode('ascii', 'ignore').decode('ascii'),
        ws['history_id'],
        tags,
        collections,
        ws['author'],
        ws['description'],
        ws['publications'],
        ws['citation_requirements'],
        ws['created_by_username'],
    ]

    if is_authenticated:
        ret = ret + [
        ws['created'],
        ws['modified_by_username'],
        ws['modified'],
        ws['owner'],
        dict(Permissions.PERMISSION_CHOICES)[ws['owner_access']],
        ws['group'],
        dict(Permissions.PERMISSION_CHOICES)[ws['group_access']],
        dict(Permissions.PERMISSION_CHOICES)[ws['world_access']]]

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
                                  is_authenticated_user=is_authenticated)
    ]

    rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)

#--------------------------------------------------------------------------

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



