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

from serializers import *

# The models imports have to be done as follows to avoid Eclipse flagging up
# access to the objects list as ambiguous.
from ..models.Concept import Concept
from ..models.Component import Component
from ..models.CodeRegex import CodeRegex
from ..models.CodeList import CodeList
from ..models.Code import Code
from ..models.Tag import Tag
from ..models.ConceptTagMap import ConceptTagMap
from ..models.WorkingSet import WorkingSet
from ..models.WorkingSetTagMap import WorkingSetTagMap
from ..models.CodingSystem import CodingSystem
#from clinicalcode.models.CodingSystem import CodingSystem

from ..models.PublishedConcept import PublishedConcept

from ..db_utils import (
    getConceptTreeByConceptId, getParentConceptTreeByConceptId,
    getGroupOfCodesByConceptId, getGroupOfConceptsByWorkingsetId,
    chk_children_permission_and_deletion,
    chk_deleted_children, getGroupOfCodesByConceptId_HISTORICAL,
    getHistoryConcept, getConceptsFromJSON,
    convert_concept_ids_to_WSjson, chkListIsAllIntegers,
    getWSConceptsHistoryIDs, isValidWorkingSet,
    getGroupOfConceptsByWorkingsetId_historical,
    modifyConceptChangeReason, saveDependentConceptsChangeReason,
    getPublishedConceptByVersionId, getPublishedConcepts
)
from ..viewmodels.js_tree_model import TreeModelManager
#from django.forms.models import model_to_dict
from ..permissions import *

from collections import OrderedDict
from django.core.exceptions import PermissionDenied
import json
from clinicalcode.context_processors import clinicalcode
from collections import OrderedDict as ordr
from ..utils import *
from numpy.distutils.fcompiler import none

from django.core import serializers
from datetime import datetime
# from snippets.models import Snippet
# from snippets.serializers import SnippetSerializer
from django.core.validators import URLValidator

'''
    ---------------------------------------------------------------------------
    View sets (see http://www.django-rest-framework.org/api-guide/viewsets).
    ---------------------------------------------------------------------------
'''

class ConceptViewSet(viewsets.ReadOnlyModelViewSet): 
    '''
        Get the API output for the list of concepts.
    '''
    queryset = Concept.objects.none()
    serializer_class = ConceptSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Restrict this to just those concepts that are visible to the user.
        '''
        queryset = get_visible_concepts(self.request.user)
        search = self.request.query_params.get('search', None)
        concept_id = self.request.query_params.get('id')
        if search is not None:
            queryset = queryset.filter(name__icontains=search).exclude(id=concept_id).exclude(is_deleted=True)
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
class CodeViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of codes.
    '''
    queryset = Code.objects.none()
    serializer_class = CodeSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Restrict this to just those codes that are visible to the user.
        '''
        code_list_id = self.request.query_params.get('code_list_id', None)
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


#--------------------------------------------------------------------------
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of tags (no permissions involved).
    '''
    queryset = Tag.objects.none()
    serializer_class = TagSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Get all the tags but limit if we are searching.
        '''
        queryset = Tag.objects.all()
        keyword_search = self.request.query_params.get('keyword', None)
        if keyword_search is not None:
            queryset = queryset.filter(description__icontains=keyword_search)
        return queryset


    def filter_queryset(self, queryset):
        '''
            Override the default filtering.
            By default we get tags ordered by creation date even if
            we provide sorted data from get_queryset(). We have to sort the
            data here.
        '''
        queryset = super(TagViewSet, self).filter_queryset(queryset)
        return queryset.order_by('description')

#     def perform_create(self, serializer):
#         raise PermissionDenied


#     def perform_update(self, serializer):
#         raise PermissionDenied
    

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------

'''
    ---------------------------------------------------------------------------
    Additional function-based views to handle specific requests.
    ---------------------------------------------------------------------------
