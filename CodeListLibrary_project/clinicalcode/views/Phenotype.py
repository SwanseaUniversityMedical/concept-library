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
from collections import OrderedDict as ordr
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

from .. import db_utils, utils
from ..models.Brand import Brand
from ..models.CodingSystem import CodingSystem
from ..models.DataSource import DataSource
from ..models.Phenotype import Phenotype
from ..models.PublishedPhenotype import PublishedPhenotype
from ..models.Tag import Tag
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.constants import *
from django.db.models.functions import Lower

from django.utils.timezone import make_aware

# from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def phenotype_list(request):
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
    page_size = page_size if page_size in db_utils.page_size_limits else 20
    page = utils.get_int_value(request.GET.get('page', request.session.get('phenotype_page', 1)), request.session.get('phenotype_page', 1))
    search = request.GET.get('search', request.session.get('phenotype_search', ''))
    tag_ids = request.GET.get('tag_collection_ids', request.session.get('phenotype_tag_collection_ids', ''))
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
   
    search_form = request.GET.get('search_form', request.session.get('phenotype_search_form', 'basic-form'))

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
    request.session['phenotype_search'] = search
    request.session['phenotype_tag_collection_ids'] = tag_ids
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
    request.session['phenotype_search_form'] = search_form
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
    phenotype_types_list, phenotypes_types_order = db_utils.get_brand_associated_phenotype_types(request, brand=None) #Phenotype.history.annotate(type_lower=Lower('type')).values('type_lower').distinct().order_by('type_lower')
    
    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'PH' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^PH\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_int_id = db_utils.chk_valid_id(request, set_class=Phenotype, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id =" + str(ret_int_id) + " ) "
            
    if tag_ids:
        sanitised_tags = utils.expect_integer_list(tag_ids)
        # split tag ids into list
        search_tag_list = [str(i) for i in sanitised_tags]
        # chk if these tags are valid, to prevent injection
        # use only those found in the DB
        tags = Tag.objects.filter(id__in=search_tag_list)
        search_tag_list = list(tags.values_list('id',  flat=True))
        search_tag_list = [str(i) for i in search_tag_list]          
        if len(search_tag_list) > 0:
            filter_cond += " AND tags && '{" + ','.join(search_tag_list) + "}' "

    if selected_phenotype_types:
        selected_phenotype_types_list = [str(t) for t in selected_phenotype_types.split(',')]
        # chk if these types are valid, to prevent injection
        # use only those found in the DB
        selected_phenotype_types_list = list(set(phenotype_types_list).intersection(set(selected_phenotype_types_list)))
        filter_cond += " AND lower(type) IN('" + "', '".join(selected_phenotype_types_list) + "') "
   
    if coding_ids:
        sanitised_codes = utils.expect_integer_list(coding_ids)
        search_coding_list = [str(i) for i in sanitised_codes]
        coding = CodingSystem.objects.filter(id__in=search_coding_list)
        search_coding_list = list(coding.values_list('id', flat=True))
        search_coding_list = [str(i) for i in search_coding_list]
        if len(search_coding_list) > 0:
            filter_cond += " AND clinical_terminologies && '{" + ','.join(search_coding_list) + "}' "

    if isinstance(start_date_query, datetime.datetime) and isinstance(end_date_query, datetime.datetime):
        filter_cond += " AND (created >= '" + start_date_range + "' AND created <= '" + end_date_range + "') "
    
    if data_sources:
        sanitised_sources = utils.expect_integer_list(data_sources)
        search_source_list = [str(i) for i in sanitised_sources]
        sources = DataSource.objects.filter(id__in=search_source_list)
        search_source_list = list(sources.values_list('id',  flat=True))
        search_source_list = [str(i) for i in search_source_list]          
        if len(search_source_list) > 0:
            filter_cond += " AND data_sources && '{" + ','.join(search_source_list) + "}' "

    
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

    order_param = db_utils.get_order_from_parameter(des_order)
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
                                                                            order_by=order_param
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
    brand_associated_collections, collections_order = db_utils.get_brand_associated_collections(request, 
                                                                            concept_or_phenotype='phenotype',
                                                                            brand=None,
                                                                            excluded_collections=collections_excluded_from_filters
                                                                            )
    
    brand_associated_collections_ids = [x.id for x in brand_associated_collections]

    # Tags
    brand_associated_tags, tags_order = db_utils.get_brand_associated_tags(request, 
                                                                excluded_tags=collections_excluded_from_filters,
                                                                concept_or_phenotype='phenotype'
                                                                )

    # Coding id 
    coding_system_reference, coding_order = db_utils.get_coding_system_reference(request, brand=None, concept_or_phenotype="phenotype")
    coding_system_reference_ids = [x.id for x in coding_system_reference]
    coding_id_list = []
    if coding_ids:
        coding_id_list = utils.expect_integer_list(coding_ids)
    
    # Data sources
    data_source_reference, datasource_order = db_utils.get_data_source_reference(request, brand=None)
    data_sources_list = []
    if data_sources:
        data_sources_list = utils.expect_integer_list(data_sources)

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


