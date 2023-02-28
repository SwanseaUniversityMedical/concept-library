'''
    ---------------------------------------------------------------------------
    PHENOTYPE VIEW
    ---------------------------------------------------------------------------
'''
import csv
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
# from django.contrib.messages import constants
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import EmptyPage, Paginator
# from django.db.models import Q
from django.db import transaction  # , models, IntegrityError
# from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.templatetags.static import static
# from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .. import generic_entity_db_utils, utils
from ..models import *
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.constants import *
from django.db.models.functions import Lower

from django.utils.timezone import make_aware

# from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def generic_entity_list(request):
    '''
        Display the list of phenotypes. This view can be searched and contains paging.
    '''

    search_tag_list = []
    tags = []
    selected_phenotype_types_list = []
    # get page index variables from query or from session
    expand_published_versions = 0  # disable this option

    method = request.GET.get('filtermethod', '')
    
    page_size = utils.get_int_value(request.GET.get('page_size', request.session.get('phenotype_page_size', 20)), request.session.get('phenotype_page_size', 20))
    page_size = page_size if page_size in generic_entity_db_utils.page_size_limits else 20
    page = utils.get_int_value(request.GET.get('page', request.session.get('phenotype_page', 1)), request.session.get('phenotype_page', 1))
    search = request.GET.get('search', request.session.get('generic_entity_search', ''))
    tag_ids = request.GET.get('tag_ids', request.session.get('phenotype_tag_ids', ''))
    collection_ids = request.GET.get('collection_ids', request.session.get('phenotype_collection_ids', ''))
    owner = request.GET.get('owner', request.session.get('phenotype_owner', ''))
    author = request.GET.get('author', request.session.get('phenotype_author', ''))
    coding_ids = request.GET.get('codingids', request.session.get('phenotype_codingids', ''))
    des_order = request.GET.get('order_by', request.session.get('phenotype_order_by', ''))
    selected_phenotype_types = request.GET.get('selected_phenotype_types', request.session.get('selected_phenotype_types', ''))
    phenotype_brand = request.GET.get('phenotype_brand', request.session.get('phenotype_brand', ''))  # request.CURRENT_BRAND
    data_sources = request.GET.get('data_source_ids', request.session.get('phenotype_data_source_ids', ''))
    
    show_deleted_phenotypes = request.GET.get('show_deleted_phenotypes', request.session.get('phenotype_show_deleted_phenotypes', 0))
    show_my_phenotypes = request.GET.get('show_my_phenotypes', request.session.get('phenotype_show_my_phenotype', 0))
    show_only_validated_phenotypes = request.GET.get('show_only_validated_phenotypes', request.session.get('show_only_validated_phenotypes', 0))
    phenotype_must_have_published_versions = request.GET.get('phenotype_must_have_published_versions', request.session.get('phenotype_must_have_published_versions', 0))

    show_my_pending_phenotypes = request.GET.get('show_my_pending_phenotypes', request.session.get('phenotype_show_my_pending_phenotypes', 0))
    show_mod_pending_phenotypes = request.GET.get('show_mod_pending_phenotypes', request.session.get('phenotype_show_mod_pending_phenotypes', 0))
    show_rejected_phenotypes = request.GET.get('show_rejected_phenotypes', request.session.get('phenotype_show_rejected_phenotypes', 0))
   
    search_form = request.GET.get('search_form', request.session.get('generic_entity_search_form', 'basic-form'))

    start_date_range = request.GET.get('startdate', request.session.get('phenotype_date_start', ''))
    end_date_range = request.GET.get('enddate', request.session.get('phenotype_date_end', ''))
    
    start_date_query, end_date_query = False, False
    try:
        start_date_query = make_aware(datetime.datetime.strptime(start_date_range, '%Y-%m-%d'))
        end_date_query = make_aware(datetime.datetime.strptime(end_date_range, '%Y-%m-%d'))
    except ValueError:
        start_date_query = False
        end_date_query = False
        
    # store page index variables to session
    request.session['phenotype_page_size'] = page_size
    request.session['phenotype_page'] = page
    request.session['generic_entity_search'] = search
    request.session['phenotype_tag_ids'] = tag_ids
    request.session['phenotype_collection_ids'] = collection_ids
    request.session['phenotype_brand'] = phenotype_brand   
    request.session['selected_phenotype_types'] = selected_phenotype_types
    request.session['phenotype_codingids'] = coding_ids
    request.session['phenotype_date_start'] = start_date_range
    request.session['phenotype_date_end'] = end_date_range
    request.session['phenotype_owner'] = owner   
    request.session['phenotype_author'] = author
    request.session['phenotype_order_by'] = des_order  
    request.session['phenotype_show_my_phenotype'] = show_my_phenotypes
    request.session['phenotype_show_deleted_phenotypes'] = show_deleted_phenotypes
    request.session['show_only_validated_phenotypes'] = show_only_validated_phenotypes
    request.session['phenotype_must_have_published_versions'] = phenotype_must_have_published_versions 
    request.session['generic_entity_search_form'] = search_form
    request.session['phenotype_show_my_pending_phenotypes'] = show_my_pending_phenotypes    
    request.session['phenotype_show_mod_pending_phenotypes'] = show_mod_pending_phenotypes
    request.session['phenotype_show_rejected_phenotypes'] = show_rejected_phenotypes
    request.session['phenotype_data_source_ids'] = data_sources

    # remove leading, trailing and multiple spaces from text search params
    search = re.sub(' +', ' ', search.strip())
    owner = re.sub(' +', ' ', owner.strip())
    author = re.sub(' +', ' ', author.strip())
    
        
    filter_cond = " 1=1 "
    approved_status = []
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published

    # available phenotype_types in the DB
    phenotype_types_list, phenotypes_types_order = generic_entity_db_utils.get_brand_associated_phenotype_types(request, brand=None) #GenericEntity.history.annotate(type_lower=Lower('type')).values('type_lower').distinct().order_by('type_lower')
    
    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'PH' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^PH\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_id = generic_entity_db_utils.chk_valid_id(request, set_class=GenericEntity, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id ='" + str(ret_id) + "') "
    
    collections, filter_cond = generic_entity_db_utils.apply_filter_condition(query='collections', selected=collection_ids, conditions=filter_cond)
    tags, filter_cond = generic_entity_db_utils.apply_filter_condition(query='tags', selected=tag_ids, conditions=filter_cond)
    
    coding, filter_cond = generic_entity_db_utils.apply_filter_condition(query='coding_systems', selected=coding_ids, conditions=filter_cond)
    sources, filter_cond = generic_entity_db_utils.apply_filter_condition(query='data_sources', selected=data_sources, conditions=filter_cond)
    selected_phenotype_types_list, filter_cond = generic_entity_db_utils.apply_filter_condition(query='phenotype_type', selected=selected_phenotype_types, conditions=filter_cond, data=phenotype_types_list)
    
    is_authenticated_user = request.user.is_authenticated
    daterange, date_range_cond = generic_entity_db_utils.apply_filter_condition(query='daterange', 
                                                             selected={'start': [start_date_query, start_date_range], 'end': [end_date_query, end_date_range]}, 
                                                             conditions='',
                                                             is_authenticated_user=is_authenticated_user)
    
    # check if it is the public site or not
    if request.user.is_authenticated:
        # ensure that user is only allowed to view/edit the relevant phenotype

        get_live_and_or_published_ver = 3
        if phenotype_must_have_published_versions == "1":
            get_live_and_or_published_ver = 2

        # show only phenotype owned by the current user
        if show_my_phenotypes == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)


        # publish approval
        if is_member(request.user, "Moderators"):
            if show_mod_pending_phenotypes == "1":
                approved_status += [1]
            if show_rejected_phenotypes == "1":
                approved_status += [3]                
        else:
            if show_my_pending_phenotypes == "1" or show_rejected_phenotypes == "1":
                filter_cond += " AND owner_id=" + str(request.user.id) 
            if show_my_pending_phenotypes == "1":
                approved_status = [1]
            if show_rejected_phenotypes == "1":
                approved_status += [3]  

        # if show deleted phenotype is 1 then show deleted phenotype
        if show_deleted_phenotypes != "1":
            exclude_deleted = True
        else:
            exclude_deleted = False

    else:
        # show published phenotype
        get_live_and_or_published_ver = 2

    show_top_version_only = True
    if expand_published_versions == "1":
        show_top_version_only = False

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                filter_cond += " AND owner_id=" + str(owner_id)
            else:
                # username not found
                filter_cond += " AND owner_id= -1 "

    # if show_only_validated_phenotypes is 1 then show only phenotype with validation_performed=True
    if show_only_validated_phenotypes == "1":
        filter_cond += " AND COALESCE(validation_performed, FALSE) IS TRUE "

    # show phenotype for a specific brand
    if phenotype_brand != "":
        current_brand = Brand.objects.all().filter(name=phenotype_brand)
        group_list = list(current_brand.values_list('groups', flat=True))
        filter_cond += " AND group_id IN(" + ', '.join(map(str, group_list)) + ") "

    order_param = db_utils.get_order_from_parameter(des_order).replace(" id,", " REPLACE(id, 'PH', '')::INTEGER,")

