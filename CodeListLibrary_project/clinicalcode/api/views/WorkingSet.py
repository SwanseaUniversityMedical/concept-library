'''
    ---------------------------------------------------------------------------
    API VIEW
    API access to the data to list the various data types (if access is
    permitted) and to access the data structure and components of groups of
    data types.
    ---------------------------------------------------------------------------
'''
from rest_framework import viewsets, status
from rest_framework.decorators import detail_route, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.http.response import Http404
from django.db.models import Q

from ..serializers import *

# The models imports have to be done as follows to avoid Eclipse flagging up
# access to the objects list as ambiguous.
from ...models.Concept import Concept
# from ...models.Component import Component
# from ...models.CodeRegex import CodeRegex
# from ...models.CodeList import CodeList
# from ...models.Code import Code
from ...models.Tag import Tag
# from ...models.ConceptTagMap import ConceptTagMap
from ...models.WorkingSet import WorkingSet
from ...models.WorkingSetTagMap import WorkingSetTagMap
# from ...models.CodingSystem import CodingSystem
from ...models.Brand import Brand

from django.contrib.auth.models import User

from ...db_utils import *
from ...viewmodels.js_tree_model import TreeModelManager
#from django.forms.models import model_to_dict
from ...permissions import *

from collections import OrderedDict
from django.core.exceptions import PermissionDenied
import json
from clinicalcode.context_processors import clinicalcode
from collections import OrderedDict as ordr
from ...utils import *
from numpy.distutils.fcompiler import none

from django.core import serializers
from datetime import datetime
# from snippets.models import Snippet
# from snippets.serializers import SnippetSerializer
from django.core.validators import URLValidator
from View import *
from django.db.models.aggregates import Max
from clinicalcode.models.WorkingSet import WorkingSet


'''
    ---------------------------------------------------------------------------
    View sets (see http://www.django-rest-framework.org/api-guide/viewsets).
    ---------------------------------------------------------------------------
'''


@api_view(['GET'])
def export_workingset_codes(request, pk):
    '''
        Returns the unique set of codes and descriptions for the specified working set saved concepts.
        Returns concepts codes + attributes for a workingset.
    '''

    # Require that the user has access to the base workingset and all its concepts.
    validate_access_to_view(request.user, WorkingSet, pk)
    children_permitted_and_not_deleted , error_dic = chk_children_permission_and_deletion(request.user, WorkingSet, pk)
    if(not children_permitted_and_not_deleted):
        #return Response(error_dic, status=status.HTTP_200_OK)
        raise PermissionDenied 
    
    if request.method == 'GET':
        workingset = WorkingSet.objects.filter(id=pk).exclude(is_deleted=True)
        if workingset.count() == 0: raise Http404

        #make all export csv work on historical data
        current_ws = WorkingSet.objects.get(pk=pk)
        latest_history_id = current_ws.history.latest().history_id
        return export_workingset_codes_byVersionID(request, pk, latest_history_id)

  
    
    