def PhenotypeDetail_combined(request, pk, phenotype_history_id=None):
    ''' 
        Display the detail of a phenotype at a point in time.
    '''
    # validate access for login and public site
    validate_access_to_view(request,
                            Phenotype,
                            pk,
                            set_history_id=phenotype_history_id)

    if phenotype_history_id is None:
        # get the latest version
        phenotype_history_id = int(Phenotype.objects.get(pk=pk).history.latest().history_id)

    is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)
    approval_status = get_publish_approval_status(Phenotype, pk, phenotype_history_id)

    # ----------------------------------------------------------------------

    phenotype = db_utils.getHistoryPhenotype(phenotype_history_id
                                            , highlight_result = [False, True][db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = db_utils.get_q_highlight(request, request.session.get('phenotype_search', ''))  
                                            )
    # The history phenotype contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the phenotype.
    if phenotype['owner_id'] is not None:
        phenotype['owner'] = User.objects.get(id=int(phenotype['owner_id']))
        
    phenotype['group'] = None
    if phenotype['group_id'] is not None:
        phenotype['group'] = Group.objects.get(id=int(phenotype['group_id']))

    phenotype_history_date = phenotype['history_date']

    tags = Tag.objects.filter(pk=-1)
    phenotype_tags = phenotype['tags']
    if phenotype_tags:
        tags = Tag.objects.filter(pk__in=phenotype_tags)

    data_sources = DataSource.objects.filter(pk=-1)
    phenotype_data_sources = phenotype['data_sources']  
    if phenotype_data_sources:
        data_sources = DataSource.objects.filter(pk__in=phenotype_data_sources)

    # ----------------------------------------------------------------------
    concept_id_list = []
    concept_hisoryid_list = []
    concepts = Concept.history.filter(pk=-1).values('id', 'history_id', 'name', 'group')

    if phenotype['concept_informations']:
        concept_id_list = [x['concept_id'] for x in json.loads(phenotype['concept_informations']) ]
        concept_hisoryid_list = [x['concept_version_id'] for x in json.loads(phenotype['concept_informations']) ]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list).values('id', 'history_id', 'name', 'group')

    concepts_id_name = json.dumps(list(concepts))

    clinicalTerminologies = CodingSystem.objects.filter(pk=-1)
    CodingSystem_ids = phenotype['clinical_terminologies']
    if CodingSystem_ids:
        clinicalTerminologies = CodingSystem.objects.filter(pk__in=list(CodingSystem_ids))

    is_latest_version = (int(phenotype_history_id) == Phenotype.objects.get(pk=pk).history.latest().history_id)
    is_latest_pending_version = False

    if len(PublishedPhenotype.objects.filter(phenotype_id=pk, phenotype_history_id=phenotype_history_id, approval_status=1)) > 0:
        is_latest_pending_version = True
   # print(is_latest_pending_version)


    children_permitted_and_not_deleted = True
    error_dic = {}
    are_concepts_latest_version = True
    version_alerts = {}

    if request.user.is_authenticated:
        can_edit = (not Phenotype.objects.get(pk=pk).is_deleted) and allowed_to_edit(request, Phenotype, pk)

        user_can_export = (allowed_to_view_children(request, Phenotype, pk, set_history_id=phenotype_history_id)
                           and db_utils.chk_deleted_children(
                                                               request,
                                                               Phenotype,
                                                               pk,
                                                               returnErrors=False,
                                                               set_history_id=phenotype_history_id)
                           and not Phenotype.objects.get(pk=pk).is_deleted)
        user_allowed_to_create = allowed_to_create()

        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request, Phenotype, pk)

        if is_latest_version:
            are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(pk)

    else:
        can_edit = False
        user_can_export = is_published
        user_allowed_to_create = False

    publish_date = None
    if is_published:
        publish_date = PublishedPhenotype.objects.get(phenotype_id=pk, phenotype_history_id=phenotype_history_id).created

    if Phenotype.objects.get(pk=pk).is_deleted == True:
        messages.info(request, "This phenotype has been deleted.")

    # published versions
    published_historical_ids = list(PublishedPhenotype.objects.filter(phenotype_id=pk, approval_status=2).values_list('phenotype_history_id', flat=True))

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
        codelist = db_utils.get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id)
        codelist_loaded = 1
        
    # codelist = db_utils.get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id)
    # codelist_loaded = 1        

    # rmd
    if phenotype['implementation'] is None:
        phenotype['implementation'] = ''
    if phenotype['secondary_publication_links'] is None:
        phenotype['secondary_publication_links'] = ''

    conceptBrands = db_utils.getConceptBrands(request, concept_id_list)
    concept_data = []
    if phenotype['concept_informations']:
        for c in json.loads(phenotype['concept_informations']):
            c['codingsystem'] = CodingSystem.objects.get(pk=Concept.history.get(id=c['concept_id'], history_id=c['concept_version_id']).coding_system_id)
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

    if phenotype['is_deleted'] == True:
        messages.info(request, "This phenotype has been deleted.")

    context = {
        'phenotype': phenotype,
        'concept_informations': json.dumps(phenotype['concept_informations']),
        'tags': tags,
        'data_sources': data_sources,
        'clinicalTerminologies': clinicalTerminologies,
        'user_can_edit': False,  # for now  #can_edit,
        'allowed_to_create': False,  # for now  #user_allowed_to_create,    # not settings.CLL_READ_ONLY,
        'user_can_export': user_can_export,
        'history': history,
        'live_ver_is_deleted': Phenotype.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'approval_status': approval_status,
        'publish_date': publish_date,
        'is_latest_version': is_latest_version,
        'is_latest_pending_version':is_latest_pending_version,
        'current_phenotype_history_id': int(phenotype_history_id),
        'component_tab_active': component_tab_active,
        'codelist_tab_active': codelist_tab_active,
        'codelist': codelist,  # json.dumps(codelist)
        'codelist_loaded': codelist_loaded,
        'concepts_id_name': concepts_id_name,
        'concept_data': concept_data,
        'page_canonical_path': get_canonical_path_by_brand(request, Phenotype, pk, phenotype_history_id),
        'q': db_utils.get_q_highlight(request, request.session.get('phenotype_search', '')),
        'force_highlight_result':  ['0', '1'][db_utils.is_referred_from_search_page(request)]                              
    }

    return render(request, 
                  'clinicalcode/phenotype/detail_combined.html',
                  context)

