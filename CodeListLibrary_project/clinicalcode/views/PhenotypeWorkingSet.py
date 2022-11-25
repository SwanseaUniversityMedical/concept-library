import csv
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime
from collections import OrderedDict as ordr
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
from ..db_utils import validate_phenotype_workingset_attribute_group
from ..view_utils import workingset_db_utils
from clinicalcode.forms.WorkingsetForm import WorkingsetForm
from ..models import *
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.constants import *
from django.db.models.functions import Lower
from clinicalcode.constants import Type_status
from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)


class MessageMixin(object):
    '''
        Make it easy to display notification messages when using Class Based Views.
    '''

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(MessageMixin, self).delete(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super(MessageMixin, self).form_valid(form)


@login_required
def workingset_list(request):
    '''
        display the list of working sets. This view can be searched and contains paging
    '''

    search_tag_list = []
    tags = []
    # get page index variables from query or from session
    expand_published_versions = 0  # disable this option
        
    method = request.GET.get('filtermethod', '')
    page_size = utils.get_int_value(request.GET.get('page_size', request.session.get('ph_workingset_page_size', 20)), 20)
    page = utils.get_int_value(request.GET.get('page', request.session.get('ph_workingset_page', 1)), 1)
    search = request.GET.get('search', request.session.get('ph_workingset_search', ''))
    tag_ids = request.GET.get('tag_ids', request.session.get('ph_workingset_tagids', ''))
    collection_ids = request.GET.get('collection_ids', request.session.get('ph_workingset_collection_ids', ''))
    owner = request.GET.get('owner', request.session.get('ph_workingset_owner', ''))
    author = request.GET.get('author', request.session.get('ph_workingset_author', ''))
    #coding_ids = request.GET.get('codingids', request.session.get('ph_workingset_codingids', ''))
    des_order = request.GET.get('order_by', request.session.get('ph_workingset_order_by', ''))
    data_sources = request.GET.get('data_source_ids', request.session.get('ph_workingset_data_source_ids', ''))
    ph_workingset_brand = request.GET.get('ph_workingset_brand', request.session.get('ph_workingset_brand', ''))  # request.CURRENT_BRAND
    
    show_deleted_ph_workingsets = request.GET.get('show_deleted_ph_workingsets', request.session.get('ph_workingset_show_deleted_ph_workingsets', 0))
    show_my_ph_workingsets = request.GET.get('show_my_ph_workingsets', request.session.get('ph_workingset_show_my_workingsets', 0))
    show_only_validated_workingsets = request.GET.get('show_only_validated_workingsets', request.session.get('ph_show_only_validated_workingsets', 0))
    ph_workingset_must_have_published_versions = request.GET.get('ph_workingset_must_have_published_versions', request.session.get('ph_workingset_must_have_published_versions', 0))

    show_my_pending_workingsets = request.GET.get('show_my_pending_workingsets', request.session.get('ph_workingset_show_my_pending_workingsets', 0))
    show_mod_pending_workingsets = request.GET.get('show_mod_pending_workingsets', request.session.get('ph_workingset_show_mod_pending_workingsets', 0))
    show_rejected_workingsets = request.GET.get('show_rejected_workingsets', request.session.get('ph_workingset_show_rejected_workingsets', 0))
    
    ph_workingset_selected_types = request.GET.get('selected_workingset_types', request.session.get('ph_workingset_selected_types', ''))
   
    search_form = request.GET.get('search_form', request.session.get('ph_workingset_search_form', 'basic-form'))

    start_date_range = request.GET.get('startdate', request.session.get('ph_workingset_date_start', ''))
    end_date_range = request.GET.get('enddate', request.session.get('ph_workingset_date_end', ''))
    
    start_date_query, end_date_query = False, False
    try:
        start_date_query = make_aware(datetime.datetime.strptime(start_date_range, '%Y-%m-%d'))
        end_date_query = make_aware(datetime.datetime.strptime(end_date_range, '%Y-%m-%d'))
    except ValueError:
        start_date_query = False
        end_date_query = False
        
    # store page index variables to session
    request.session['ph_workingset_page_size'] = page_size
    request.session['ph_workingset_page'] = page
    request.session['ph_workingset_search'] = search  
    request.session['ph_workingset_tagids'] = tag_ids
    request.session['ph_workingset_brand'] = ph_workingset_brand   
    request.session['ph_workingset_selected_types'] = ph_workingset_selected_types
    request.session['ph_workingset_author'] = author  
    request.session['ph_workingset_owner'] = owner     
    request.session['ph_workingset_show_my_workingsets'] = show_my_ph_workingsets
    request.session['ph_workingset_show_deleted_ph_workingsets'] = show_deleted_ph_workingsets
    request.session['ph_show_only_validated_workingsets'] = show_only_validated_workingsets
    request.session['ph_workingset_must_have_published_versions'] = ph_workingset_must_have_published_versions 
    request.session['ph_workingset_search_form'] = search_form
    request.session['ph_workingset_show_my_pending_workingsets'] = show_my_pending_workingsets    
    request.session['ph_workingset_show_mod_pending_workingsets'] = show_mod_pending_workingsets
    request.session['ph_workingset_show_rejected_workingsets'] = show_rejected_workingsets
    request.session['ph_workingset_collection_ids'] = collection_ids
    #request.session['ph_workingset_codingids'] = coding_ids
    request.session['ph_workingset_date_start'] = start_date_range
    request.session['ph_workingset_date_end'] = end_date_range
    request.session['ph_workingset_order_by'] = des_order  
    request.session['ph_workingset_data_source_ids'] = data_sources

    # remove leading, trailing and multiple spaces from text search params
    search = re.sub(' +', ' ', search.strip())
    owner = re.sub(' +', ' ', owner.strip())
    author = re.sub(' +', ' ', author.strip())
        
    filter_cond = " 1=1 "
    approved_status = []
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published

    # available ph_workingset_types in the DB
    ph_workingset_types_list, ph_workingset_types_order = workingset_db_utils.get_brand_associated_workingset_types(request, brand=None)
    ph_workingset_selected_types_list = {ph_workingset_types_order[k]: v for k, v in enumerate(ph_workingset_types_list)}
    
    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'WS' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^WS\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_id = db_utils.chk_valid_id(request, set_class=PhenotypeWorkingset, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id ='" + str(ret_id) + "') "

    collections, filter_cond = db_utils.apply_filter_condition(query='collections', selected=collection_ids, conditions=filter_cond)
    tags, filter_cond = db_utils.apply_filter_condition(query='tags', selected=tag_ids, conditions=filter_cond)
    #coding, filter_cond = db_utils.apply_filter_condition(query='clinical_terminologies', selected=coding_ids, conditions=filter_cond)
    sources, filter_cond = db_utils.apply_filter_condition(query='data_sources', selected=data_sources, conditions=filter_cond)
    selected_phenotype_types_list, filter_cond = db_utils.apply_filter_condition(query='workingset_type', selected=ph_workingset_selected_types, conditions=filter_cond, data=ph_workingset_types_list)
    daterange, filter_cond = db_utils.apply_filter_condition(query='daterange', selected={'start': [start_date_query, start_date_range], 'end': [end_date_query, end_date_range]}, conditions=filter_cond)
    
    
    # check if it is the public site or not
    if request.user.is_authenticated:
        # ensure that user is only allowed to view/edit the relevant phenotype

        get_live_and_or_published_ver = 3
        if ph_workingset_must_have_published_versions == "1":
            get_live_and_or_published_ver = 2

        # show only phenotype owned by the current user
        if show_my_ph_workingsets == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)


        # publish approval
        if is_member(request.user, "Moderators"):
            if show_mod_pending_workingsets == "1":
                approved_status += [1]
            if show_rejected_workingsets == "1":
                approved_status += [3]                
        else:
            if show_my_pending_workingsets == "1" or show_rejected_workingsets == "1":
                filter_cond += " AND owner_id=" + str(request.user.id) 
            if show_my_pending_workingsets == "1":
                approved_status = [1]
            if show_rejected_workingsets == "1":
                approved_status += [3]  

        # if show deleted phenotype is 1 then show deleted phenotype
        if show_deleted_ph_workingsets != "1":
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

    # if show_only_validated_workingsets is 1 then show only phenotype with validation_performed=True
    if show_only_validated_workingsets == "1":
        filter_cond += " AND COALESCE(validation_performed, FALSE) IS TRUE "

    # show phenotype for a specific brand
    if ph_workingset_brand != "":
        current_brand = Brand.objects.all().filter(name=ph_workingset_brand)
        group_list = list(current_brand.values_list('groups', flat=True))
        filter_cond += " AND group_id IN(" + ', '.join(map(str, group_list)) + ") "

    order_param = db_utils.get_order_from_parameter(des_order).replace(" id,", " REPLACE(id, 'WS', '')::INTEGER,")
    workingset_srch = workingset_db_utils.get_visible_live_or_published_phenotype_workingset_versions(request,
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
    paginator = Paginator(workingset_srch,
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
        tag_ids_list = [int(t) for t in tag_ids.split(',')]

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
    # coding_system_reference, coding_order = db_utils.get_coding_system_reference(request, brand=None, concept_or_phenotype="phenotype")
    # coding_system_reference_ids = [x.id for x in coding_system_reference]
    # coding_id_list = []
    # if coding_ids:
    #     coding_id_list = utils.expect_integer_list(coding_ids)
    
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
        #'coding': coding_order,
        'types': ph_workingset_types_order,
        'datasources': datasource_order,
    }

    context = {
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'show_my_ph_workingsets': show_my_ph_workingsets,
        'show_deleted_ph_workingsets': show_deleted_ph_workingsets,
        'show_my_pending_workingsets': show_my_pending_workingsets,
        'show_mod_pending_workingsets': show_mod_pending_workingsets,
        'show_rejected_workingsets': show_rejected_workingsets,
        'workingset_must_have_published_versions': ph_workingset_must_have_published_versions,
        'show_only_validated_workingsets': show_only_validated_workingsets,
        'tags': tags,
        'tag_ids': tag_ids2,
        'tag_ids_list': tag_ids_list,
        'collections': collections,
        'collection_ids': collection_ids,
        'collection_ids_list': collection_ids_list,
        'owner': owner,
        'allowed_to_create': not settings.CLL_READ_ONLY,
        'ph_workingset_brand': ph_workingset_brand,
        'allTags': Tag.objects.all().order_by('description'),
        'all_CodingSystems': CodingSystem.objects.all().order_by('id'),
        'search_form': search_form,
        'p_btns': p_btns,
        'brand_associated_collections': brand_associated_collections,
        'brand_associated_collections_ids': brand_associated_collections_ids,
        'all_collections_selected': all(item in tag_ids_list for item in brand_associated_collections_ids),
        'workingset_types': ph_workingset_selected_types_list,
        'workingset_selected_types': [t for t in ph_workingset_selected_types.split(',') ],
        'workingset_selected_types_str': ph_workingset_selected_types,
        # 'coding_system_reference': coding_system_reference,
        # 'coding_system_reference_ids': coding_system_reference_ids,
        # 'coding_id_list': coding_id_list,
        # 'coding_ids': coding_ids,
        # 'all_coding_selected': all(item in coding_id_list for item in coding_system_reference_ids),
        'data_source_ids': data_sources,
        'data_source_list': data_sources_list,
        'data_sources_reference': data_source_reference,
        'brand_associated_tags': brand_associated_tags,
        'brand_associated_tags_ids': list(brand_associated_tags.values()),
        'all_tags_selected': all(item in tag_ids_list for item in brand_associated_tags.values()),
        'ordered_by': des_order,
        'filter_start_date': start_date_range,
        'filter_end_date': end_date_range,
        'filter_statistics_ordering': filter_statistics_ordering,
    }

    if method == 'basic-form':
        return render(request, 'clinicalcode/phenotypeworkingset/workingset_results.html', context)
    else:
        return render(request, 'clinicalcode/phenotypeworkingset/index.html', context)


def commaSeparate(request):
    data = request
    overall = None
    if data:
        overall = [int(i) for i in data.split(",")]
    return overall


class WorkingSetCreate(LoginRequiredMixin, HasAccessToCreateCheckMixin, MessageMixin, CreateView):
    model = PhenotypeWorkingset
    form_class = WorkingsetForm
    template_name = 'clinicalcode/phenotypeworkingset/form.html'


    def get_form_kwargs(self):
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def get_success_url(self):
        if allowed_to_edit(self.request, PhenotypeWorkingset, self.object.id):
            return reverse('phenotypeworkingset_update', args=(self.object.id, ))
        elif allowed_to_view(self.request, PhenotypeWorkingset, self.object.id):
            return reverse('phenotypeworkingset_detail', args=(self.object.id, ))
        else:
            return reverse('phenotypeworkingsets_list')



    def form_invalid(self, form):
        tag_ids = commaSeparate(self.request.POST.get('tagids'))
        collections = commaSeparate(self.request.POST.get('collections'))
        datasources = commaSeparate(self.request.POST.get('datasources'))
        publications = self.request.POST.get('publication_data')
        table_elements_data = self.request.POST.get('phenotypes_concepts_json')
        previous_selection = self.request.POST.get('previous_selection')
        context = self.get_context_data()


        if tag_ids:
            context['tags'] = Tag.objects.filter(pk__in=tag_ids)

        if collections:
            queryset = Tag.objects.filter(tag_type=2)
            context['collections'] = queryset.filter(id__in=collections)

        if datasources:
            context['datasources'] = DataSource.objects.filter(datasource_id__in=datasources)

        if publications:
            context['publications'] = publications

        if table_elements_data:
            context['table_elements'] = table_elements_data

        if previous_selection:
            context['previous_selection'] = previous_selection

        return self.render_to_response(context)

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.author = self.request.POST.get('author')
            form.instance.tags = commaSeparate(self.request.POST.get('tagids'))
            form.instance.collections = commaSeparate(self.request.POST.get('collections'))
            form.instance.data_sources = commaSeparate(self.request.POST.get('datasources'))
            form.instance.phenotypes_concepts_data = json.loads(self.request.POST.get('workingset_data') or '[]')
            form.instance.publications = json.loads(self.request.POST.get('publication_data') or '[]')

            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset, self.object.pk, "Created")
            messages.success(self.request, "Workingset has been successfully created.")

        return HttpResponseRedirect(self.get_success_url())