'''
@api_view(['GET'])
def child_concepts(request, pk):
    '''
        Return the children of the specified concept (pk).
    '''
    if request.method == 'GET':
        concept = Concept.objects.filter(id=pk).exclude(is_deleted=True)
        if concept.count() == 0: raise Http404

        # Use a SQL function to extract this data.
        rows = getConceptTreeByConceptId(pk)
        tree = {
            'id': pk,
            'text': 'root - ' + concept.first().name,
            'children': [],
            'state': {'opened': True}
        }
        treeManager = TreeModelManager()
        if rows:
            treeManager.build_child_tree(tree, pk, rows)

        return Response(tree, status=status.HTTP_200_OK)


@api_view(['GET'])
def parent_concepts(request, pk):
    '''
        Return the parents of the specified concept (pk).
    '''
    if request.method == 'GET':
        concept = Concept.objects.filter(id=pk).exclude(is_deleted=True)
        if concept.count() == 0: raise Http404

        # Use a SQL function to extract this data.
        rows = getParentConceptTreeByConceptId(pk)
        tree = {
            'text': 'root',
            'children': [],
            'state': {'opened': True}}
        treeManager = TreeModelManager()
        if rows:
            # get concept id by max depth
            max_depth_item = max(rows, key=lambda item: item['level_depth'])
            # build tree from the list of concepts returned
            treeManager.build_parent_tree(tree, max_depth_item['concept_id'], rows)

        return Response(tree, status=status.HTTP_200_OK)


@api_view(['GET']) 
def export_concept_codes(request, pk):
    '''
        Return the unique set of codes and descriptions for the specified
        concept (pk).
    '''
    # Require that the user has access to the base concept.
    validate_access_to_view(request.user, Concept, pk)
    if not (allowed_to_view_children(request.user, Concept, pk)
            and
            chk_deleted_children(request.user, Concept, pk, returnErrors = False)
           ):
        raise PermissionDenied
    #
    if request.method == 'GET':
        concept = Concept.objects.filter(id=pk).exclude(is_deleted=True)
        if concept.count() == 0: raise Http404
        
        rows_to_return = []
        titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']
        
        current_concept = Concept.objects.get(pk=pk)

        # Use a SQL function to extract this data.
        rows = getGroupOfCodesByConceptId(pk)
        for row in rows:
            rows_to_return.append(ordr(zip(titles,  
                                [
                                    row['code'],  
                                    row['description'].encode('ascii', 'ignore').decode('ascii'),
                                    pk,
                                    current_concept.history.latest().history_id,
                                    current_concept.name,
                                ]
                                )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)

    
    
@api_view(['GET']) 
def export_concept_codes_byVersionID(request, pk, concept_history_id):
    '''
        Return the unique set of codes and descriptions for the specified
        concept (pk),
        for a specific historical concept version (concept_history_id).
    '''
    # Require that the user has access to the base concept.
    validate_access_to_view(request.user, Concept, pk)
    if not (allowed_to_view_children(request.user, Concept, pk)
            and
            chk_deleted_children(request.user, Concept, pk, returnErrors = False)
           ):
        raise PermissionDenied
    #
    if request.method == 'GET':
        concept = Concept.objects.filter(id=pk).exclude(is_deleted=True)
        if concept.count() == 0: raise Http404
        
        concept_ver = Concept.history.filter(id=pk, history_id=concept_history_id) #.exclude(is_deleted=True)
        if concept_ver.count() == 0: raise Http404
        
        rows_to_return = []
        titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']
        
        current_concept = Concept.objects.get(pk=pk)

        # Use db_util function to extract this data.
        history_concept = getHistoryConcept(concept_history_id)
    
        rows = getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)
        for row in rows:
            rows_to_return.append(ordr(zip(titles,  
                                [
                                    row['code'],  
                                    row['description'].encode('ascii', 'ignore').decode('ascii'),
                                    pk,
                                    concept_history_id,
                                    history_concept['name'],
                                ]
                                )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)
    
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

        #-----------------------------------------------------------------------
#         show_version_number = True
#         # Get the list of concepts in the working set data (this is listed in the
#         # concept_informations field with additional, user specified columns. Each
#         # row is a concept ID and the column data for these extra columns.
#         concepts_info = getGroupOfConceptsByWorkingsetId(pk)
#         
#         concept_data = OrderedDict([])
#         title_row = []
#         final_titles = []
#         rows_to_return = []
#         
#         # Run through the concept_informations                                                    
#         for concept_id, columns in concepts_info.iteritems():
#             concept_data[concept_id] = []
#             for column_name, column_data in columns.iteritems():
#                 if concept_id in concept_data:
#                     concept_data[concept_id].append(column_data)
#                 else:
#                     concept_data[concept_id] = [column_data]
#                     
#                 if column_name.strip() !="":
#                     if not column_name.split('|')[0] in title_row:
#                         title_row.append(column_name.split('|')[0])
#     
#         final_titles = (['code', 'description', 'concept_id']
#                 + [[] , ['concept_version_id']][show_version_number]
#                 + ['concept_name']
#                 + title_row
#                 )
#         
#         concept_version = WorkingSet.objects.get(pk=pk).concept_version
#         
#         for concept_id, data in concept_data.iteritems():
#             ##data.reverse()
#             rows_no=0
#             codes = getGroupOfCodesByConceptId(concept_id)
#             #Allow Working sets with zero attributes
#             if title_row == [] and data == ['']:
#                 data = []
#             for cc in codes:
#                 rows_no+=1
#                 rows_to_return.append(ordr(zip(final_titles,  
#                                     [
#                                         cc['code'], 
#                                         cc['description'].encode('ascii', 'ignore').decode('ascii'),
#                                         concept_id
#                                     ]
#                                     + [[] , [concept_version[concept_id]]][show_version_number]
#                                     + [Concept.objects.get(pk=concept_id).name]
#                                     + data
#                             )))
#                 
#             if rows_no==0:
#                 rows_to_return.append(ordr(zip(final_titles,  
#                                 [
#                                     '', 
#                                     '',
#                                     concept_id
#                                 ]
#                                 + [[] , [concept_version[concept_id]]][show_version_number]
#                                 + [Concept.objects.get(pk=concept_id).name] 
#                                 + data
#                             )))
#     
#         return Response(rows_to_return, status=status.HTTP_200_OK)
    
    
    
@api_view(['GET'])
def export_workingset_codes_byVersionID(request, pk, workingset_history_id):
    '''
        Returns the unique set of codes and descriptions for the specified working set saved concepts.
        Returns concepts codes + attributes for a workingset
        for a specific version.
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
        
        #.exclude(is_deleted=True)
        if WorkingSet.history.filter(id=pk, history_id=workingset_history_id).count() == 0: raise Http404

        current_ws_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id) 
        
        show_version_number = True
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
    
        final_titles = (['code', 'description', 'concept_id']
                + [[] , ['concept_version_id']][show_version_number]
                + ['concept_name']
                + ['working_set_id' , 'working_set_version_id' , 'working_set_name']
                + title_row
                )
        
        concept_version = WorkingSet.history.get(id=pk , history_id=workingset_history_id).concept_version 
        
        for concept_id, data in concept_data.iteritems():
            ##data.reverse()
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
                                        concept_id
                                    ]
                                    + [[] , [concept_version[concept_id]]][show_version_number]
                                    + [Concept.history.get(id=concept_id , history_id=concept_version[concept_id] ).name]
                                    + [current_ws_version.id ,current_ws_version.history_id , current_ws_version.name] 
                                    + data
                            )))
                
            if rows_no==0:
                rows_to_return.append(ordr(zip(final_titles,  
                                [
                                    '', 
                                    '',
                                    concept_id
                                ]
                                + [[] , [concept_version[concept_id]]][show_version_number]
                                + [Concept.history.get(id=concept_id , history_id=concept_version[concept_id] ).name] 
                                + [current_ws_version.id ,current_ws_version.history_id , current_ws_version.name]
                                + data
                            )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)    


@api_view(['GET'])
def customRoot(request):
    '''
        Custom API Root page.
        Replace pk=0 (i.e.'/0/' in the url) with the relevant id.
        Replace history=0 (i.e.'/0/' in the url) with the relevant version_id.
    '''
    from django.shortcuts import render    
    from rest_framework.reverse import reverse
    from rest_framework.views import APIView

    
    api_absolute_ip = str(request.build_absolute_uri(reverse('api:api_export_concept_codes', kwargs={'pk': 0}))).split('/')[2]
    site = 'https://'+api_absolute_ip
    
  
    
    urls_available = {
        'export_concept_codes': site + reverse('api:api_export_concept_codes', kwargs={'pk': 0}),
        'export_concept_codes_byVersionID': site + reverse('api:api_export_concept_codes_byVersionID', kwargs={'pk': 0, 'concept_history_id': 1}),
        
        'export_workingset_codes': site + reverse('api:api_export_workingset_codes', kwargs={'pk': 0}),
        'export_workingset_codes_byVersionID': site + reverse('api:api_export_workingset_codes_byVersionID', kwargs={'pk': 0, 'workingset_history_id': 1})
    }
    

    return render(request,
                   'rest_framework/API-root-pg.html',
                   urls_available
                   )

    
    
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
                        # check all concepts are permitted
                        permittedConcepts = get_visible_concepts(request.user).exclude(is_deleted=True)                
                        if not (set(concept_ids_list).issubset(set(permittedConcepts.values_list('id' , flat=True)))):
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
                        permittedConcepts = get_visible_concepts(request.user).exclude(is_deleted=True)                
                        if not (set(concept_ids_list).issubset(set(permittedConcepts.values_list('id' , flat=True)))):
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
        
    
           

#############################################################################
#############################################################################
#@api_view(['GET', 'POST', 'PUT'])
@api_view(['POST'])
def api_concept_create(request):
    
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

        new_concept = Concept()
        new_concept.name = request.data.get('name')  
        new_concept.author = request.data.get('author') 
        new_concept.publication = request.data.get('publication')  
        new_concept.description = request.data.get('description') 
        new_concept.publication_doi = request.data.get('publication_doi')
        new_concept.publication_link = request.data.get('publication_link')  # valid URL 
        new_concept.secondary_publication_links = request.data.get('secondary_publication_links')
        new_concept.source_reference = request.data.get('source_reference')
        new_concept.citation_requirements = request.data.get('citation_requirements')

        new_concept.paper_published = request.data.get('paper_published')
        new_concept.validation_performed = request.data.get('validation_performed')
        new_concept.validation_description = request.data.get('validation_description')
        new_concept.entry_date = datetime.now()
         
        new_concept.created_by = request.user        
        new_concept.owner_access = Permissions.EDIT   # int(request.data.get('ownerAccess'))     
        new_concept.owner_id = request.user.id        # int(request.data.get('owner_id'))     
          
        # handle coding_system
        is_valid_data, err, ret_value = chk_coding_system(request.data.get('coding_system'))
        if is_valid_data:
            new_concept.coding_system = ret_value
        else:
            errors_dict['coding_system'] = err

        
        #  group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                new_concept.group_id = None
                new_concept.group_access = 1
            else:
                new_concept.group_id = group_id
                # handle group-Access
                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    new_concept.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err
            
 
        
        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            new_concept.world_access = ret_value
        else:
            errors_dict['world_access'] = err        
        
                  
        
        # handling tags  
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
        else:
            errors_dict['tags'] = err  
                    
                
        #-----------------------------------------------------------
        is_valid_components = False
        is_valid_data, err, ret_value = chk_components_and_codes(request.data.get('components'))
        if is_valid_data:
            is_valid_components = True
            components = ret_value
        else:
            errors_dict['components'] = err  
            
        

        
        # Validation

        errors_concept = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_cp = True
        is_valid_cp , errors_concept = isValidConcept(request, new_concept) #??
        
        
        #-----------------------------------------------------------
        if not is_valid or not is_valid_cp:  # errors             
            errors_dict.update(errors_concept)
           # y= {**errors_dict, **errors_concept}
            return Response( #data = json.dumps(errors_dict)
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
  
        #-----------------------------------------------------------
        else:
            new_concept.save()
            created_concept = Concept.objects.get(pk=new_concept.pk)
            created_concept.history.latest().delete() 
 
            #-- Tags -------------------------------             
            tag_ids = tags  
            # new_tag_list = tags
            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids]
                  
            # add tags that have not been stored in db
            if tag_ids:
                for tag_id_to_add in new_tag_list:
                    ConceptTagMap.objects.get_or_create(concept=new_concept, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)
                      
                      
            #-- Components/codelists/codes --------
            for comp in components:
                component = Component.objects.create(
                                    comment=comp['comment'],
                                    component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT, # fixed since it is the only allowed type (not comp['component_type'])
                                    concept=new_concept,
                                    created_by=request.user,
                                    logical_type=comp['logical_type'],
                                    name=comp['name']
                                    )
                
                code_list = CodeList.objects.create(component=component, description='-')
                codeRegex = CodeRegex.objects.create(
                                    component=component,
                                    code_list=code_list,
                                    regex_type=CodeRegex.SIMPLE,
                                    regex_code='',
                                    column_search=CodeRegex.CODE,
                                    sql_rules=''
                                    )
                row_count = 0
                # create codes
                for row in comp['codes']:
                    row_count += 1
                    # Need to check stripped codes
                    if row['code'].strip() == '':      continue
                    obj, created = Code.objects.get_or_create(
                                    code_list=code_list,
                                    code=row['code'],
                                    defaults={
                                            'description': row['description']
                                        }
                                    )
            #--------------------------------------
            #--------------------------------------
              
            created_concept.changeReason = "Created from API"
            created_concept.save()   
              

            data = {'message': 'Concept created successfully',
                    'id': created_concept.pk
                    }
            return Response(data = data
                            , content_type="text/json-comment-filtered"
                            , status=status.HTTP_201_CREATED
                            )
        
        
#############################################################################
#############################################################################
#@api_view(['GET', 'POST', 'PUT'])
@api_view(['PUT'])
def api_concept_update(request):
    
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
        
        concept_id = request.data.get('id') 
        if not isInt(concept_id):
            errors_dict['id'] = 'concept_id must be a valid id.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
        
        if Concept.objects.filter(pk=concept_id).count() == 0: 
            errors_dict['id'] = 'concept_id not found.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
            
        if not allowed_to_edit(request.user, Concept, concept_id):
            errors_dict['id'] = 'concept_id must be a valid accessible concept id.' 
            return Response( 
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
        
        
        update_concept = Concept.objects.get(pk=concept_id)
        update_concept.name = request.data.get('name')  
        update_concept.author = request.data.get('author') 
        update_concept.publication = request.data.get('publication')  
        update_concept.description = request.data.get('description') 
        update_concept.publication_doi = request.data.get('publication_doi')
        update_concept.publication_link = request.data.get('publication_link')  # valid URL 
        update_concept.secondary_publication_links = request.data.get('secondary_publication_links')
        update_concept.source_reference = request.data.get('source_reference')
        update_concept.citation_requirements = request.data.get('citation_requirements')

        update_concept.paper_published = request.data.get('paper_published')
        update_concept.validation_performed = request.data.get('validation_performed')
        update_concept.validation_description = request.data.get('validation_description')
        
        update_concept.modified = datetime.now()        
        update_concept.modified_by = request.user
                
        #update_concept.owner_access = Permissions.EDIT   # int(request.data.get('ownerAccess'))     
        #update_concept.owner_id = request.user.id        # int(request.data.get('owner_id'))     
          
        # handle coding_system
        is_valid_data, err, ret_value = chk_coding_system(request.data.get('coding_system'))
        if is_valid_data:
            update_concept.coding_system = ret_value
        else:
            errors_dict['coding_system'] = err


        
        #  group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                update_concept.group_id = None
                update_concept.group_access = 1
            else:
                update_concept.group_id = group_id
                # handle group-Access
                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    update_concept.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err
            
 
        
        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            update_concept.world_access = ret_value
        else:
            errors_dict['world_access'] = err        
        
                  
        
        # handling tags  
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
        else:
            errors_dict['tags'] = err  
                    
                
        #-----------------------------------------------------------
        is_valid_components = False
        is_valid_data, err, ret_value = chk_components_and_codes(request.data.get('components'))
        if is_valid_data:
            is_valid_components = True
            components = ret_value
        else:
            errors_dict['components'] = err  
            
        

        
        # Validation

        errors_concept = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_cp = True
        is_valid_cp , errors_concept = isValidConcept(request, update_concept) #??
        
        
        #-----------------------------------------------------------
        if not is_valid or not is_valid_cp:  # errors             
            errors_dict.update(errors_concept)
           # y= {**errors_dict, **errors_concept}
            return Response( #data = json.dumps(errors_dict)
                            data = errors_dict
                            , content_type="json"
                            , status=status.HTTP_406_NOT_ACCEPTABLE
                            )
  
        #-----------------------------------------------------------
        else:
            # update ...
            #-- Tags -------------------------------------------    
            # get tags
            tag_ids = tags  
            new_tag_list = []
            if tag_ids:
                # split tag ids into list
                new_tag_list = [int(i) for i in tag_ids]
            # save the tag ids
            old_tag_list = list(ConceptTagMap.objects.filter(concept=update_concept).values_list('tag', flat=True))
            # detect tags to add
            tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))
            # detect tags to remove
            tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))
            # add tags that have not been stored in db
            for tag_id_to_add in tag_ids_to_add:
                ConceptTagMap.objects.get_or_create(concept=update_concept, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)
            # remove tags no longer required in db
            for tag_id_to_remove in tag_ids_to_remove:
                tag_to_remove = ConceptTagMap.objects.filter(concept=update_concept, tag=Tag.objects.get(id=tag_id_to_remove))
                tag_to_remove.delete()
            #-----------------------------------------------------
         
                  
            # DELETE ALL EXISTING COMPONENTS FIRST SINCE THERE IS NA MAPPINGa
            # get all the components attached to the concept
            old_components = update_concept.component_set.all()        
            for old_comp in old_components:
                old_comp.delete()
                
            # insert as new
            #-- Components/codelists/codes --------
            for comp in components:
                component = Component.objects.create(
                                    comment=comp['comment'],
                                    component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT, # fixed since it is the only allowed type (not comp['component_type'])
                                    concept=update_concept,
                                    created_by=request.user,
                                    logical_type=comp['logical_type'],
                                    name=comp['name']
                                    )
                
                code_list = CodeList.objects.create(component=component, description='-')
                codeRegex = CodeRegex.objects.create(
                                    component=component,
                                    code_list=code_list,
                                    regex_type=CodeRegex.SIMPLE,
                                    regex_code='',
                                    column_search=CodeRegex.CODE,
                                    sql_rules=''
                                    )
                row_count = 0
                # create codes
                for row in comp['codes']:
                    row_count += 1
                    # Need to check stripped codes
                    if row['code'].strip() == '':      continue
                    obj, created = Code.objects.get_or_create(
                                    code_list=code_list,
                                    code=row['code'],
                                    defaults={
                                            'description': row['description']
                                        }
                                    )
            #--------------------------------------
            #--------------------------------------
              
            update_concept.changeReason = "Updates from API"
            update_concept.save()   

            # Get all the 'parent' concepts i.e. those that include this one,
            # and add a history entry to those that this concept has been updated.
            saveDependentConceptsChangeReason(update_concept.pk , "Component concept #" + str(update_concept.pk) + " was updated")
        

            data = {'message': 'Concept updated successfully',
                    'id': update_concept.pk
                    }
            return Response(data = data
                            , content_type="text/json-comment-filtered"
                            , status=status.HTTP_201_CREATED
                            )
        
        