def get_history_table_data(request, pk):
    """"
        get history table data for the template
    """
    
    versions = Phenotype.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = db_utils.getHistoryPhenotype(v.history_id
                                        , highlight_result = [False, True][db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = db_utils.get_q_highlight(request, request.session.get('phenotype_search', ''))  
                                        )
        
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        ver['updated_by'] = None
        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(Phenotype, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedPhenotype.objects.get(phenotype_id=ver['id'], phenotype_history_id=ver['history_id'], approval_status=2).created
        else:
            ver['publish_date'] = None

        ver['approval_status'] = -1
        ver['approval_status_label'] = ''
        if PublishedPhenotype.objects.filter(phenotype_id=ver['id'], phenotype_history_id=ver['history_id']).exists():
            ver['approval_status'] = PublishedPhenotype.objects.get(phenotype_id=ver['id'], phenotype_history_id=ver['history_id']).approval_status
            ver['approval_status_label'] = APPROVED_STATUS[ver['approval_status']][1]        
        
        
        if request.user.is_authenticated:
            if allowed_to_edit(request, Phenotype, pk) or allowed_to_view(request, Phenotype, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)
                
    return historical_versions
                

def checkConceptVersionIsTheLatest(phenotypeID):
    # check live version

    phenotype = Phenotype.objects.get(pk=phenotypeID)

    is_ok = True
    version_alerts = {}

    if not phenotype.concept_informations:
        return is_ok, version_alerts

    concepts_id_versionID = json.loads(phenotype.concept_informations)

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
def phenotype_conceptcodesByVersion(request,
                                    pk,
                                    phenotype_history_id,
                                    target_concept_id=None,
                                    target_concept_history_id=None):
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
                            Phenotype,
                            pk,
                            set_history_id=phenotype_history_id)

    # here, check live version
    current_ph = Phenotype.objects.get(pk=pk)

    #     children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request,
    #                                                                                                 Phenotype, pk,
    #                                                                                                 set_history_id=phenotype_history_id)
    #     if not children_permitted_and_not_deleted:
    #         raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    # --------------------------------------------------

    codes = db_utils.get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id, target_concept_id, target_concept_history_id)

    data = dict()
    data['form_is_valid'] = True


    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = db_utils.getGroupOfConceptsByPhenotypeId_historical(pk, phenotype_history_id)

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