# TO be changed to generic entity search 
#    phenotype_srch = generic_entity_db_utils.get_visible_live_or_published_generic_entity_versions(request,
    phenotype_srch = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                                            search=[search, ''][search_by_id],
                                                                            author=author,
                                                                            exclude_deleted=exclude_deleted,
                                                                            filter_cond=filter_cond,
                                                                            approved_status=approved_status,
                                                                            show_top_version_only=show_top_version_only,
                                                                            search_name_only = False,
                                                                            highlight_result = True,
                                                                            order_by = order_param,
                                                                            date_range_cond = date_range_cond
                                                                            )
    # create pagination
    paginator = Paginator(phenotype_srch,
                          page_size,
                          allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    p_btns = utils.get_paginator_pages(paginator, p)

    tag_ids2 = tag_ids
    tag_ids_list = []
    if tag_ids:
        tag_ids_list = utils.expect_integer_list(tag_ids)

    collections_excluded_from_filters = []
    if request.CURRENT_BRAND != "":
        collections_excluded_from_filters = request.BRAND_OBJECT.collections_excluded_from_filters

    # Collections
    brand_associated_collections, collections_order = generic_entity_db_utils.get_brand_associated_collections(request, 
                                                                            concept_or_phenotype='phenotype',
                                                                            brand=None,
                                                                            excluded_collections=collections_excluded_from_filters
                                                                            )
    
    brand_associated_collections_ids = [x.id for x in brand_associated_collections]

    # Tags
    brand_associated_tags, tags_order = generic_entity_db_utils.get_brand_associated_tags(request, 
                                                                excluded_tags=collections_excluded_from_filters,
                                                                concept_or_phenotype='phenotype'
                                                                )

    # Coding id 
    coding_system_reference, coding_order = generic_entity_db_utils.get_coding_system_reference(request, brand=None, concept_or_phenotype="phenotype")
    coding_system_reference_ids = [x.id for x in coding_system_reference]
    coding_id_list = []
    if coding_ids:
        coding_id_list = utils.expect_integer_list(coding_ids)
    
    # Data sources
    data_source_reference, datasource_order = generic_entity_db_utils.get_data_source_reference(request, brand=None)
    data_sources_list = []
    if data_sources:
        data_sources_list = utils.expect_integer_list(data_sources)

    # Collections
    collection_ids_list = []
    if collection_ids:
        collection_ids_list = utils.expect_integer_list(collection_ids)

    # Sorted order of each field
    filter_statistics_ordering = {
        'tags': tags_order,
        'collection': collections_order,
        'coding': coding_order,
        'types': phenotypes_types_order,
        'datasources': datasource_order,
    }

    context = {
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'show_my_phenotypes': show_my_phenotypes,
        'show_deleted_phenotypes': show_deleted_phenotypes,
        'show_my_pending_phenotypes': show_my_pending_phenotypes,
        'show_mod_pending_phenotypes': show_mod_pending_phenotypes,
        'show_rejected_phenotypes': show_rejected_phenotypes,
        'tags': tags,
        'tag_ids': tag_ids2,
        'tag_ids_list': tag_ids_list,
        'collections': collections,
        'collection_ids': collection_ids,
        'collection_ids_list': collection_ids_list,
        'owner': owner,
        'show_only_validated_phenotypes': show_only_validated_phenotypes,
        'allowed_to_create': not settings.CLL_READ_ONLY,
        'phenotype_brand': phenotype_brand,
        'phenotype_must_have_published_versions': phenotype_must_have_published_versions,
        'allTags': Tag.objects.all().order_by('description'),
        'all_CodingSystems': CodingSystem.objects.all().order_by('id'),
        'search_form': search_form,
        'p_btns': p_btns,
        'brand_associated_collections': brand_associated_collections,
        'brand_associated_collections_ids': brand_associated_collections_ids,
        'all_collections_selected': all(item in tag_ids_list for item in brand_associated_collections_ids),
        'phenotype_types': phenotype_types_list,
        'selected_phenotype_types': [t for t in selected_phenotype_types.split(',') ],
        'selected_phenotype_types_str': selected_phenotype_types, # ','.join([t for t in selected_phenotype_types.split(',') ]),
        'all_types_selected': all(item in selected_phenotype_types_list for item in phenotype_types_list),
        'coding_system_reference': coding_system_reference,
        'coding_system_reference_ids': coding_system_reference_ids,
        'data_source_ids': data_sources,
        'data_source_list': data_sources_list,
        'data_sources_reference': data_source_reference,
        'brand_associated_tags': brand_associated_tags,
        'brand_associated_tags_ids': list(brand_associated_tags.values()),
        'all_tags_selected': all(item in tag_ids_list for item in brand_associated_tags.values()),
        'coding_id_list': coding_id_list,
        'coding_ids': coding_ids,
        'all_coding_selected': all(item in coding_id_list for item in coding_system_reference_ids),
        'ordered_by': des_order,
        'filter_start_date': start_date_range,
        'filter_end_date': end_date_range,
        'filter_statistics_ordering': filter_statistics_ordering,
    }

    if method == 'basic-form':
        return render(request, 'clinicalcode/phenotype/phenotype_results.html', context)
    else:
        return render(request, 'clinicalcode/phenotype/index.html', context)


def generic_entity_list_temp(request):
    '''
        Display the list of phenotypes. 
    '''
    
    page = utils.get_int_value(request.GET.get('page', request.session.get('entity_page', 1)), request.session.get('phenotype_page', 1))
    page_size = 20    
 
    request.session['entity_page'] = page
    
    srch = generic_entity_db_utils.get_visible_live_or_published_generic_entity_versions(request,
                                                                            get_live_and_or_published_ver=3,
                                                                            search='',
                                                                            author='',
                                                                            exclude_deleted=True,
                                                                            filter_cond=" 1=1 ",
                                                                            search_name_only = False,
                                                                            highlight_result = True
                                                                            )
    # create pagination
    paginator = Paginator(srch,
                          page_size,
                          allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    p_btns = utils.get_paginator_pages(paginator, p)


    context = {
        'page': page,
        'page_size': str(20),
        'page_obj': p,
        'search_form': 'basic-form',
        'p_btns': p_btns,
        }
    
    return render(request, 'clinicalcode/generic_entity/search_temp.html', context)



def generic_entity_detail(request, pk, history_id=None):
    ''' 
        Display the detail of a generic entity at a point in time.
    '''
    # validate access for login and public site
    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)

    is_published = checkIfPublished(GenericEntity, pk, history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, history_id)

    # ----------------------------------------------------------------------

    generic_entity = generic_entity_db_utils.get_historical_entity(history_id
                                            , highlight_result = [False, True][generic_entity_db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = generic_entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))  
                                            )
    # The historical entity contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the generic_entity.
    if generic_entity['owner_id'] is not None:
        generic_entity['owner'] = User.objects.get(id=int(generic_entity['owner_id']))
        
    generic_entity['group'] = None
    if generic_entity['group_id'] is not None:
        generic_entity['group'] = Group.objects.get(id=int(generic_entity['group_id']))

    history_date = generic_entity['history_date']