#---------------------------------------------------------------------------
def isValidConcept(request, concept):       
    '''
        Check that the concept data is valid.
        
        MUST have the first parameter as a request for the @login_required decorator.
    '''

    is_valid = True
    errors = {}
    
    if concept.name.isspace() or len(concept.name) < 3 or concept.name is None:
        errors['name'] = "concept name should be at least 3 characters"
        is_valid = False
         
    if concept.author.isspace() or len(concept.author) < 3 or concept.author is None:
        errors['author'] = "Author should be at least 3 characters"
        is_valid = False

    if concept.description.isspace() or len(concept.description) < 10 or concept.description is None:
        errors['description'] = "concept description should be at least 10 characters"
        is_valid = False
      
    if not concept.publication_link.isspace()  and len(concept.publication_link) > 0 and not concept.publication_link is None:
        # if publication_link is given, it must be a valid URL
        validate = URLValidator()

        try:
            validate(concept.publication_link)
            #print("String is a valid URL")
        except Exception as exc:
            #print("String is not valid URL")
            errors['publication_link'] = "concept publication_link is not valid URL"
            is_valid = False
                
    return is_valid, errors

#---------------------------------------------------------------------------
def chk_coding_system(coding_system_input):
    is_valid_data = True
    err = ""
    ret_value = coding_system_input
    
    coding_system = coding_system_input  # request.data.get('coding_system') #*
    if coding_system is None:
        is_valid_data = False
        err = 'coding_system must be a valid coding system id'
    else:
        if isInt(coding_system):
            coding_system = int(coding_system_input)
            if coding_system not in list(CodingSystem.objects.all().values_list('id' , flat=True)):
                is_valid_data = False
                err = 'coding_system must be a valid coding system id'

        else:
            is_valid_data = False
            err = 'coding_system must be a valid coding system id'

    if is_valid_data:
        return is_valid_data, err, CodingSystem.objects.get(pk=ret_value)
    else:
        return is_valid_data, err, ret_value