@login_required
def phenotype_create(request):
    """
        create a phenotype
    """
    # TODO: implement this
    pass


class PhenotypeUpdate(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin,
                      UpdateView):
    """
        Update the current phenotype.
    """
    # ToDo
    pass


class PhenotypeDelete(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin,
                      TemplateResponseMixin, View):
    """
        Delete a phenotype.
    """
    # ToDo
    pass


def history_phenotype_codes_to_csv(request, pk, phenotype_history_id=None):
    """
        Return a csv file of codes for a phenotype for a specific historical version.
    """
    if phenotype_history_id is None:
        # get the latest version
        phenotype_history_id = Phenotype.objects.get(pk=pk).history.latest().history_id
        
    # validate access for login and public site
    validate_access_to_view(request,
                            Phenotype,
                            pk,
                            set_history_id=phenotype_history_id)

    is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)

    # ----------------------------------------------------------------------

    # exclude(is_deleted=True)
    if Phenotype.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # exclude(is_deleted=True)
    if Phenotype.history.filter(id=pk, history_id=phenotype_history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # here, check live version
    current_ph = Phenotype.objects.get(pk=pk)

    if not is_published:
        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request, Phenotype, pk, set_history_id=phenotype_history_id)
        if not children_permitted_and_not_deleted:
            raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    current_ph_version = Phenotype.history.get(id=pk, history_id=phenotype_history_id)

    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = db_utils.getGroupOfConceptsByPhenotypeId_historical(pk, phenotype_history_id)

    my_params = {
        'phenotype_id': pk,
        'phenotype_history_id': phenotype_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="phenotype_PH%(phenotype_id)s_ver_%(phenotype_history_id)s_concepts_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    final_titles = ([
        'code', 'description', 'coding_system', 'concept_id',
        'concept_version_id'
        ] 
        + ['concept_name'] +
        ['phenotype_id', 'phenotype_version_id', 'phenotype_name'])

    writer.writerow(final_titles)

    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name

        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        for cc in codes:
            rows_no += 1
            writer.writerow([
                cc['code'], cc['description'].encode('ascii', 'ignore').decode('ascii'), concept_coding_system, 'C' +
                str(concept_id), concept_version_id
            ] + [
                Concept.history.get(id=concept_id,
                                    history_id=concept_version_id).name
            ] + [
                current_ph_version.friendly_id, current_ph_version.history_id,
                current_ph_version.name
            ])

        if rows_no == 0:
            writer.writerow([
                '', '', concept_coding_system, 'C' +
                str(concept_id), concept_version_id
            ] + [
                Concept.history.get(id=concept_id,
                                    history_id=concept_version_id).name
            ] + [
                current_ph_version.friendly_id, current_ph_version.history_id,
                current_ph_version.name
            ])

    return response