################################################
    entity_layout = generic_entity_db_utils.get_entity_layout(generic_entity)
    entity_layout_category = generic_entity_db_utils.get_entity_layout_category(generic_entity)
        
    side_menu = get_side_menu(request, generic_entity['data'])




################################################



    # ----------------------------------------------------------------------
    concept_id_list = []
    concept_hisoryid_list = []
    concepts = Concept.history.filter(pk=-1).values('id', 'history_id', 'name', 'group')

    if generic_entity['data']['concept_informations']:
        #concept_informations = json.loads(generic_entity['data']['concept_informations'])
        concept_informations = generic_entity['data']['concept_informations']['value']
        concept_id_list = [x['concept_id'] for x in concept_informations]
        concept_hisoryid_list = [x['concept_version_id'] for x in concept_informations]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list).values('id', 'history_id', 'name', 'group')

    concepts_id_name = json.dumps(list(concepts))


    is_latest_version = (int(history_id) == GenericEntity.objects.get(pk=pk).history.latest().history_id)
    is_latest_pending_version = False

    if len(PublishedGenericEntity.objects.filter(entity_id=pk, entity_history_id=history_id, approval_status=1)) > 0:
        is_latest_pending_version = True
   # print(is_latest_pending_version)


    children_permitted_and_not_deleted = True
    error_dic = {}
    are_concepts_latest_version = True
    version_alerts = {}

    if request.user.is_authenticated:
        can_edit = (not GenericEntity.objects.get(pk=pk).is_deleted) and allowed_to_edit(request, GenericEntity, pk)

        user_can_export = True 
         # (allowed_to_view_children(request, GenericEntity, pk, set_history_id=history_id)
         #                   and generic_entity_db_utils.chk_deleted_children(request,
         #                                                   GenericEntity,
         #                                                   pk,
         #                                                   returnErrors=False,
         #                                                   set_history_id=history_id)
         #                   and not GenericEntity.objects.get(pk=pk).is_deleted)
        user_allowed_to_create = allowed_to_create()

        #children_permitted_and_not_deleted, error_dic = generic_entity_db_utils.chk_children_permission_and_deletion(request, GenericEntity, pk)

        if is_latest_version:
            are_concepts_latest_version, version_alerts = check_concept_version_is_the_latest(pk)

    else:
        can_edit = False
        user_can_export = is_published
        user_allowed_to_create = False

    publish_date = None
    if is_published:
        publish_date = PublishedGenericEntity.objects.get(entity_id=pk, entity_history_id=history_id).created

    if GenericEntity.objects.get(pk=pk).is_deleted == True:
        messages.info(request, "This entity has been deleted.")

    # published versions
    published_historical_ids = list(PublishedGenericEntity.objects.filter(entity_id=pk, approval_status=2).values_list('entity_history_id', flat=True))

    # # history
    history = get_history_table_data(request, pk)


    # how to show codelist tab
    if request.user.is_authenticated:
        component_tab_active = "active"
        codelist_tab_active = ""
        codelist = []
        codelist_loaded = 0
    else:
        # published
        component_tab_active = "active"  # ""
        codelist_tab_active = ""  # "active"
        codelist = generic_entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id) ## change
        codelist_loaded = 1
        
    # codelist = generic_entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id)
    # codelist_loaded = 1        

    # rmd
    if generic_entity['data']['implementation'] is None:
        generic_entity['data']['implementation'] = ''

            
    conceptBrands = generic_entity_db_utils.getConceptBrands(request, concept_id_list)
    concept_data = []
    if concept_informations:
        for c in concept_informations:
            c['codingsystem'] = CodingSystem.objects.get(pk=Concept.history.get(id=c['concept_id'], history_id=c['concept_version_id']).coding_system_id).name
            c['code_attribute_header'] = Concept.history.get(id=c['concept_id'], history_id=c['concept_version_id']).code_attribute_header

            c['alerts'] = ''
            if not are_concepts_latest_version:
                if c['concept_version_id'] in version_alerts:
                    c['alerts'] = version_alerts[c['concept_version_id']]

            if not children_permitted_and_not_deleted:
                if c['concept_id'] in error_dic:
                    c['alerts'] += "<BR>- " + "<BR>- ".join(error_dic[c['concept_id']])

            c['alerts'] = re.sub("Child ", "", c['alerts'], flags=re.IGNORECASE)

            c['brands'] = ''
            if c['concept_id'] in conceptBrands:
                for brand in conceptBrands[c['concept_id']]:
                    c['brands'] += "<img src='" + static('img/brands/' + brand + '/logo.png') + "' height='10px' title='" + brand + "' alt='" + brand + "' /> "

            c['is_published'] = checkIfPublished(Concept, c['concept_id'], c['concept_version_id'])
            c['name'] = concepts.get(id=c['concept_id'], history_id=c['concept_version_id'])['name']

            c['codesCount'] = 0
            if codelist:
                c['codesCount'] = len([x['code'] for x in codelist if x['concept_id'] == 'C' + str(c['concept_id']) and x['concept_version_id'] == c['concept_version_id'] ])

            c['concept_friendly_id'] = 'C' + str(c['concept_id'])
            concept_data.append(c)


    context = {
        'side_menu': side_menu,  
        'entity_layout': entity_layout,
        'entity_layout_category': entity_layout_category,
        'entity': generic_entity,
        'entity_data': generic_entity['data'],
        'history': history,

          
        
        #'concept_informations': json.dumps(concept_informations),
        'component_tab_active': component_tab_active,
        'codelist_tab_active': codelist_tab_active,
        'codelist': codelist,  # json.dumps(codelist)
        'codelist_loaded': codelist_loaded,
        'concepts_id_name': concepts_id_name,
        'concept_data': concept_data,
        
        
        'page_canonical_path': get_canonical_path_by_brand(request, GenericEntity, pk, history_id),
        
        
        #'gender': gender,        
        #'clinicalTerminologies': clinicalTerminologies,
        'user_can_edit': False,  # for now  #can_edit,
        'allowed_to_create': False,  # for now  #user_allowed_to_create,    # not settings.CLL_READ_ONLY,
        'user_can_export': user_can_export,
        
        'live_ver_is_deleted': GenericEntity.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'approval_status': approval_status,
        'publish_date': publish_date,
        'is_latest_version': is_latest_version,
        'is_latest_pending_version':is_latest_pending_version,
        'current_phenotype_history_id': int(history_id),

        'q': generic_entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', '')),
        'force_highlight_result':  ['0', '1'][generic_entity_db_utils.is_referred_from_search_page(request)]                              
    }

    return render(request, 
                  'clinicalcode/generic_entity/detail.html',
                  context)