#---------------------------------------------------------------------------
def chk_group(group_input , user_groups):            
    #  group id 
    is_valid_data = True
    err = ""
    ret_value = group_input
        
    group_id = group_input
    if group_id is None or group_id == "0":
        ret_value = None
    else:
        if isInt(group_id):
            group_id = int(group_input)
            if group_id not in list(user_groups.all().values_list('id' , flat=True)):
                is_valid_data = False
                err = 'API user is not a member of group with id (%s) or group does not exist.' % str(group_id)
            else:
                ret_value = group_id
        else:
            is_valid_data = False
            err = 'group_id must be valid accessible group id (integer) or null'

    return is_valid_data, err, ret_value

#---------------------------------------------------------------------------   
def chk_group_access(group_access_input):
    # group-Access
    is_valid_data = True
    err = ""
    ret_value = group_access_input
        
    group_access = group_access_input
    if isInt(group_access):
        group_access = int(group_access_input)
        if group_access not in [1, 2, 3]:
            is_valid_data = False
            err = 'invalid group access (allowed values = [1=No Access, 2=View, 3=Edit])'
        else:
            ret_value = group_access
    else:
        is_valid_data = False
        err = 'group access must be an integer (allowed values = [1=No Access, 2=View, 3=Edit])'
            
    return is_valid_data, err, ret_value