@login_required
def phenotype_workingset_DB_test_create(request):
    '''
        temp create test DB ws
    '''
    if not request.user.is_superuser:
        raise PermissionDenied

    import random

    test_workingset = PhenotypeWorkingset.objects.create(
        name="wokringset test #" + str(random.random() * 1000000),
        type=random.choice(Type_status)[0],
        tags=random.sample(list(Tag.objects.filter(tag_type=1).values_list('id', flat=True)), 1),
        collections=random.sample(list(Tag.objects.filter(tag_type=2).values_list('id', flat=True)), 2),
        publications=["paper no 1", "paper no 2", "paper no 3"],
        author="me, others, world",
        citation_requirements="citation requirements",
        description="description description description",
        data_sources=random.sample(list(DataSource.objects.values_list('id', flat=True)), 2),
        phenotypes_concepts_data=[
            {
                "phenotype_id": "PH1",
                "phenotype_version_id": 2,
                "concept_id": "C714",
                "concept_version_id": 2567,
                "Attributes": [
                    {
                        "name": "attr_1",
                        "type": "INT",
                        "value": "123"
                    },
                    {
                        "name": "attr_2",
                        "type": "STRING",
                        "value": "male/female"
                    }
                ]
            },
            {
                "phenotype_id": "PH3",
                "phenotype_version_id": 6,
                "concept_id": "C717",
                "concept_version_id": 2573,
                "Attributes": [
                    {
                        "name": "attr_1",
                        "type": "INT",
                        "value": "87523"
                    },
                    {
                        "name": "attr_2",
                        "type": "STRING",
                        "value": "male"
                    }
                ]
            },
            {
                "phenotype_id": "PH43",
                "phenotype_version_id": 86,
                "concept_id": "C806",
                "concept_version_id": 2751,
                "Attributes": [
                    {
                        "name": "attr_1",
                        "type": "INT",
                        "value": "654"
                    },
                    {
                        "name": "attr_2",
                        "type": "STRING",
                        "value": "female"
                    }
                ]
            }

        ],

        created_by=request.user,
        updated_by=request.user,
        owner=request.user,

        group=Group.objects.get(id=5),
        group_access=Permissions.VIEW,
        owner_access=Permissions.EDIT,
        world_access=Permissions.VIEW
    )

    return render(
        request,
        'custom-msg.html',
        {
            "successMsg": ["Working set created", test_workingset.id]
        }
    )


def WorkingsetDetail_combined(request, pk, workingset_history_id=None):
    ''' 
        Display the detail of a working set.
    '''

    # validate access for login and public site
    validate_access_to_view(request,
                            PhenotypeWorkingset,
                            pk,
                            set_history_id=workingset_history_id)

    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = int(PhenotypeWorkingset.objects.get(pk=pk).history.latest().history_id)

    is_published = checkIfPublished(PhenotypeWorkingset, pk, workingset_history_id)
    approval_status = get_publish_approval_status(PhenotypeWorkingset, pk, workingset_history_id)

    # ----------------------------------------------------------------------

    workingset = workingset_db_utils.getHistoryPhenotypeWorkingset(workingset_history_id,
                                                        highlight_result=[False, True][
                                                            db_utils.is_referred_from_search_page(request)],
                                                        q_highlight=db_utils.get_q_highlight(request,
                                                                                             request.session.get(
                                                                                                 'ph_workingset_search',
                                                                                                 ''))
                                                        )
    # The history working set contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the working set.
    if workingset['owner_id'] is not None:
        workingset['owner'] = User.objects.get(id=int(workingset['owner_id']))

    workingset['group'] = None
    if workingset['group_id'] is not None:
        workingset['group'] = Group.objects.get(id=int(workingset['group_id']))

    workingset_type = list(Type_status)[workingset['type']][1] if workingset['type'] < len(list(Type_status)) else ''

    tags = Tag.objects.filter(pk=-1)
    workingset_tags = workingset['tags']
    has_tags = False
    if workingset_tags:
        tags = Tag.objects.filter(pk__in=workingset_tags)
        has_tags = tags.count() != 0

    collections_tags = Tag.objects.filter(pk=-1)
    workingset_collections = workingset['collections']
    has_collections = False
    if workingset_collections:
        collections_tags = Tag.objects.filter(pk__in=workingset_collections)
        has_collections = collections_tags.count() != 0

    data_sources = DataSource.objects.filter(pk=-1)
    workingset_data_sources = workingset['data_sources']
    if workingset_data_sources:
        data_sources = DataSource.objects.filter(pk__in=workingset_data_sources)

    is_latest_version = (
            int(workingset_history_id) == PhenotypeWorkingset.objects.get(pk=pk).history.latest().history_id)
    is_latest_pending_version = False

    if len(PublishedWorkingset.objects.filter(workingset_id=pk, workingset_history_id=workingset_history_id,
                                              approval_status=1)) > 0:
        is_latest_pending_version = True

    children_permitted_and_not_deleted = True
    error_dic = {}
    are_concepts_latest_version = True
    version_alerts = {}

    if request.user.is_authenticated:
        can_edit = (not PhenotypeWorkingset.objects.get(pk=pk).is_deleted) and allowed_to_edit(request,
                                                                                               PhenotypeWorkingset, pk)

        can_restore = PhenotypeWorkingset.objects.get(pk=pk).is_deleted and allowed_to_edit(request,
                                                                                               PhenotypeWorkingset, pk)

        user_can_export = (
                allowed_to_view_children(request, PhenotypeWorkingset, pk, set_history_id=workingset_history_id)
                and db_utils.chk_deleted_children(
            request,
            PhenotypeWorkingset,
            pk,
            returnErrors=False,
            set_history_id=workingset_history_id)
                and not PhenotypeWorkingset.objects.get(pk=pk).is_deleted)
        user_allowed_to_create = allowed_to_create()

        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request,
                                                                                                      PhenotypeWorkingset,
                                                                                                      pk)

        # if is_latest_version:
        #     are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(pk)

    else:
        can_edit = False
        can_restore =False
        user_can_export = is_published
        user_allowed_to_create = False

    publish_date = None
    if is_published:
        publish_date = PublishedWorkingset.objects.get(workingset_id=pk,
                                                       workingset_history_id=workingset_history_id).created


    # published versions
    published_historical_ids = list(
        PublishedWorkingset.objects.filter(workingset_id=pk, approval_status=2).values_list('workingset_history_id',
                                                                                            flat=True))

    # history
    history = get_history_table_data(request, pk)

    # attributes
    workingset_attributes = workingset['phenotypes_concepts_data']
    if workingset_attributes:
        for data in workingset_attributes:
            concept_id = db_utils.parse_ident(data["concept_id"])
            concept_version = db_utils.parse_ident(data["concept_version_id"])
            try:
                concept = Concept.history.get(id=concept_id, history_id=concept_version)
                data['concept_name'] = concept.name
            except:
                data['contept_name'] = 'Unknown'

    if PhenotypeWorkingset.objects.get(pk=pk).is_deleted == True:
        messages.info(request, "This Working Set has been deleted.")

    context = {
        'workingset': workingset,
        'workingset_type': workingset_type,
        'workingset_attributes': workingset_attributes,
        'tags': tags,
        'has_tags': has_tags,
        'collections': collections_tags,
        'has_collections': has_collections,
        'data_sources': data_sources,
        'user_can_edit': can_edit,  #can_edit,
        'user_can_restore':can_restore,
        'allowed_to_create': False,  # for now  #user_allowed_to_create,    # not settings.CLL_READ_ONLY,
        'user_can_export': user_can_export,
        'history': history,
        'live_ver_is_deleted': PhenotypeWorkingset.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'approval_status': approval_status,
        'publish_date': publish_date,
        'is_latest_version': is_latest_version,
        'is_latest_pending_version': is_latest_pending_version,
        'current_phenotype_history_id': int(workingset_history_id),
        'page_canonical_path': get_canonical_path_by_brand(request, PhenotypeWorkingset, pk, workingset_history_id),
        'q': db_utils.get_q_highlight(request, request.session.get('ph_workingset_search', '')),
        'force_highlight_result': ['0', '1'][db_utils.is_referred_from_search_page(request)]
    }

    return render(request, 'clinicalcode/phenotypeworkingset/detail_combined.html', context)


def get_history_table_data(request, pk):
    """"
        get history table data for the template
    """

    versions = PhenotypeWorkingset.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = workingset_db_utils.getHistoryPhenotypeWorkingset(v.history_id
                                                     , highlight_result=[False, True][
                db_utils.is_referred_from_search_page(request)]
                                                     , q_highlight=db_utils.get_q_highlight(request,
                                                                                            request.session.get(
                                                                                                'ph_workingset_search',
                                                                                                ''))
                                                     )

        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        ver['updated_by'] = None
        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(PhenotypeWorkingset, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedWorkingset.objects.get(workingset_id=ver['id'],
                                                                  workingset_history_id=ver['history_id'],
                                                                  approval_status=2).created
        else:
            ver['publish_date'] = None

        ver['approval_status'] = -1
        ver['approval_status_label'] = ''
        if PublishedWorkingset.objects.filter(workingset_id=ver['id'],
                                              workingset_history_id=ver['history_id']).exists():
            ver['approval_status'] = PublishedWorkingset.objects.get(workingset_id=ver['id'], workingset_history_id=ver[
                'history_id']).approval_status
            ver['approval_status_label'] = APPROVED_STATUS[ver['approval_status']][1]

        if request.user.is_authenticated:
            if allowed_to_edit(request, PhenotypeWorkingset, pk) or allowed_to_view(request, PhenotypeWorkingset, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)

    return historical_versions


class WorkingSetPublish(LoginRequiredMixin, HasAccessToEditPhenotypeWorkingsetCheckMixin, TemplateResponseMixin, View):
    '''
        Publish the current working set.
    '''

    model = PhenotypeWorkingset
    template_name = 'clinicalcode/phenotypeworkingset/publish.html'

    pass





class WorkingSetUpdate(LoginRequiredMixin, HasAccessToEditPhenotypeWorkingsetCheckMixin, UpdateView):
    '''
        Update the current working set.
    '''

    model = PhenotypeWorkingset
    form_class = WorkingsetForm
    success_url = reverse_lazy('phenotypeworkingsets_list')
    template_name = 'clinicalcode/phenotypeworkingset/form.html'

    confirm_overrideVersion = 0
    errors_dict = {}
    is_valid1 = True

    def get_form_kwargs(self):
        kwargs = super(UpdateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def get_success_url(self):
        return reverse('phenotypeworkingset_update', args=(self.object.id,))

    def form_valid(self, form):
        # ----------------------------------------------------------
        # alert user when concurrent editing of workingset
        latest_history_id = str(self.object.history.latest().history_id)
        latest_history_id_shown = str(self.request.POST.get('latest_history_id'))
        overrideVersion = self.request.POST.get('overrideVersion')

        self.confirm_overrideVersion = 0
        if latest_history_id_shown != latest_history_id and str(overrideVersion) == "0":
            self.confirm_overrideVersion = -1
            self.is_valid1 = False
            form.is_valid = self.is_valid1
            return self.form_invalid(form)
            # return HttpResponseRedirect(self.get_context_data(**kwargs))
        # ----------------------------------------------------------

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            form.instance.modified = datetime.datetime.now()
            form.instance.created_by = self.request.user
            form.instance.author = self.request.POST.get('author')
            form.instance.tags = commaSeparate(self.request.POST.get('tagids'))
            form.instance.collections = commaSeparate(self.request.POST.get('collections'))
            form.instance.data_sources = commaSeparate(self.request.POST.get('datasources'))
            form.instance.phenotypes_concepts_data = json.loads(self.request.POST.get('workingset_data') or '[]')
            form.instance.publications = json.loads(self.request.POST.get('publication_data') or '[]')

            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset, self.kwargs['pk'], "Updated")
            # Get all the 'parent' concepts i.e. those that include this one,
            # and add a history entry to those that this concept has been
            # updated.

            messages.success(self.request, "Workingset has been successfully updated.")

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)

        tags = Tag.objects.filter(pk=-1)
        workigset_tags = self.get_object().tags
        workigset_publications = self.get_object().publications
        workingset_collections = self.get_object().collections
        workingset_datasources = self.get_object().data_sources

        if workigset_tags:
            tags = Tag.objects.filter(pk__in=workigset_tags)

        if workingset_collections:
            queryset = Tag.objects.filter(tag_type=2)
            workingset_collections = queryset.filter(id__in=workingset_collections)

        if workingset_datasources:
            workingset_datasources = DataSource.objects.filter(datasource_id__in=workingset_datasources)

        workingset_data = self.get_object().phenotypes_concepts_data
        if workingset_data:
            for data in workingset_data:
                concept_id = db_utils.parse_ident(data["concept_id"])
                concept_version = db_utils.parse_ident(data["concept_version_id"])
                phenotype_version = db_utils.parse_ident(data["phenotype_version_id"])
                try:
                    concept = Concept.history.get(id=concept_id, history_id=concept_version)
                    phenotype = Phenotype.history.get(id=data["phenotype_id"], history_id=phenotype_version)
                    data['phenotype_name'] = phenotype.name
                    data['concept_name'] = concept.name
                    data['concept_coding'] = concept.coding_system.name
                except Exception:
                    data['concept_name'] = 'Unknown'

        if self.get_object().is_deleted == True:
            messages.info(self.request, "This workingset has been deleted.")



        context['tags'] = tags
        context['datasources'] = workingset_datasources
        context['collections'] = workingset_collections
        context['publications'] = workigset_publications
        context['workingset_data'] = workingset_data
        context['allowed_to_permit'] = allowed_to_permit(self.request.user, PhenotypeWorkingset, self.get_object().id)


        context['overrideVersion'] = self.confirm_overrideVersion
        context['history'] = self.get_object().history.all()
        latest_history_id = context['phenotypeworkingset'].history.first().history_id
        context['latest_history_id'] = latest_history_id if self.request.POST.get(
            'latest_history_id') is None else self.request.POST.get('latest_history_id')

        context['current_workingset_history_id'] = int(latest_history_id)
        context['is_published'] = PublishedWorkingset.objects.filter(workingset_id=self.get_object().id,
                                                                     workingset_history_id=context[
                                                                         'latest_history_id']).exists()

        return context


class WorkingSetDelete(LoginRequiredMixin, HasAccessToEditPhenotypeWorkingsetCheckMixin, TemplateResponseMixin, View):
    '''
           Delete a workingset.
       '''
    model = PhenotypeWorkingset
    success_url = reverse_lazy('phenotypeworkingsets_list')
    template_name = 'clinicalcode/phenotypeworkingset/delete.html'

    def get_success_url(self):
        return reverse_lazy('phenotypeworkingsets_list')

    def get(self, request, pk):
        workingset = PhenotypeWorkingset.objects.get(pk=pk)

        return self.render_to_response({'pk': pk, 'name': workingset.name})

    def post(self, request, pk):
        with transaction.atomic():
            workingset_db_utils.deletePhenotypeWorkingset(pk, request.user)
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset, pk, "Workingset has been deleted")
        messages.success(self.request, "Workingset has been successfully deleted.")
        return HttpResponseRedirect(self.get_success_url())


class WorkingSetRestore(LoginRequiredMixin, HasAccessToEditPhenotypeWorkingsetCheckMixin, TemplateResponseMixin, View):
    '''
        Restore a deleted working set.
    '''

    model = PhenotypeWorkingset
    success_url = reverse_lazy('phenotypeworkingsets_list')
    template_name = 'clinicalcode/phenotypeworkingset/restore.html'

    def get_success_url(self):
        return reverse_lazy('phenotypeworkingsets_list')

    def get(self, request, pk):
        workingset = PhenotypeWorkingset.objects.get(pk=pk)
        return self.render_to_response({'pk': pk, 'name': workingset.name})

    def post(self, request, pk):
        with transaction.atomic():
            workingset_db_utils.restorePhenotypeWorkingset(pk, request.user)
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset, pk, "Workingset has been restored")
        messages.success(self.request, "Workingset has been successfully restored.")
        return HttpResponseRedirect(self.get_success_url())

@login_required
def workingset_history_revert(request, pk, concept_history_id):
    ''' 
        Revert a previously saved working set from the history.
    '''
    pass
    # look at concept equivalent


def history_workingset_codes_to_csv(request, pk, workingset_history_id=None):
    '''
        Return a csv file of codes for a working set for a specific historical version.
    '''

    if workingset_history_id is None:
        # get the latest version
        workingset_history_id = PhenotypeWorkingset.objects.get(pk=pk).history.latest().history_id

    # validate access for login and public site
    validate_access_to_view(request,
                            PhenotypeWorkingset,
                            pk,
                            set_history_id=workingset_history_id)

    is_published = checkIfPublished(PhenotypeWorkingset, pk, workingset_history_id)

    # ----------------------------------------------------------------------

    # exclude(is_deleted=True)
    if PhenotypeWorkingset.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # exclude(is_deleted=True)
    if PhenotypeWorkingset.history.filter(id=pk, history_id=workingset_history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # here, check live version
    current_ws = PhenotypeWorkingset.objects.get(pk=pk)

    if not is_published:
        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request,
                                                                                                      PhenotypeWorkingset,
                                                                                                      pk,
                                                                                                      set_history_id=workingset_history_id)
        if not children_permitted_and_not_deleted:
            raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied

    current_ws_version = PhenotypeWorkingset.history.get(id=pk, history_id=workingset_history_id)

    phenotypes_concepts_data = current_ws_version.phenotypes_concepts_data

    my_params = {
        'workingset_id': pk,
        'workingset_history_id': workingset_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
            'attachment; filename="workingset_%(workingset_id)s_ver_%(workingset_history_id)s_codes_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    attributes_titles = []
    if phenotypes_concepts_data:
        attr_sample = phenotypes_concepts_data[0]["Attributes"]
        attributes_titles = [x["name"] + "(" + x["type"] + ")" for x in attr_sample]

    titles = (['code', 'description', 'coding_system']
              + ['concept_id', 'concept_version_id', 'concept_name']
              + ['phenotype_id', 'phenotype_version_id', 'phenotype_name']
              + ['workingset_id', 'workingset_version_id', 'workingset_name']
              + attributes_titles
              )

    writer.writerow(titles)

    for concept in phenotypes_concepts_data:
        concept_id = int(concept["concept_id"].replace("C", ""))
        concept_version_id = concept["concept_version_id"]
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name
        concept_name = Concept.history.get(id=concept_id, history_id=concept_version_id).name

        phenotype_id = concept["phenotype_id"]
        phenotype_version_id = concept["phenotype_version_id"]
        phenotype_name = Phenotype.history.get(id=phenotype_id, history_id=phenotype_version_id).name

        attributes_values = []
        if attributes_titles:
            attributes_values = [x["value"] for x in concept["Attributes"]]

        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        for cc in codes:
            rows_no += 1
            writer.writerow([
                                cc['code']
                                , cc['description'].encode('ascii', 'ignore').decode('ascii')
                                , concept_coding_system
                                , 'C' + str(concept_id)
                                , concept_version_id
                                , concept_name
                                , phenotype_id
                                , phenotype_version_id
                                , phenotype_name
                                , current_ws_version.id
                                , current_ws_version.history_id
                                , current_ws_version.name
                            ]
                            + attributes_values
                            )

        if rows_no == 0:
            writer.writerow([
                                ''
                                , ''
                                , concept_coding_system
                                , 'C' + str(concept_id)
                                , concept_version_id
                                , concept_name
                                , phenotype_id
                                , phenotype_version_id
                                , phenotype_name
                                , current_ws_version.id
                                , current_ws_version.history_id
                                , current_ws_version.name
                            ]
                            + attributes_values
                            )

    return response


@login_required
def workingset_conceptcodesByVersion(request,
                                     pk,
                                     workingset_history_id,
                                     target_concept_id=None,
                                     target_concept_history_id=None):
    '''
        Get the codes of the working set concepts
        for a specific version
        for a specific concept
        Parameters:     request    The request.
                        pk         The working set id.
                        workingset_history_id  The version id
                        target_concept_id
                        target_concept_history_id
        Returns:        data       Dict with the codes. 
    '''
    pass

    validate_access_to_view(request,
                            PhenotypeWorkingset,
                            pk,
                            set_history_id=workingset_history_id)

    current_phw = PhenotypeWorkingset.objects.get(pk=pk)

    if current_phw.is_deleted == True:
        raise PermissionDenied

    # --------------------------------------------------

    codes = workingset_db_utils.get_working_set_codes_by_version(request, pk, workingset_history_id, target_concept_id,
                                                      target_concept_history_id)

    data = dict()
    data['form_is_valid'] = True

    # Get the list of concepts in the workingset data
    groups = workingset_db_utils.getGroupOfConceptsByPhenotypeWorkingsetId_historical(pk, workingset_history_id)

    concept_codes_html = []
    for group in groups:
        concept_id = db_utils.parse_ident(group[0])
        concept_version_id = group[1]

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

        c_code_attribute_header = Concept.history.get(id=concept_id,
                                                      history_id=concept_version_id).code_attribute_header
        concept_codes_html.append({
            'concept_id': concept_id,
            'concept_version_id': concept_version_id,
            'c_codes_count': c_codes_count,
            'c_html': render_to_string(
                'clinicalcode/phenotypeworkingset/get_concept_codes.html', {
                    'codes': c_codes,
                    'code_attribute_header': c_code_attribute_header,
                    'showConcept': False,
                    'q': ['', request.session.get('phenotype_search', '')][request.GET.get('highlight', '0') == '1']
                })
        })

    data['headers'] = c_code_attribute_header
    data['concept_codes_html'] = concept_codes_html

    return JsonResponse(data)