def get_side_menu(request, template_data):
    """
    return side menu tabs
    """
   
    side_menu = {}
    
    field_definitions = template_data
    for (field_name, field_definition) in field_definitions.items():
        ##field_name = field_name.replace(' ', '') 
        is_side_menu = False
        side_menu_title = ''
        
        if field_name.strip().lower() == 'name':
            continue
        
        if 'do_not_show_in_production' in field_definition and field_definition['do_not_show_in_production'] == True:
            if (not settings.IS_DEMO) and (not settings.IS_DEVELOPMENT_PC):
                continue  
                     
        if 'display_only_if_user_is_authenticated' in field_definition and field_definition['display_only_if_user_is_authenticated'] == True:
            if not request.user.is_authenticated:
                continue  
            
        if 'hide_if_empty' in field_definition and field_definition['hide_if_empty'] == True:
            if field_definition['value'].strip() == '':
                continue   
                
        # if 'is_base_field' in field_definition and field_definition['is_base_field'] == True:
        #     is_side_menu = True
        #     side_menu_title = field_name 

        if 'side_menu' in field_definition:
            is_side_menu = True
            side_menu_title = field_definition['side_menu'] 


        if is_side_menu:
            #field_name = side_menu_title.replace(' ', '')
            side_menu[field_definition['html_id']] = side_menu_title

    return side_menu
            