@api_view(['GET'])
def export_workingset_codes_byVersionID(request, pk, workingset_history_id):
    '''
        Returns the unique set of codes and descriptions for the specified working set saved concepts.
        Returns concepts codes + attributes for a workingset
        for a specific version.
    '''

    # Require that the user has access to the base workingset and all its concepts.
    validate_access_to_view(request.user, WorkingSet, pk)
    children_permitted_and_not_deleted , error_dic = chk_children_permission_and_deletion(request.user, WorkingSet, pk, set_history_id=workingset_history_id)
    if(not children_permitted_and_not_deleted):
        #return Response(error_dic, status=status.HTTP_200_OK)
        raise PermissionDenied 
    
    if request.method == 'GET':
        workingset = WorkingSet.objects.filter(id=pk).exclude(is_deleted=True)
        if workingset.count() == 0: raise Http404
        
        #.exclude(is_deleted=True)
        if WorkingSet.history.filter(id=pk, history_id=workingset_history_id).count() == 0: raise Http404

        current_ws_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id) 
        
        # Get the list of concepts in the working set data (this is listed in the
        # concept_informations field with additional, user specified columns. Each
        # row is a concept ID and the column data for these extra columns.
        concepts_info = getGroupOfConceptsByWorkingsetId_historical(pk , workingset_history_id)
        
        concept_data = OrderedDict([])
        title_row = []
        final_titles = []
        rows_to_return = []
        
        # Run through the concept_informations                                                    
        for concept_id, columns in concepts_info.iteritems():
            concept_data[concept_id] = []
            for column_name, column_data in columns.iteritems():
                if concept_id in concept_data:
                    concept_data[concept_id].append(column_data)
                else:
                    concept_data[concept_id] = [column_data]
                    
                if column_name.strip() !="":
                    if not column_name.split('|')[0] in title_row:
                        title_row.append(column_name.split('|')[0])
    
        final_titles = (['code', 'description', 'coding_system', 'concept_id', 'concept_version_id']
                + ['concept_name']
                + ['working_set_id' , 'working_set_version_id' , 'working_set_name']
                + title_row
                )
        
        concept_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id).concept_version 
        
        for concept_id, data in concept_data.iteritems():
            concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version[concept_id]).coding_system.name
            concept_name = Concept.history.get(id=concept_id , history_id=concept_version[concept_id]).name
            rows_no=0
            codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id , concept_version[concept_id])
            #Allow Working sets with zero attributes
            if title_row == [] and data == ['']:
                data = []
            for cc in codes:
                rows_no+=1
                rows_to_return.append(ordr(zip(final_titles,  
                                    [
                                        cc['code'], 
                                        cc['description'].encode('ascii', 'ignore').decode('ascii'),
                                        concept_coding_system,
                                        concept_id,
                                        concept_version[concept_id],
                                        concept_name,
                                        current_ws_version.id,
                                        current_ws_version.history_id, 
                                        current_ws_version.name
                                    ] 
                                    + data
                            )))
                
            if rows_no==0:
                rows_to_return.append(ordr(zip(final_titles,  
                                [
                                    '', 
                                    '',
                                    concept_coding_system,
                                    concept_id,
                                    concept_version[concept_id],
                                    concept_name,
                                    current_ws_version.id,
                                    current_ws_version.history_id,
                                    current_ws_version.name
                                ]
                                + data
                            )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)    

    
    
#############################################################################
#############################################################################
#############################################################################
#@api_view(['GET', 'POST', 'PUT'])
@api_view(['POST'])
def api_workingset_create(request):
    
    # allow only super user (and nor 'ReadOnlyUsers')
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if is_member(request.user, group_name='ReadOnlyUsers'):
        raise PermissionDenied
    
    
    validate_access_to_create()
     
    user_groups = getGroups(request.user)
    
    if request.method == 'POST':
        errors_dict = {}
        is_valid = True

        new_workingset = WorkingSet()
        new_workingset.name = request.data.get('name')
        new_workingset.author = request.data.get('author')
        new_workingset.publication = request.data.get('publication')
        new_workingset.description = request.data.get('description')
        new_workingset.publication_doi = request.data.get('publication_doi')
        new_workingset.publication_link = request.data.get('publication_link') # valid URL    #??
        new_workingset.secondary_publication_links = request.data.get('secondary_publication_links')
        new_workingset.source_reference = request.data.get('source_reference')
        new_workingset.citation_requirements = request.data.get('citation_requirements')
        
        new_workingset.created_by = request.user        
        new_workingset.owner_access = Permissions.EDIT   # int(request.data.get('ownerAccess'))     
        new_workingset.owner_id = request.user.id        # int(request.data.get('owner_id'))     
        
           
        # concepts
        concept_ids_list = request.data.get('concept_informations')
        if concept_ids_list is None or not isinstance(concept_ids_list, list):
            errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
        else:
            # validate concept_ids_list 
            if len(concept_ids_list) == 0:
                errors_dict['concept_informations'] = 'concept_informations must have a valid non-empty concept ids list'
            else:
                if not chkListIsAllIntegers(concept_ids_list):
                    errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
                else: 
                    if len(set(concept_ids_list)) != len(concept_ids_list):
                        errors_dict['concept_informations'] = 'concept_informations must have a unique concept ids list'
                    else:
                        # check all concepts are permitted/or published
                        permittedConcepts = get_list_of_visible_concept_ids(
                                                                            get_visible_live_or_published_concept_versions(request , exclude_deleted = True)
                                                                            , return_id_or_history_id="id")
                        if not (set(concept_ids_list).issubset(set(permittedConcepts))):
                            errors_dict['concept_informations'] = 'invalid concept_informations ids list, all concept ids must be valid and accessible by user'
                        else:
                            concept_informations = convert_concept_ids_to_WSjson(concept_ids_list , no_attributes=True)
                            new_workingset.concept_informations = concept_informations
                            # concept_version always point to latest versions - from API
                            new_workingset.concept_version = getWSConceptsHistoryIDs(concept_informations, concept_ids_list = concept_ids_list)
                    

        

        
        #  group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                new_workingset.group_id = None
                new_workingset.group_access = 1
            else:
                new_workingset.group_id = group_id
                # handle group-Access
                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    new_workingset.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err
            
     
        #-----------------------------------------------------------        
        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            new_workingset.world_access = ret_value
        else:
            errors_dict['world_access'] = err        
                    
        #-----------------------------------------------------------
        # handling tags  
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
        else:
            errors_dict['tags'] = err  
            
           
        
        # Validation
        errors_ws = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_ws = True
        is_valid_ws , errors_ws = isValidWorkingSet(request, new_workingset)
        

        #-----------------------------------------------------------
        if not is_valid or not is_valid_ws:  # errors             
            errors_dict.update(errors_ws)
           # y= {**errors_dict, **errors_ws}
            return Response( #data = json.dumps(errors_dict)
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
 
        #-----------------------------------------------------------
        else:
            new_workingset.save()
            created_WS = WorkingSet.objects.get(pk=new_workingset.pk)
            created_WS.history.latest().delete() 
             
            tag_ids = tags
 
            # new_tag_list = tags
            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids]
                 
            
            # add tags that have not been stored in db
            if tag_ids:
                for tag_id_to_add in new_tag_list:
                    WorkingSetTagMap.objects.get_or_create(workingset=new_workingset, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)
                     
             
            created_WS.changeReason = "Created from API"
            created_WS.save()   
             

            data = {'message': 'Workingset created successfully',
                    'id': created_WS.pk
                    }
            return Response(data = data
                            , content_type="text/json-comment-filtered"
                            , status=status.HTTP_201_CREATED
                            )
        
        
#############################################################################
#############################################################################
#@api_view(['GET', 'POST', 'PUT'])
@api_view(['PUT'])
def api_workingset_update(request):
    
    # allow only super user (and nor 'ReadOnlyUsers')
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if is_member(request.user, group_name='ReadOnlyUsers'):
        raise PermissionDenied
    
    
    validate_access_to_create()
     
    user_groups = getGroups(request.user)
    
    if request.method == 'PUT':
        errors_dict = {}
        is_valid = True

        workingset_id = request.data.get('id') 
        if not isInt(workingset_id):
            errors_dict['id'] = 'workingset_id must be a valid id.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
        
        if WorkingSet.objects.filter(pk=workingset_id).count() == 0: 
            errors_dict['id'] = 'workingset_id not found.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
            
        if not allowed_to_edit(request.user, WorkingSet, workingset_id):
            errors_dict['id'] = 'workingset_id must be a valid accessible working set id.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
        
        update_workingset = WorkingSet.objects.get(pk=workingset_id)
        update_workingset.name = request.data.get('name')
        update_workingset.author = request.data.get('author')
        update_workingset.publication = request.data.get('publication')
        update_workingset.description = request.data.get('description')
        update_workingset.publication_doi = request.data.get('publication_doi')
        update_workingset.publication_link = request.data.get('publication_link') # valid URL    #??
        update_workingset.secondary_publication_links = request.data.get('secondary_publication_links')
        update_workingset.source_reference = request.data.get('source_reference')
        update_workingset.citation_requirements = request.data.get('citation_requirements')
        
        update_workingset.updated_by = request.user        
        update_workingset.modified = datetime.now() 
        #update_workingset.owner_access = Permissions.EDIT   # int(request.data.get('ownerAccess'))     
        #update_workingset.owner_id = request.user.id        # int(request.data.get('owner_id'))     
        
           
        # concepts
        concept_ids_list = request.data.get('concept_informations')
        if concept_ids_list is None or not isinstance(concept_ids_list, list):
            errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
        else:
            # validate concept_ids_list 
            if len(concept_ids_list) == 0:
                errors_dict['concept_informations'] = 'concept_informations must have a valid non-empty concept ids list'
            else:
                if not chkListIsAllIntegers(concept_ids_list):
                    errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
                else: 
                    if len(set(concept_ids_list)) != len(concept_ids_list):
                        errors_dict['concept_informations'] = 'concept_informations must have a unique concept ids list'
                    else:
                        # check all concepts are permitted
                        permittedConcepts = get_list_of_visible_concept_ids(
                                                                            get_visible_live_or_published_concept_versions(request , exclude_deleted = True)
                                                                            , return_id_or_history_id="id")               
                        if not (set(concept_ids_list).issubset(set(permittedConcepts))):
                            errors_dict['concept_informations'] = 'invalid concept_informations ids list, all concept ids must be valid and accessible by user'
                        else:
                            concept_informations = convert_concept_ids_to_WSjson(concept_ids_list , no_attributes=True)
                            update_workingset.concept_informations = concept_informations
                            # concept_version always point to latest versions - from API
                            update_workingset.concept_version = getWSConceptsHistoryIDs(concept_informations, concept_ids_list = concept_ids_list)
                    

        

        
        #  group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                update_workingset.group_id = None
                update_workingset.group_access = 1
            else:
                update_workingset.group_id = group_id
                # handle group-Access
                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    update_workingset.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err
            
     
        #-----------------------------------------------------------        
        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            update_workingset.world_access = ret_value
        else:
            errors_dict['world_access'] = err        
                    
        #-----------------------------------------------------------
        # handling tags  
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
        else:
            errors_dict['tags'] = err  
            
           
        
        # Validation
        errors_ws = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_ws = True
        is_valid_ws , errors_ws = isValidWorkingSet(request, update_workingset)
        

        #-----------------------------------------------------------
        if not is_valid or not is_valid_ws:  # errors             
            errors_dict.update(errors_ws)
           # y= {**errors_dict, **errors_ws}
            return Response( #data = json.dumps(errors_dict)
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
 
        #-----------------------------------------------------------
        else:
            # update ...
            #-----------------------------------------------------
            # get tags
            tag_ids = tags
            new_tag_list = []

            if tag_ids:
                # split tag ids into list
                new_tag_list = [int(i) for i in tag_ids]

            # save the tag ids
            old_tag_list = list(WorkingSetTagMap.objects.filter(workingset=update_workingset).values_list('tag', flat=True))

            # detect tags to add
            tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))

            # detect tags to remove
            tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))

            # add tags that have not been stored in db
            for tag_id_to_add in tag_ids_to_add:
                WorkingSetTagMap.objects.get_or_create(workingset=update_workingset, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)

            # remove tags no longer required in db
            for tag_id_to_remove in tag_ids_to_remove:
                tag_to_remove = WorkingSetTagMap.objects.filter(workingset=update_workingset, tag=Tag.objects.get(id=tag_id_to_remove))
                tag_to_remove.delete()
                
            #-----------------------------------------------------

             
            update_workingset.changeReason = "Updated from API"
            update_workingset.save()   
             

            data = {'message': 'Workingset updated successfully',
                    'id': update_workingset.pk
                    }
            return Response(data = data
                            , content_type="text/json-comment-filtered"
                            , status=status.HTTP_201_CREATED
                            )
        
    
           