class PhenotypePublish(LoginRequiredMixin, HasAccessToViewPhenotypeCheckMixin,
                       TemplateResponseMixin, View):
    model = Phenotype
    template_name = 'clinicalcode/phenotype/publish.html'

    errors = {}
    allow_to_publish = True
    phenotype_is_deleted = False
    is_owner = True
    is_moderator = True
    phenotype_has_codes = True
    AllnotDeleted = True
    AllarePublished = True
    isAllowedtoViewChildren = True

    def checkPhenotypeTobePublished(self, request, pk, phenotype_history_id):
        global errors, allow_to_publish, phenotype_is_deleted, is_owner, is_moderator,is_latest_pending_version
        global phenotype_has_codes, AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        '''
            Allow to publish if:
            - Phenotype is not deleted
            - user is an owner
            - Phenotype contains codes
            - all conceots are published
        '''
        errors = {}
        allow_to_publish = True
        phenotype_is_deleted = False
        is_owner = True
        is_moderator = False
        is_latest_pending_version = False
        phenotype_has_codes = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        if (Phenotype.objects.get(id=pk).is_deleted == True):
            allow_to_publish = False
            phenotype_is_deleted = True

        if (Phenotype.objects.filter(Q(id=pk), Q(owner=self.request.user)).count() == 0):
            allow_to_publish = False
            is_owner = False

        if (self.request.user.groups.filter(name="Moderators").exists()):
            allow_to_publish = True
            is_moderator = True

        if (self.request.user.groups.filter(name="Moderators").exists()
                and not (Phenotype.objects.filter(Q(id=pk), Q(owner=self.request.user)).count() == 0)):
            allow_to_publish = True
            is_owner = True
            is_moderator = True

        if len(PublishedPhenotype.objects.filter(phenotype_id=pk,phenotype_history_id = phenotype_history_id,approval_status=1)) > 0:
            is_latest_pending_version = True
       # print(is_latest_pending_version)

        if (len(db_utils.get_phenotype_conceptcodesByVersion(self.request, pk, phenotype_history_id)) == 0):
            allow_to_publish = False
            phenotype_has_codes = False

        has_child_concepts, isOK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors = checkAllChildConcepts4Publish_Historical(request, pk, phenotype_history_id)
        if not isOK:
            allow_to_publish = False

    def get(self, request, pk, phenotype_history_id):
        global errors, allow_to_publish, phenotype_is_deleted, is_owner, approval_status, is_moderator,is_latest_pending_version
        global phenotype_has_codes, AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        errors = {}
        allow_to_publish = True
        phenotype_is_deleted = False
        is_owner = True
        is_moderator = True
        phenotype_has_codes = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        phenotype_ver = Phenotype.history.get(id=pk, history_id=phenotype_history_id)
        is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)
        approval_status = get_publish_approval_status(Phenotype, pk, phenotype_history_id)
        is_lastapproved = len(PublishedPhenotype.objects.filter(phenotype = Phenotype.objects.get(pk=pk).id,approval_status=2))>0

        self.checkPhenotypeTobePublished(request, pk, phenotype_history_id)

        if not is_published:
            self.checkPhenotypeTobePublished(request, pk, phenotype_history_id)

        # --------------------------------------------

        return self.render_to_response({
            'pk': pk,
            'name': phenotype_ver.name,
            'phenotype_history_id': phenotype_history_id,
            'is_published': is_published,
            'allowed_to_publish': allow_to_publish,
            'is_owner': is_owner,
            'approval_status': approval_status,
            'is_lastapproved':is_lastapproved,
            'is_latest_pending_version':is_latest_pending_version,
            'is_moderator': is_moderator,
            'phenotype_is_deleted': phenotype_is_deleted,
            'phenotype_has_codes': phenotype_has_codes,
            'AllnotDeleted': AllnotDeleted,
            'AllarePublished': AllarePublished,
            'isAllowedtoViewChildren': isAllowedtoViewChildren,
            'errors': errors
        })



    def post(self, request, pk, phenotype_history_id):
        global errors, allow_to_publish, phenotype_is_deleted, is_owner, phenotype_has_codes, approval_status, is_moderator,\
            is_latest_pending_version
        global AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        errors = {}
        allow_to_publish = True
        phenotype_is_deleted = False
        is_owner = True
        is_moderator = True
        phenotype_has_codes = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)
        approval_status = get_publish_approval_status(Phenotype, pk, phenotype_history_id)

        self.checkPhenotypeTobePublished(request, pk, phenotype_history_id)


        data = dict()

        submitValue = self.validate_request(request)



        if 'decline' == submitValue or (approval_status == 3 and is_moderator):
                return self.update_published(request, pk, phenotype_history_id, submitValue, is_latest_pending_version)

        elif 'publish' == submitValue:
            if not allow_to_publish or (is_published and approval_status == 2):

                data['form_is_valid'] = False
                data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)
                return JsonResponse(data)

            try:
                if (allow_to_publish and not is_published and approval_status is None) or (approval_status == 2 and not is_published):
                    # start a transaction
                    with transaction.atomic():
                        #if moderator publish automaticaly
                        if is_moderator:
                            phenotype = Phenotype.objects.get(pk=pk)


                            published_phenotype = PublishedPhenotype(phenotype_id=phenotype.id,
                                                                    phenotype_history_id=phenotype_history_id,
                                                                    approval_status = 2,
                                                                    moderator = request.user,
                                                                    created_by=Phenotype.objects.get(pk=pk).created_by)
                            published_phenotype.save()

                            data['approval_status'] = 2
                            data = self.form_validation(request, data, phenotype_history_id, pk, phenotype)

                        else:
                            #Check if already published phenotype to publish automatically
                            if len(PublishedPhenotype.objects.filter(phenotype = Phenotype.objects.get(pk=pk).id,approval_status=2))>0:

                                phenotype = Phenotype.objects.get(pk=pk)
                                published_phenotype = PublishedPhenotype.objects.filter(phenotype_id=phenotype.id,approval_status=2).first()
                                published_phenotype_new = PublishedPhenotype(phenotype=phenotype,
                                                                            phenotype_history_id=phenotype_history_id,
                                                                            approval_status=2,
                                                                            moderator = published_phenotype.moderator,
                                                                            created_by=request.user)
                                published_phenotype_new.save()
                                data['approval_status'] = 2

                              #Not for phase 1
                          #  elif len(PublishedPhenotype.objects.filter(phenotype = Phenotype.objects.get(pk=pk).id,approval_status=1))>0:
                           #     phenotype = Phenotype.objects.get(pk=pk)
                           #     published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype.id)
                            #    published_phenotype.phenotype_history_id = phenotype_history_id
                           #     published_phenotype.approval_status = 1
                            #    published_phenotype.created_by = PublishedPhenotype.objects.get(
                            #        phenotype_id=phenotype.id).created_by
                           #     published_phenotype.save()
                           #     data['approval_status'] = 1
                            else:
                                # put phenotype version in the pending state
                                phenotype = Phenotype.objects.get(pk=pk)
                                published_phenotype = PublishedPhenotype(phenotype=phenotype,
                                                                        phenotype_history_id=phenotype_history_id,
                                                                        approval_status=1,
                                                                        created_by=request.user)
                                published_phenotype.save()
                                data['approval_status'] = 1

                            data = self.form_validation(request, data, phenotype_history_id, pk, phenotype)
                #Publish pending phenotype if mod wants it
                elif approval_status == 1 and is_moderator:
                    # start a transaction
                    with transaction.atomic():

                        phenotype = Phenotype.objects.get(pk=pk)
                        published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype.id,phenotype_history_id = phenotype_history_id,approval_status=1)
                        published_phenotype.phenotype_history_id = phenotype_history_id
                        published_phenotype.approval_status = 2
                        published_phenotype.moderator = request.user
                        published_phenotype.created_by = PublishedPhenotype.objects.get(phenotype_id=phenotype.id,phenotype_history_id = phenotype_history_id ,approval_status=1).created_by
                        published_phenotype.save()

                        data['approval_status'] = 2
                        data = self.form_validation(request, data, phenotype_history_id, pk, phenotype)






            except Exception as e:
               # print(e)
                data['form_is_valid'] = False
                data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)

            return JsonResponse(data)

    def form_validation(self, request, data, phenotype_history_id, pk, phenotype):
        data['form_is_valid'] = True
        data['latest_history_ID'] = phenotype_history_id  # phenotype.history.latest().pk



        # update history list
        data['html_history_list'] = render_to_string(
            'clinicalcode/phenotype/partial_history_list.html',
            {
                'history': get_history_table_data(request, pk), #phenotype.history.all(),
                'current_phenotype_history_id': int(phenotype_history_id),  # phenotype.history.latest().pk,
                'published_historical_ids':
                    list(PublishedPhenotype.objects.filter(phenotype_id=pk,approval_status=2).values_list('phenotype_history_id', flat=True))

            },
            request=self.request)

        data['message'] = self.send_message(pk, phenotype_history_id, data, phenotype, approval_status, is_moderator)['message']
        return data

    def send_message(self, pk, phenotype_history_id, data,phenotype, approval_status, is_moderator):
        if approval_status == 2:
            data['message'] = render_to_string('clinicalcode/phenotype/published.html', 
                                               {
                                                'id': pk,
                                                'phenotype_history_id': phenotype_history_id
                                               },
                                               self.request)
            self.send_email_decision(phenotype,approval_status)
            return data

        elif len(PublishedPhenotype.objects.filter(phenotype = Phenotype.objects.get(pk=pk).id,approval_status=2))>0 and not approval_status == 3:
            data['message'] = render_to_string('clinicalcode/phenotype/published.html', 
                                               {
                                                'id': pk,
                                                'phenotype_history_id': phenotype_history_id
                                               }, 
                                               self.request)
            self.send_email_decision(phenotype, approval_status)
            return data


        elif approval_status == 1:
            data['message'] = render_to_string('clinicalcode/phenotype/published.html', 
                                               {
                                                    'id': pk,
                                                    'phenotype_history_id': phenotype_history_id
                                               }, 
                                               self.request)
            self.send_email_decision(phenotype, approval_status)
            return data

        elif approval_status == 3:
            data['message'] = render_to_string('clinicalcode/phenotype/declined.html', 
                                               {
                                                'id': pk,
                                                'phenotype_history_id': phenotype_history_id
                                               }, 
                                               self.request)
            self.send_email_decision(phenotype, approval_status)
            return data

        elif approval_status is None and is_moderator:
            data['message'] = render_to_string('clinicalcode/phenotype/published.html', 
                                               {
                                                'id': pk,
                                                'phenotype_history_id': phenotype_history_id
                                               }, 
                                               self.request)
            return data

        elif approval_status is None:
            data['message'] = render_to_string('clinicalcode/phenotype/approve.html', 
                                               {
                                                'id': pk,
                                                'phenotype_history_id': phenotype_history_id
                                                }, 
                                               self.request)
            return data


    def send_email_decision(self,phenotype,approved):

        if approved == 1:
           db_utils.send_review_email(phenotype,
                                      "Published",
                                      "Phenotype has been successfully approved and published on the website")

        elif approved == 2:
            # This line for the case when user want to get notification of same phenotype id but different version
           db_utils.send_review_email(phenotype,
                                      "Published",
                                      "Phenotype has been successfully approved and published on the website")
        elif approved == 3:
            db_utils.send_review_email(phenotype, 
                                       "Rejected",
                                       "Phenotype has been rejected by the moderator. Please consider update changes and try again")




    def validate_request(self,request):
        
        if request.method == 'POST':
            if 'publish' in request.POST['value']:
                return 'publish'
            elif 'decline' in request.POST['value']:
                return 'decline'


    def update_published(self, request, pk, phenotype_history_id,submitValue,is_latest_pending_version):
        errors = {}
        data = dict()

        try:
            # start a transaction
            with transaction.atomic():
                #If moderator clicks decline put to decline state
                if submitValue == "decline":

                    approval_status = 3
                    phenotype = Phenotype.objects.get(pk=pk)
                    published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype, phenotype_history_id=phenotype_history_id)
                    published_phenotype.moderator = request.user
                    published_phenotype.approval_status = approval_status
                    published_phenotype.save()



                #Publish previosly declined phenotype
                elif submitValue == "publish":

                    approval_status = 2
                    phenotype = Phenotype.objects.get(pk=pk)
                    published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype, phenotype_history_id=phenotype_history_id)
                    published_phenotype.moderator = request.user
                    published_phenotype.approval_status = approval_status
                    published_phenotype.save()




                data['form_is_valid'] = True
                data[
                    'latest_history_ID'] = phenotype_history_id  # phenotype.history.latest().pk
                data['approval_status'] = approval_status


                list_published_id = []
                if data['approval_status'] == 2:
                  list_published_id =list(PublishedPhenotype.objects.filter(phenotype_id=pk, approval_status=2).values_list('phenotype_history_id', flat=True))


                # update history list
                data['html_history_list'] = render_to_string(
                    'clinicalcode/phenotype/partial_history_list.html',
                    {
                        'history': get_history_table_data(request, pk),  #phenotype.history.all(),
                        'current_phenotype_history_id':int(phenotype_history_id),  # phenotype.history.latest().pk,
                        'published_historical_ids': list_published_id
                    },
                    request=self.request)

                data['message'] = self.send_message(pk, phenotype_history_id, data, phenotype, approval_status, is_moderator)['message']



        except Exception as e:
            data['form_is_valid'] = False
           # print(e)
            data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)

        return JsonResponse(data)