def get_history_table_data(request, pk):
    """"
        get history table data for the template
    """
    
    versions = GenericEntity.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = generic_entity_db_utils.get_historical_entity(v.history_id
                                        , highlight_result = [False, True][generic_entity_db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = generic_entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))
                                        , include_template_data = False  
                                        )
        
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        ver['updated_by'] = None
        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(GenericEntity, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedGenericEntity.objects.get(entity_id=ver['id'], entity_history_id=ver['history_id'], approval_status=2).created
        else:
            ver['publish_date'] = None

        ver['approval_status'] = -1
        ver['approval_status_label'] = ''
        if PublishedGenericEntity.objects.filter(entity_id=ver['id'], entity_history_id=ver['history_id']).exists():
            ver['approval_status'] = PublishedGenericEntity.objects.get(entity_id=ver['id'], entity_history_id=ver['history_id']).approval_status
            ver['approval_status_label'] = APPROVED_STATUS[ver['approval_status']][1]        
        
        
        if request.user.is_authenticated:
            if allowed_to_edit(request, GenericEntity, pk) or allowed_to_view(request, GenericEntity, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)
                
    return historical_versions
   
   
@login_required
# phenotype_conceptcodesByVersion
def phenotype_concept_codes_by_version(request,
                                    pk,
                                    phenotype_history_id,
                                    target_concept_id = None,
                                    target_concept_history_id = None):
    '''
        Get the codes of the phenotype concepts
        for a specific version
        for a specific concept
        Parameters:     request    The request.
                        pk         The phenotype id.
                        phenotype_history_id  The version id
                        target_concept_id
                        target_concept_history_id
        Returns:        data       Dict with the codes. 
    '''

    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=phenotype_history_id)

    # here, check live version
    current_ph = GenericEntity.objects.get(pk=pk)

    #     children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request,
    #                                                                                                 GenericEntity, pk,
    #                                                                                                 set_history_id=phenotype_history_id)
    #     if not children_permitted_and_not_deleted:
    #         raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    # --------------------------------------------------

    codes = generic_entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, phenotype_history_id, target_concept_id, target_concept_history_id)

    data = dict()
    data['form_is_valid'] = True


    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = generic_entity_db_utils.get_concept_ids_versions_of_historical_phenotype(pk, phenotype_history_id)

    concept_codes_html = []
    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]

        # check if the sent concept id/ver are valid
        if (target_concept_id is not None and target_concept_history_id is not None):
            if target_concept_id != str(concept_id) and target_concept_history_id != str(concept_version_id):
                continue

        c_codes = []

        c_codes = codes

        c_codes_count = "0"
        try:
            c_codes_count = str(len(c_codes))
        except:
            c_codes_count = "0"

        # c_codes_count_2 = len([c['code'] for c in codes if c['concept_id'] == concept_id and c['concept_version_id'] == concept_version_id ])

        c_code_attribute_header = Concept.history.get(id=concept_id, history_id=concept_version_id).code_attribute_header
        concept_codes_html.append({
            'concept_id': concept_id,
            'concept_version_id': concept_version_id,
            'c_codes_count': c_codes_count,
            'c_html': render_to_string(
                                        'clinicalcode/phenotype/get_concept_codes.html', {
                                            'codes': c_codes,
                                            'code_attribute_header': c_code_attribute_header,
                                            'showConcept': False,
                                            'q': ['', request.session.get('phenotype_search', '')][request.GET.get('highlight','0')=='1']
                                        })
        })

    data['concept_codes_html'] = concept_codes_html

    # data['codes'] = codes

    return JsonResponse(data)