##############################################################################
# search my Working Sets 
@api_view(['GET']) 
def myWorkingSets(request):
    '''
        Get the API output for the list of my Working Sets.
    '''
    search = request.query_params.get('search', None)
    workingset_id = request.query_params.get('id', None)
    tag_ids = request.query_params.get('tag_ids', '')
    owner = request.query_params.get('owner_username', '')
    show_only_my_workingsets = request.query_params.get('show_only_my_workingsets', "0")
    show_deleted_workingsets = request.query_params.get('show_deleted_workingsets', "0")
    ws_brand = request.query_params.get('brand', "")
    author = request.query_params.get('author', None)
    do_not_show_versions = request.query_params.get('do_not_show_versions', "0")

    # ensure that user is only allowed to view/edit the relevant workingsets
    workingsets = get_visible_workingsets(request.user)
    
    if workingset_id is not None:
        if workingset_id != '':
            workingsets = workingsets.filter(pk=workingset_id)

    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            workingsets = workingsets.filter(name__icontains=search)

    if author is not None:
        if author != '':
            workingsets = workingsets.filter(author__icontains=author)


    if tag_ids.strip() != '':
        # split tag ids into list
        new_tag_list = [int(i) for i in tag_ids.split(",")]
        workingsets = workingsets.filter(workingsettagmap__tag__id__in=new_tag_list)

    if owner is not None:
        if owner !='':
            if User.objects.filter(username__iexact = owner.strip()).exists():
                owner_id = User.objects.get(username__iexact = owner.strip()).id
                workingsets = workingsets.filter(owner_id = owner_id)
            else:
                workingsets = workingsets.filter(owner_id = -1) 
                
    # show only workingsets created by the current user
    if show_only_my_workingsets == "1":
        workingsets = workingsets.filter(owner_id=request.user.id)

    # if show deleted workingsets is 1 then show deleted workingsets
    if show_deleted_workingsets != "1":
        workingsets = workingsets.exclude(is_deleted=True)


    # show workingsets for a specific brand
    if ws_brand != "":
        current_brand = Brand.objects.all().filter(name__iexact = ws_brand)
        workingsets = workingsets.filter(group__id__in = list(current_brand.values_list('groups', flat=True)))


    # order by id
    workingsets = workingsets.order_by('id')
    
#     # Serializer could be used here...
#     # but needs to return names not ids
#     return Response(list(workingsets.values('id' , 'name' , 'owner'))
#                     , status=status.HTTP_200_OK)       

    rows_to_return = []
    titles = ['workingset_id', 'workingset_name'
            , 'latest_version_id'
            , 'author', 'owner'
            , 'created_by', 'created_date'  
            , 'modified_by', 'modified_date'  
            , 'is_deleted', 'deleted_by', 'deleted_date'
            ]
    if do_not_show_versions != "1":
        titles += ['versions']
    
    

    for c in workingsets:
        ret = [
                c.id,  
                c.name.encode('ascii', 'ignore').decode('ascii'),
                WorkingSet.objects.get(pk=c.id).history.latest().history_id,
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
            ret += [get_visible_versions_list(request, WorkingSet, c.id, is_authenticated_user=True)]
        
        rows_to_return.append(ordr(zip(titles,  ret )))
                                   
    return Response(rows_to_return, status=status.HTTP_200_OK)                                   


                                                
# my working set detail 
@api_view(['GET']) 
def myWorkingset_detail(request, pk, workingset_history_id=None, get_versions_only=None):
    ''' 
        Display the detail of a working set at a point in time.
    '''
    
    if WorkingSet.objects.filter(id=pk).count() == 0: 
        raise Http404
    
    # validate access
    if not allowed_to_view(request.user, WorkingSet, pk):
        raise PermissionDenied
    
    if workingset_history_id is not None:
        ws_ver = WorkingSet.history.filter(id=pk, history_id=workingset_history_id) 
        if ws_ver.count() == 0: raise Http404
        
    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = WorkingSet.objects.get(pk=pk).history.latest().history_id 
        
    # here, check live version
    current_ws = WorkingSet.objects.get(pk=pk)
        
    children_permitted_and_not_deleted , error_dic = chk_children_permission_and_deletion(request.user, WorkingSet, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied
        
    if current_ws.is_deleted == True:
        raise PermissionDenied
    
    #----------------------------------------------------------------------
    do_not_show_codes = request.query_params.get('do_not_show_codes', "0")
    
    #------------------------
    if get_versions_only is not None:
        if get_versions_only == '1':
            titles = ['versions']
            ret = [get_visible_versions_list(request, WorkingSet, pk, is_authenticated_user=True)]
            rows_to_return = []
            rows_to_return.append(ordr(zip(titles,  ret )))
            return Response(rows_to_return, status=status.HTTP_200_OK)   
    #--------------------------
    
    
    ws = getHistoryWorkingset(workingset_history_id)
    # The history ws contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the ws.
    ws['owner'] = None
    if ws['owner_id'] is not None:
        ws['owner'] = User.objects.get(pk=ws['owner_id']).username

    ws['group'] = None
    if ws['group_id'] is not None: 
        ws['group'] = Group.objects.get(pk=ws['group_id']).name


    ws_history_date = ws['history_date']
    
    tags =  []
    tags_comp = getHistoryTags_Workingset(pk, ws_history_date)
    if tags_comp:
        tag_list = [i['tag_id'] for i in tags_comp if 'tag_id' in i]
        tags = list(Tag.objects.filter(pk__in=tag_list).values('description', 'id'))
    
    rows_to_return = []
    titles = [
              'workingset_id', 'workingset_name', 'version_id'
            , 'tags'
            , 'author'
            , 'description'
            , 'publication' 
            
            , 'created_by', 'created_date'  
            , 'modified_by', 'modified_date'  


            , 'publication_doi'
            , 'publication_link'
            , 'secondary_publication_links'

            , 'source_reference'
            , 'citation_requirements'
            
            , 'owner', 'owner_access'
            , 'group', 'group_access'
            , 'world_access'
            
            , 'is_deleted'  # may come from ws live version / or history
            # , 'deleted_by', 'deleted_date' # no need here
            
            , 'concepts'
            ]
    if do_not_show_codes != "1":
        titles += ['codes']
        
    titles += ['versions']
    
    ret = [
            ws['id'],
            ws['name'].encode('ascii', 'ignore').decode('ascii'),
            ws['history_id'],
            tags,
            ws['author'],
            ws['description'],
            ws['publication'],
            
            ws['created_by_username'],
            ws['created'],   
            ws['modified_by_username'],
            ws['modified'],

            ws['publication_doi'],
            ws['publication_link'],
            ws['secondary_publication_links'],

            ws['source_reference'],
            ws['citation_requirements'],
            
            ws['owner'] ,
            dict(Permissions.PERMISSION_CHOICES)[ws['owner_access']],
            ws['group'],
            dict(Permissions.PERMISSION_CHOICES)[ws['group_access']],
            dict(Permissions.PERMISSION_CHOICES)[ws['world_access']],
        ]
            
    # may come from ws live version / or history    
    if (ws['is_deleted'] == True or WorkingSet.objects.get(pk=pk).is_deleted==True):
        ret += [True]
    else:
        ret += [None]
           
    # concepts 
    ret += [get_workingset_concepts(request, pk, workingset_history_id)]
    
    # codes
    if do_not_show_codes != "1":
        ret += [get_workingset_codes(request, pk, workingset_history_id)]
  
    ret += [get_visible_versions_list(request, WorkingSet, pk, is_authenticated_user=True)]
     
    rows_to_return.append(ordr(zip(titles,  ret )))
                                   
    return Response(rows_to_return, status=status.HTTP_200_OK)                
    
    
    
def get_workingset_concepts(request, pk, workingset_history_id):
    """
        Return concepts info for a working set for a specific historical version.
    """
    
    # validate access
    validate_access_to_view(request.user, WorkingSet, pk) 
    
    #exclude(is_deleted=True)
    if WorkingSet.objects.filter(id=pk).count() == 0:
        raise Http404         
        
    #exclude(is_deleted=True)
    if WorkingSet.history.filter(id=pk , history_id=workingset_history_id).count() == 0:
        raise Http404          
        
    # here, check live version
    current_ws = WorkingSet.objects.get(pk=pk)
        
    children_permitted_and_not_deleted , error_dic = chk_children_permission_and_deletion(request.user, WorkingSet, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied
        
    if current_ws.is_deleted == True:
        raise PermissionDenied
    #----------------------------------------------------------------------

        
    #current_ws_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id)   
        
    # Get the list of concepts in the working set data (this is listed in the
    # concept_informations field with additional, user specified columns. Each
    # row is a concept ID and the column data for these extra columns.
    rows = getGroupOfConceptsByWorkingsetId_historical(pk , workingset_history_id)


    concept_data = OrderedDict([])
    title_row = []
    
    # Run through the concept_informations rows = one concept at a time.
    for concept_id, columns in rows.iteritems():
        concept_data[concept_id] = []
        for column_name, column_data in columns.iteritems():
            if concept_id in concept_data:
                concept_data[concept_id].append(column_data)
            else:
                concept_data[concept_id] = [column_data]
                 
            if column_name.strip() !="":
                if not column_name.split('|')[0] in title_row:
                    title_row.append(column_name.split('|')[0])

    titles = ['concept_id', 'concept_version_id', 'concept_name'] + title_row
                
    concept_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id).concept_version 

    rows_to_return = []
    for concept_id, data in concept_data.iteritems():
        ret = ([concept_id, concept_version[concept_id]] 
                + [Concept.history.get(id=concept_id , history_id=concept_version[concept_id] ).name] 
                + data
            )
                
        rows_to_return.append(ordr(zip(titles,  ret )))
            

    return rows_to_return         
    


def get_workingset_codes(request, pk, workingset_history_id):
    """
        Return codes+attributes for a working set for a specific historical version.
    """
    
    # validate access
    validate_access_to_view(request.user, WorkingSet, pk) 
    
    #exclude(is_deleted=True)
    if WorkingSet.objects.filter(id=pk).count() == 0:
        raise Http404         
        
    #exclude(is_deleted=True)
    if WorkingSet.history.filter(id=pk , history_id=workingset_history_id).count() == 0:
        raise Http404          
        
    # here, check live version
    current_ws = WorkingSet.objects.get(pk=pk)
        
    children_permitted_and_not_deleted , error_dic = chk_children_permission_and_deletion(request.user, WorkingSet, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied
        
    if current_ws.is_deleted == True:
        raise PermissionDenied
    #----------------------------------------------------------------------
         
    #current_ws_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id)   
    
    
    # Get the list of concepts in the working set data (this is listed in the
    # concept_informations field with additional, user specified columns. Each
    # row is a concept ID and the column data for these extra columns.
    rows = getGroupOfConceptsByWorkingsetId_historical(pk , workingset_history_id)


    concept_data = OrderedDict([])
    title_row = []
    
    # Run through the concept_informations rows = one concept at a time.
    for concept_id, columns in rows.iteritems():
        concept_data[concept_id] = []
        for column_name, column_data in columns.iteritems():
            if concept_id in concept_data:
                concept_data[concept_id].append(column_data)
            else:
                concept_data[concept_id] = [column_data]
                 
            if column_name.strip() !="":
                if not column_name.split('|')[0] in title_row:
                    title_row.append(column_name.split('|')[0])

    titles = (['code', 'description', 'concept_id']
                + ['concept_version_id']
                + ['concept_name']
                #+ ['working_set_id' , 'working_set_version_id' , 'working_set_name']
                + title_row
                )

    concept_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id).concept_version 

    rows_to_return = []
    for concept_id, data in concept_data.iteritems():
        rows_no=0
        codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id , concept_version[concept_id])
        #Allow Working sets with zero attributes
        if title_row == [] and data == ['']:
            data = []
        for cc in codes:
            rows_no+=1
            ret = ([
                        cc['code'], 
                        cc['description'].encode('ascii', 'ignore').decode('ascii'),
                        concept_id
                    ] 
                    + [concept_version[concept_id]] 
                    + [Concept.history.get(id=concept_id , history_id=concept_version[concept_id] ).name] 
                    #+ [current_ws_version.id ,current_ws_version.history_id , current_ws_version.name] 
                    + data
                )
                    
            rows_to_return.append(ordr(zip(titles,  ret )))
            
        if rows_no==0:
            ret = ([
                        '', 
                        '',
                        concept_id
                    ] 
                    + [concept_version[concept_id]] 
                    + [Concept.history.get(id=concept_id , history_id=concept_version[concept_id] ).name] 
                    #+ [current_ws_version.id ,current_ws_version.history_id , current_ws_version.name] 
                    + data
                )
                    
            rows_to_return.append(ordr(zip(titles,  ret )))

    return rows_to_return         
    

    
  





