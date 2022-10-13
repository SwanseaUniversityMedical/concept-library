'''
    ---------------------------------------------------------------------------
    WorkingSet selection view
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


def selection_list(request):
    '''
        Returns phenotype list & assoc. concepts
    '''
    if not request.user.is_authenticated:
        raise PermissionDenied()

    method = request.GET.get('method', '')
    if method != '1':
        return redirect('/workingsets/')
    
    search_tag_list = []
    tags = []
    selected_phenotype_types_list = []

    page_size = utils.get_int_value(request.GET.get('page_size', 20), 20)
    page_size = page_size if page_size in db_utils.page_size_limits else 20
    page = utils.get_int_value(request.GET.get('page', 1), 1)
    search = request.GET.get('search', '')
    tag_ids = request.GET.get('tag_ids', '')
    collection_ids = request.GET.get('collection_ids', '')
    owner = request.GET.get('owner', '')
    author = request.GET.get('author', '')
    coding_ids = request.GET.get('coding_ids', '')
    des_order = request.GET.get('order_by', '')
    selected_phenotype_types = request.GET.get('selected_phenotype_types', '')
    phenotype_brand = request.GET.get('phenotype_brand', '')
    data_sources = request.GET.get('data_source_ids', '')
    start_date_range = request.GET.get('startdate', '')
    end_date_range = request.GET.get('enddate', '')
    
    start_date_query, end_date_query = False, False
    try:
        start_date_query = make_aware(datetime.datetime.strptime(start_date_range, '%Y-%m-%d'))
        end_date_query = make_aware(datetime.datetime.strptime(end_date_range, '%Y-%m-%d'))
    except ValueError:
        start_date_query = False
        end_date_query = False

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
                filter_cond += " AND (id ='" + str(ret_int_id) + "') "
    
    # Change to collections once model + data represents parameter
    collections, filter_cond = db_utils.apply_filter_condition(query='tags', selected=collection_ids, conditions=filter_cond)

    tags, filter_cond = db_utils.apply_filter_condition(query='tags', selected=tag_ids, conditions=filter_cond)
    coding, filter_cond = db_utils.apply_filter_condition(query='clinical_terminologies', selected=coding_ids, conditions=filter_cond)
    sources, filter_cond = db_utils.apply_filter_condition(query='data_sources', selected=data_sources, conditions=filter_cond)
    selected_phenotype_types_list, filter_cond = db_utils.apply_filter_condition(query='phenotype_type', selected=selected_phenotype_types, conditions=filter_cond, data=phenotype_types_list)
    daterange, filter_cond = db_utils.apply_filter_condition(query='daterange', selected={'start': [start_date_query, start_date_range], 'end': [end_date_query, end_date_range]}, conditions=filter_cond)

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                filter_cond += " AND owner_id=" + str(owner_id)
            else:
                # username not found
                filter_cond += " AND owner_id= -1 "

    # show phenotype for a specific brand
    if phenotype_brand != "":
        current_brand = Brand.objects.all().filter(name=phenotype_brand)
        group_list = list(current_brand.values_list('groups', flat=True))
        filter_cond += " AND group_id IN(" + ', '.join(map(str, group_list)) + ") "

    order_param = db_utils.get_order_from_parameter(des_order).replace(" id,", " REPLACE(id, 'PH', '')::INTEGER,")
    phenotype_srch = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                                            search=[search, ''][search_by_id],
                                                                            author=author,
                                                                            exclude_deleted=exclude_deleted,
                                                                            filter_cond=filter_cond,
                                                                            approved_status=approved_status,
                                                                            show_top_version_only=0,
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

    filter_statistics_ordering = json.dumps(filter_statistics_ordering)

    # JSONified filter data
    filter_data = {
        'coding_data': [{'name': tag.description, 'id': tag.id} for tag in coding_system_reference],
        'tag_data': [{'name': tag, 'id': tagid} for tag, tagid in brand_associated_tags.items()],
        'collection_data': [{'name': tag.description, 'id': tag.id} for tag in brand_associated_collections],
        'phenotype_data': [{'name': tag, 'id': tag} for tag in phenotype_types_list],
        'datasource_data': [{'name': tag.name, 'id': tag.id} for tag in data_source_reference],
    }

    filter_data = json.dumps(filter_data)

    # JSONified concept data for current page obj
    concept_data = { }
    for phenotype in p.object_list:
        if phenotype['concept_informations']:
            concept_id_list = [x['concept_id'] for x in phenotype['concept_informations'] ]
            concept_hisoryid_list = [x['concept_version_id'] for x in phenotype['concept_informations'] ]
            concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list) #.values('id', 'history_id', 'name', 'group')
            concept_data[phenotype['id']] = {
                'phenotype_id': phenotype['id'],
                'concepts': list(concepts)
            }

    # ctx
    context = {
        'concept_data': concept_data,
        'filter_data': filter_data,
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'tags': tags,
        'tag_ids': tag_ids2,
        'tag_ids_list': tag_ids_list,
        'collections': collections,
        'collection_ids': collection_ids,
        'collection_ids_list': collection_ids_list,
        'owner': owner,
        'allowed_to_create': not settings.CLL_READ_ONLY,
        'phenotype_brand': phenotype_brand,
        'allTags': Tag.objects.all().order_by('description'),
        'all_CodingSystems': CodingSystem.objects.all().order_by('id'),
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

    return render(request, 'clinicalcode/workingset/selection_results.html', context)