def check_concept_version_is_the_latest(phenotypeID):
    """
    check live version of concepts in a phenotype concept_informations
    """

    phenotype = GenericEntity.objects.get(pk=phenotypeID)

    is_ok = True
    version_alerts = {}

    if not phenotype.template_data['concept_informations']:
        return is_ok, version_alerts

    concepts_id_versionID = phenotype.template_data['concept_informations']

    # loop for concept versions
    for c in concepts_id_versionID:
        c_id = c['concept_id']
        c_ver_id = c['concept_version_id']
        latest_history_id = Concept.objects.get(pk=c_id).history.latest('history_id').history_id
        if latest_history_id != c_ver_id:
            version_alerts[c_ver_id] = "newer version available"
            is_ok = False
    #         else:
    #             version_alerts[c_id] = ""
    return is_ok, version_alerts



@login_required
def Entity_Create(request):
    """
        create an antity
    """
    # TODO: implement this
    pass


class Entity_Update(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, UpdateView):
    """
        Update the current entity.
    """
    # ToDo
    pass


class PhenotypeDelete(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, TemplateResponseMixin, View):
    """
        Delete an entity.
    """
    # ToDo
    pass


def history_phenotype_codes_to_csv(request, pk, history_id=None):
    """
        Return a csv file of codes for a phenotype for a specific historical version.
    """
    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)        
        
    # validate access for login and public site
    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    is_published = checkIfPublished(GenericEntity, pk, history_id)

    # ----------------------------------------------------------------------

    # exclude(is_deleted=True)
    if GenericEntity.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # exclude(is_deleted=True)
    if GenericEntity.history.filter(id=pk, history_id=history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # here, check live version
    current_ph = GenericEntity.objects.get(pk=pk)

    if not is_published:
        children_permitted_and_not_deleted, error_dic = generic_entity_db_utils.chk_children_permission_and_deletion(request, GenericEntity, pk, set_history_id=history_id)
        if not children_permitted_and_not_deleted:
            raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    current_ph_version = GenericEntity.history.get(id=pk, history_id=history_id)

    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = generic_entity_db_utils.get_concept_ids_versions_of_historical_phenotype(pk, history_id)

    my_params = {
        'phenotype_id': pk,
        'history_id': history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="phenotype_%(phenotype_id)s_ver_%(history_id)s_concepts_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    final_titles = ([
        'code', 'description', 'coding_system', 
        'concept_id', 'concept_version_id', 'concept_name',
        'phenotype_id', 'phenotype_version_id', 'phenotype_name'
        ])
    # if the phenotype contains only one concept, write titles in the loop below
    if len(concept_ids_historyIDs) != 1:
        final_titles = final_titles + ["code_attributes"]
        writer.writerow(final_titles)
        

    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        current_concept_version = Concept.history.get(id=concept_id, history_id=concept_version_id)
        concept_coding_system = current_concept_version.coding_system.name
        concept_name = current_concept_version.name
        code_attribute_header = current_concept_version.code_attribute_header
        concept_history_date = current_concept_version.history_date
        
        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        #---------------------------------------------
        #  code attributes  ---
        codes_with_attributes = []
        if code_attribute_header:
            codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=concept_id,
                                                                                    concept_history_date=concept_history_date,
                                                                                    allCodes=codes,
                                                                                    code_attribute_header=code_attribute_header)
        
            codes = codes_with_attributes
            
        # if the phenotype contains only one concept
        if len(concept_ids_historyIDs) == 1:
            if code_attribute_header:
                final_titles = final_titles + code_attribute_header
                
            writer.writerow(final_titles)
    
        #---------------------------------------------

        
        for cc in codes:
            rows_no += 1
                         
            #---------------------------------------------   
            code_attributes = []
            # if the phenotype contains only one concept
            if len(concept_ids_historyIDs) == 1:
                if code_attribute_header:
                    for a in code_attribute_header:
                        code_attributes.append(cc[a])
            else:
                code_attributes_dict = OrderedDict([])
                if code_attribute_header:
                    for a in code_attribute_header:
                        code_attributes_dict[a] = cc[a]
                    code_attributes.append(dict(code_attributes_dict))
            #---------------------------------------------
            
            
            writer.writerow([
                cc['code'], 
                cc['description'].encode('ascii', 'ignore').decode('ascii'), 
                concept_coding_system, 
                'C' + str(concept_id), 
                concept_version_id,
                concept_name,
                current_ph_version.id, 
                current_ph_version.history_id,
                current_ph_version.name
            ] + code_attributes)

        if rows_no == 0:
            writer.writerow([
                '', 
                '', 
                concept_coding_system, 
                'C' + str(concept_id), 
                concept_version_id,
                concept_name,
                current_ph_version.id, 
                current_ph_version.history_id,
                current_ph_version.name
            ])

    return response



