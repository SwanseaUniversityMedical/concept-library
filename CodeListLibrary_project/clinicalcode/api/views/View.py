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
from ...models.Component import Component
from ...models.CodeRegex import CodeRegex
from ...models.CodeList import CodeList
from ...models.Code import Code
from ...models.Tag import Tag
from ...models.ConceptTagMap import ConceptTagMap
from ...models.WorkingSet import WorkingSet
from ...models.WorkingSetTagMap import WorkingSetTagMap
from ...models.CodingSystem import CodingSystem
from ...models.Brand import Brand
from django.contrib.auth.models import User

#from ...models.PublishedConcept import PublishedConcept

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
from django.db.models.aggregates import Max

'''
    ---------------------------------------------------------------------------
    View sets (see http://www.django-rest-framework.org/api-guide/viewsets).
    ---------------------------------------------------------------------------
'''

#--------------------------------------------------------------------------
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of tags (no permissions involved).
    '''

    #disable authentication for this class
    authentication_classes = []
    permission_classes = []


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

    
    #api_absolute_ip = str(request.build_absolute_uri(reverse('api:api_export_concept_codes', kwargs={'pk': 0}))).split('/')[2]

    urls_available = {
        'export_concept_codes': reverse('api:api_export_concept_codes', kwargs={'pk': 0}),
        'export_concept_codes_byVersionID': reverse('api:api_export_concept_codes_byVersionID', kwargs={'pk': 0, 'concept_history_id': 1}),
        'myConcepts': reverse('api:myConcepts', kwargs={}),
        'myConceptdetail':  reverse('api:myConceptdetail', kwargs={'pk': 0}),
        'myConceptdetail_version': reverse('api:myConceptdetail_version', kwargs={'pk': 0, 'concept_history_id': 1}),
     
        'export_workingset_codes': reverse('api:api_export_workingset_codes', kwargs={'pk': 0}),
        'export_workingset_codes_byVersionID': reverse('api:api_export_workingset_codes_byVersionID', kwargs={'pk': 0, 'workingset_history_id': 1}),
        'myWorkingSets': reverse('api:myWorkingSets', kwargs={}),
        'myWorkingsetdetail': reverse('api:myWorkingsetdetail', kwargs={'pk': 0}),
        'myWorkingsetdetail_version': reverse('api:myWorkingsetdetail_version', kwargs={'pk': 0, 'workingset_history_id': 1})
         
    }
    

    return render(request,
                   'rest_framework/API-root-pg.html',
                   urls_available
                   )

    
    
#############################################################################
#############################################################################
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

def get_versions_list(user, set_class, pk):
    
    versions = set_class.objects.get(pk=pk).history.all().order_by('-history_id')
   
    max_version_id = versions.aggregate(Max('history_id'))['history_id__max']
    
    rows_to_return = []
    titles = ['version_id', 'version_name', 'version_date', 'is_latest']
    
    for v in versions:
        ret = [
                v.history_id,  
                v.name.encode('ascii', 'ignore').decode('ascii'),
                v.history_date,
                [False, True][v.history_id == max_version_id]
            ]
        rows_to_return.append(ordr(zip(titles,  ret )))
    
    return rows_to_return


def get_visible_concept_versions_list(request, pk):
    set_class = Concept
    
    versions = set_class.objects.get(pk=pk).history.all().order_by('-history_id')
   
    visible_concept_versions = []

    for v in versions:
        ver = getHistoryConcept(v.history_id)
        is_this_version_published = False
        is_this_version_published = PublishedConcept.objects.filter(concept_id=ver['id'], concept_history_id=ver['history_id']).exists()
        
        ver['is_published'] = is_this_version_published
        
        if request.user.is_authenticated(): 
            if allowed_to_edit(request.user, set_class, pk) or allowed_to_view(request.user, set_class, pk):
                visible_concept_versions.append(ver)
            else:
                if is_this_version_published:
                    visible_concept_versions.append(ver)
        else:
            if is_this_version_published:
                visible_concept_versions.append(ver)
                
    max_version_id = versions.aggregate(Max('history_id'))['history_id__max']
    
    rows_to_return = []
    titles = ['version_id', 'version_name', 'version_date', 'is_published', 'is_latest']
    
    for v in visible_concept_versions:
        ret = [
                v['history_id'],  
                v['name'].encode('ascii', 'ignore').decode('ascii'),
                v['history_date'],
                v['is_published'],
                [False, True][v['history_id'] == max_version_id]
            ]
        rows_to_return.append(ordr(zip(titles,  ret )))
    
    return rows_to_return