# ---------------------------------------------------------------------------
def checkAllChildConcepts4Publish_Historical(request, phenotype_id,
                                             phenotype_history_id):

    phenotype = db_utils.getHistoryPhenotype(phenotype_history_id)


    if len(phenotype['concept_informations']) == 0:
        has_child_concepts = False
        child_concepts_versions = ''
    else:
        child_concepts_versions = [(x['concept_id'], x['concept_version_id']) for x in json.loads(phenotype['concept_informations']) ]

    # Now check all the child concepts for deletion(from live version) and Publish(from historical version)
    # we check access(from live version) here.

    errors = {}
    has_child_concepts = False
    if child_concepts_versions:
        has_child_concepts = True

    AllnotDeleted = True
    for cc in child_concepts_versions:
        isDeleted = False
        isDeleted = (Concept.objects.filter(Q(id=cc[0])).exclude(is_deleted=True).count() == 0)
        if (isDeleted):
            errors[cc[0]] = 'Child concept (' + str(cc[0]) + ') is deleted'
            AllnotDeleted = False

    AllarePublished = True
    for cc in child_concepts_versions:
        is_published = False
        is_published = checkIfPublished(Concept, cc[0], cc[1])
        if (not is_published):
            errors[str(cc[0]) + '/' + str(cc[1])] = 'Child concept (' + str(cc[0]) + '/' + str(cc[1]) + ') is not published'
            AllarePublished = False

    # Now check all for access.
    isAllowedtoViewChildren = True

    for cc in child_concepts_versions:
        permitted = False
        permitted = allowed_to_view(request,
                                    Concept,
                                    set_id=cc[0],
                                    set_history_id=cc[1])

        if (not permitted):
            errors[str(cc[0]) + '_view'] = 'Child concept (' + str(cc[0]) + ') is not permitted.'
            isAllowedtoViewChildren = False

    isOK = (AllnotDeleted and AllarePublished and isAllowedtoViewChildren)

    return has_child_concepts, isOK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors

