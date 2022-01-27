'''
    ---------------------------------------------------------------------------
    API VIEW
    API access to the data to list the various data types (if access is
    permitted) and to access the data structure and components of groups of
    data types.
    ---------------------------------------------------------------------------
'''
import json
from collections import OrderedDict
from collections import OrderedDict as ordr
from datetime import datetime

from clinicalcode.context_processors import clinicalcode
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import PermissionDenied
# from snippets.models import Snippet
# from snippets.serializers import SnippetSerializer
from django.core.validators import URLValidator
from django.db.models import Q
from django.db.models.aggregates import Max
from django.http.response import Http404
from numpy.distutils.fcompiler import none
from rest_framework import status, viewsets
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes)
from rest_framework.response import Response

from ...db_utils import *
from ...models.Brand import Brand
from ...models.Code import Code
from ...models.CodeList import CodeList
from ...models.CodeRegex import CodeRegex
from ...models.CodingSystem import CodingSystem
from ...models.Component import Component
# The models imports have to be done as follows to avoid Eclipse flagging up
# access to the objects list as ambiguous.
from ...models.Concept import Concept
from ...models.DataSource import DataSource
from ...models.Tag import Tag
from ...models.WorkingSet import WorkingSet
from ...models.WorkingSetTagMap import WorkingSetTagMap
#from django.forms.models import model_to_dict
from ...permissions import *
from ...utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ..serializers import *

#from ...models.PublishedConcept import PublishedConcept
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
class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    '''
        Get the API output for the list of data sources (no permissions involved).
    '''

    # disable authentication for this class
    authentication_classes = []
    permission_classes = []

    queryset = DataSource.objects.none()
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        '''
            Provide the dataset for the view.
            Get all the data sources but limit if we are searching.
        '''
        queryset = DataSource.objects.all()
        keyword_search = self.request.query_params.get('search', None)
        if keyword_search is not None:
            queryset = queryset.filter(name__icontains=keyword_search)
        return queryset

    def filter_queryset(self, queryset):
        '''
            Override the default filtering.
            By default we get data sources ordered by creation date even if
            we provide sorted data from get_queryset(). We have to sort the
            data here.
        '''
        queryset = super(DataSourceViewSet, self).filter_queryset(queryset)
        return queryset.order_by('name')


#     def perform_create(self, serializer):
#         raise PermissionDenied

#     def perform_update(self, serializer):
#         raise PermissionDenied


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

    if concept.author.isspace() or len(
            concept.author) < 3 or concept.author is None:
        errors['author'] = "Author should be at least 3 characters"
        is_valid = False

#     if concept.description.isspace() or len(concept.description) < 10 or concept.description is None:
#         errors['description'] = "concept description should be at least 10 characters"
#         is_valid = False

    if not concept.publication_link.isspace() and len(
            concept.publication_link
    ) > 0 and not concept.publication_link is None:
        # if publication_link is given, it must be a valid URL
        validate = URLValidator()

        try:
            validate(concept.publication_link)
            #print("String is a valid URL")
        except Exception as exc:
            #print("String is not valid URL")
            errors[
                'publication_link'] = "concept publication_link is not valid URL"
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
            if coding_system not in list(
                    CodingSystem.objects.all().values_list('id', flat=True)):
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
def chk_group(group_input, user_groups):
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
            if group_id not in list(user_groups.all().values_list('id',
                                                                  flat=True)):
                is_valid_data = False
                err = 'API user is not a member of group with id (%s) or group does not exist.' % str(
                    group_id)
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
    if not tags_input:  #    is empty list
        ret_value = None

    tags = tags_input
    if tags is not None:
        if isinstance(tags, list):  # check tags is a list
            if not (set(tags).issubset(
                    set(Tag.objects.all().values_list('id', flat=True)))):
                is_valid_data = False
                err = 'invalid tag ids list, all tags ids must be valid'
            else:
                ret_value = tags
        else:
            is_valid_data = False
            err = 'tags must be valid list with valid tag ids'

    return is_valid_data, err, ret_value


#---------------------------------------------------------------------------
def chk_data_sources(data_sources):
    # handling data-sources
    is_valid_data = True
    err = ""
    ret_value = data_sources

    ds = data_sources
    if ds is not None:
        if isinstance(ds, list):  # check data_sources is a list
            if not (set(ds).issubset(
                    set(DataSource.objects.all().values_list('id',
                                                             flat=True)))):
                is_valid_data = False
                err = 'invalid data_source ids list, all data_sources ids must be valid'
            else:
                ret_value = ds
        else:
            is_valid_data = False
            err = 'data_sources must be valid list with valid data_sources ids'

    return is_valid_data, err, ret_value


#---------------------------------------------------------------------------
def chk_concept_ids_list(request, concept_ids_list, item_name=''):
    # checking concept ids list
    is_valid_data = True
    err = ""
    ret_value = concept_ids_list

    if concept_ids_list is None or not isinstance(concept_ids_list, list):
        is_valid_data = False
        err = item_name + ' must have a valid concept ids list'
    else:
        if len(concept_ids_list) == 0:
            # allow empty concepts list
            is_valid_data = True  # False
            #err = item_name + ' must have a valid non-empty concept ids list'
        else:
            if not chkListIsAllIntegers(concept_ids_list):
                is_valid_data = False
                err = item_name + ' must have a valid concept ids list'
            else:
                if len(set(concept_ids_list)) != len(concept_ids_list):
                    is_valid_data = False
                    err = item_name + ' must have a unique concept ids list'
                else:
                    permittedConcepts = get_list_of_visible_entity_ids(
                        get_visible_live_or_published_concept_versions(
                            request, exclude_deleted=True),
                        return_id_or_history_id="id")
                    if not (set(concept_ids_list).issubset(
                            set(permittedConcepts))):
                        is_valid_data = False
                        err = item_name + ' invalid ids list, all concept ids must be valid and accessible by user'
                    else:
                        ret_value = concept_ids_list

    return is_valid_data, err, ret_value


#---------------------------------------------------------------------------
def chk_components_and_codes(components_inputs):
    # handling components
    is_valid_data = True
    err = ""
    ret_value = components_inputs

    # accepts concepts without components
    if not components_inputs:
        return is_valid_data, err, ret_value

    components = components_inputs
    if components is not None:
        if isinstance(components, list):  # check components is a list
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
def chk_code_attribute_header(code_attribute_header):
    # checking concept code_attribute_header is a list
    is_valid_data = True
    err = ""
    ret_value = code_attribute_header

    if code_attribute_header is not None:
        if not isinstance(code_attribute_header, list):
            is_valid_data = False
            err = 'code_attribute_header mustbe a list'

    return is_valid_data, err, ret_value


#---------------------------------------------------------------------------
############################################################################


def get_versions_list(request, set_class, pk):

    versions = set_class.objects.get(
        pk=pk).history.all().order_by('-history_id')

    max_version_id = versions.aggregate(Max('history_id'))['history_id__max']

    rows_to_return = []
    titles = ['version_id', 'version_name', 'version_date', 'is_latest']

    for v in versions:
        ret = [
            v.history_id,
            v.name.encode('ascii', 'ignore').decode('ascii'), v.history_date,
            [False, True][v.history_id == max_version_id]
        ]
        rows_to_return.append(ordr(list(zip(titles, ret))))

    return rows_to_return


def get_visible_versions_list(request,
                              set_class,
                              pk,
                              is_authenticated_user=True):

    if set_class == WorkingSet:
        return get_versions_list(request, set_class, pk)

    versions = set_class.objects.get(
        pk=pk).history.all().order_by('-history_id')

    visible_versions = []

    for v in versions:
        if set_class == Concept:
            ver = getHistoryConcept(v.history_id)
        elif set_class == Phenotype:
            ver = getHistoryPhenotype(v.history_id)

        is_this_version_published = False
        is_this_version_published = checkIfPublished(set_class, ver['id'],
                                                     ver['history_id'])

        ver['is_published'] = is_this_version_published

        if is_authenticated_user:
            if allowed_to_edit(request, set_class, pk) or allowed_to_view(
                    request, set_class, pk):
                visible_versions.append(ver)
            else:
                if is_this_version_published:
                    visible_versions.append(ver)
        else:
            if is_this_version_published:
                visible_versions.append(ver)

    max_version_id = versions.aggregate(Max('history_id'))['history_id__max']

    rows_to_return = []
    titles = [
        'version_id', 'version_name', 'version_date', 'is_published',
        'is_latest'
    ]

    for v in visible_versions:
        ret = [
            v['history_id'], v['name'].encode('ascii',
                                              'ignore').decode('ascii'),
            v['history_date'], v['is_published'],
            [False, True][v['history_id'] == max_version_id]
        ]
        rows_to_return.append(ordr(list(zip(titles, ret))))

    return rows_to_return


def publish_entity(request, set_class, pk):
    """
        publish Concepts / Phenotypes directly from API
        for HDR-UK testing
        (No validation done here)
    """

    latest_version_id = set_class.objects.get(
        pk=pk).history.latest().history_id
    is_published = checkIfPublished(set_class, pk, latest_version_id)

    if is_published:
        return True

    if set_class == Concept:
        concept = Concept.objects.get(pk=pk)
        published_concept = PublishedConcept(
            concept=concept,
            concept_history_id=latest_version_id,
            created_by=request.user)
        published_concept.save()
        return True

    elif set_class == Phenotype:
        phenotype = Phenotype.objects.get(pk=pk)
        published_phenotype = PublishedPhenotype(
            phenotype=phenotype,
            phenotype_history_id=latest_version_id,
            created_by=request.user)
        published_phenotype.save()
        return True

    return False