#---------------------------------------------------------------------------
def chk_world_access(world_access_input):
    # world_access
    is_valid_data = True
    err = ""
    ret_value = world_access_input
          
    world_access = world_access_input
    if world_access is None:
        ret_value = 1
    else:
        if isInt(world_access):
            world_access = int(world_access_input)
            if world_access not in [1, 2]:
                is_valid_data = False
                err = 'invalid world access (allowed values = [1=No Access, 2=View])'
            else:
                ret_value = world_access
        else:
            is_valid_data = False
            err = 'world access must be an integer (allowed values = [1=No Access, 2=View])'
              
    return is_valid_data, err, ret_value

#---------------------------------------------------------------------------
def chk_tags(tags_input):
    # handling tags
    is_valid_data = True
    err = ""
    ret_value = tags_input
               
    tags = tags_input
    if tags is not None: 
        if isinstance(tags, list): # check tags is a list
            if not (set(tags).issubset(set(Tag.objects.all().values_list('id' , flat=True)))):
                is_valid_data = False
                err = 'invalid tag ids list, all tags ids must be valid'
            else:
                ret_value = tags
        else:
            is_valid_data = False
            err = 'tags must be valid list with valid tag ids'


    return is_valid_data, err, ret_value

#---------------------------------------------------------------------------
def chk_components_and_codes(components_inputs):
    # handling components
    is_valid_data = True
    err = ""
    ret_value = components_inputs

    components = components_inputs
    if components is not None: 
        if isinstance(components, list): # check components is a list
            #--------------------------------------
            #-- Components/codes ------------------
            for comp in components:
                if str(comp['name']).strip() == '':
                    is_valid_data = False
                    err += ' / component name must not be empty'    
                
                if isInt(comp['logical_type']):
                    logical_type = int(comp['logical_type'])
                    if logical_type not in [1, 2]:
                        is_valid_data = False
                        err += ' / invalid component logical_type (allowed values = [1=Add Codes, 2=Remove Codes])'
                else:
                    is_valid_data = False
                    err += ' / component logical_type must be an integer (allowed values = [1=Add Codes, 2=Remove Codes])'
                 
                if isInt(comp['component_type']):
                    component_type = int(comp['component_type'])
                    if component_type not in [4]:
                        is_valid_data = False
                        err += ' / invalid component component_type (allowed values = [4=Expression_Select])'
                else:
                    is_valid_data = False
                    err += ' / component component_type must be an integer (allowed values = [4=Expression_Select])'
                 
                
                #row_count = 0
                for row in comp['codes']:
                    #row_count += 1
                    # Need to check stripped codes
                    if row['code'].strip() == '':      
                        is_valid_data = False
                        err += ' / Empty code not allowed'  
                        continue
                    
            #--------------------------------------
        else:
            is_valid_data = False
            err = 'components must be valid list of dictionaries'                              
    else:
        is_valid_data = False
        err = 'components with codes must be provided'    
       
                
    return is_valid_data, err, ret_value

#---------------------------------------------------------------------------

############################################################################
# published concepts
############################################################################

@api_view(['GET'])
def get_all_published_concepts(request):
    '''
        Return all published concepts.
    '''
    if request.method == 'GET':
        rows_to_return = []
        titles = ['id', 'version', 'name', 'description', 'author', 'validation_performed', 'validation_description',
                    'publication_doi', 'publication_link', 'paper_published', 'source_reference', 'citation_requirements',
                    'coding_system_id', 'publication_date', 'publisher_id']
        
        #current_concept = Concept.objects.get(pk=pk)

        # Use a SQL function to extract this data.
        rows = getPublishedConcepts()
        for row in rows:
            rows_to_return.append(ordr(zip(titles,  
                                [
                                    row['id'],  
                                    row['history_id'],
                                    row['name'].encode('ascii', 'ignore').decode('ascii'),
                                    row['description'].encode('ascii', 'ignore').decode('ascii'),
                                    row['author'].encode('ascii', 'ignore').decode('ascii'),
                                    row['validation_performed'],
                                    row['validation_description'].encode('ascii', 'ignore').decode('ascii'),
                                    row['publication_doi'].encode('ascii', 'ignore').decode('ascii'),
                                    row['publication_link'].encode('ascii', 'ignore').decode('ascii'),
                                    row['paper_published'],
                                    row['source_reference'].encode('ascii', 'ignore').decode('ascii'),
                                    row['citation_requirements'].encode('ascii', 'ignore').decode('ascii'),
                                    row['coding_system_id'],
                                    row['publication_date'],
                                    row['publisher_id'],
                                ]
                                )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)


@api_view(['GET'])
def published_concept(request, version_id):
    '''
        Return published concept using version id.
    '''
    if request.method == 'GET':
        # check if the concept version is published
        concept = PublishedConcept.objects.filter(concept_history_id=version_id)
        if concept.count() == 0: raise Http404

        titles = ['id', 'version', 'name', 'description', 'author', 'validation_performed', 'validation_description',
                    'publication_doi', 'publication_link', 'paper_published', 'source_reference', 'citation_requirements',
                    'coding_system_id', 'publication_date', 'publisher_id']

        # Use a SQL function to extract this data.
        concept = getPublishedConceptByVersionId(version_id)
        concept_to_return = (ordr(zip(titles,  
                                [
                                    concept['id'],  
                                    concept['history_id'],
                                    concept['name'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['description'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['author'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['validation_performed'],
                                    concept['validation_description'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['publication_doi'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['publication_link'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['paper_published'],
                                    concept['source_reference'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['citation_requirements'].encode('ascii', 'ignore').decode('ascii'),
                                    concept['coding_system_id'],
                                    concept['publication_date'],
                                    concept['publisher_id'],
                                ]
                                )))
    
        return Response(concept_to_return, status=status.HTTP_200_OK)


#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def published_concept_codes(request, version_id):
    '''
        Return all published codes for specific published concept.
    '''
    if request.method == 'GET':
        # check if the concept version is published
        concept = PublishedConcept.objects.filter(concept_history_id=version_id)
        if concept.count() == 0: raise Http404

        historical_concept = getHistoryConcept(version_id)
        pk = historical_concept['id']
        
        codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id=pk, concept_history_id=version_id)
        

        rows_to_return = []
        titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']

        for row in codes:
            rows_to_return.append(ordr(zip(titles,  
                                [
                                    row['code'],  
                                    row['description'].encode('ascii', 'ignore').decode('ascii'),
                                    pk,
                                    version_id,
                                    historical_concept['name'],
                                ]
                                )))
    
        return Response(rows_to_return, status=status.HTTP_200_OK)




                