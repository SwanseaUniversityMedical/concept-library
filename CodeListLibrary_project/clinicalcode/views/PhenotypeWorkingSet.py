
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
    ph_workingset_types_list, ph_workingset_types_order = db_utils.get_brand_associated_workingset_types(request, brand=None)
    ph_workingset_selected_types_list = {ph_workingset_types_order[k]: v for k, v in enumerate(ph_workingset_types_list)}
    
    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'PH' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^WS\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_int_id = db_utils.chk_valid_id(request, set_class=Phenotype, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id =" + str(ret_int_id) + " ) "

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

    workingset_srch = db_utils.get_visible_live_or_published_phenotype_workingset_versions(request,
                                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                                            search=[search, ''][search_by_id],
                                                                            author=author,
                                                                            exclude_deleted=exclude_deleted,
                                                                            filter_cond=filter_cond,
                                                                            approved_status=approved_status,
                                                                            show_top_version_only=show_top_version_only,
                                                                            search_name_only = False,
                                                                            highlight_result = True
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




class WorkingSetCreate(LoginRequiredMixin, HasAccessToCreateCheckMixin, MessageMixin, CreateView):
    model = PhenotypeWorkingset
    form_class = WorkingsetForm
    template_name = 'clinicalcode/phenotypeworkingset/form.html'

    def commaSeparate(self, id):
        data = self.request.POST.get(id)
        overall = None
        if data:
            overall = [int(i) for i in data.split(",")]

        return overall



    def get_form_kwargs(self):
        print('test kwarks ')
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def form_invalid(self, form):
        print('test form invalid ')
        tag_ids = self.commaSeparate('tagids')
        collections = self.commaSeparate('collections')
        datasources = self.commaSeparate('datasources')
        context = self.get_context_data()

        if tag_ids:
            context['tags'] = Tag.objects.filter(pk__in=tag_ids)
            print(context['tags'])

        if collections:
            queryset = Tag.objects.filter(tag_type=2)
            context['collections'] = queryset.filter(id__in=collections)
            print(context['collections'])

        if datasources:
            print(datasources)
            context['datasources'] = DataSource.objects.filter(datasource_id__in=datasources)


        return self.render_to_response(context)

    def form_valid(self, form):
        print('test form valid ')
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.author = self.request.POST.get('author')
            form.instance.tags = self.commaSeparate('tagids')
            form.instance.collections = self.commaSeparate('collections')
            form.instance.data_sources = self.commaSeparate('datasources')
            form.instance.phenotypes_concepts_data = [{"phenotype_id": "PH3","phenotype_version_id": 6,"concept_id": "C717","concept_version_id":2573,"Attributes":[{"name": "Attributename","type":"int","value": 234}]}]


            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset,self.object.pk,"Created")
            print(self.object.pk)
            messages.success(self.request,"Workingset has been successfully created.")

        return HttpResponseRedirect(reverse('phenotypeworkingset_create'))
        # return HttpResponseRedirect(reverse('workingset_update'),args=(self.object.pk)) when update is done


@login_required
def phenotype_workingset_DB_test_create(request):
    '''
        temp create test DB ws
    '''
    if not request.user.is_superuser:
        raise PermissionDenied
    
    import random
    
    test_workingset = PhenotypeWorkingset.objects.create(
            name = "wokringset test #" + str(random.random()*1000000),
            type = random.choice(Type_status)[0],
            tags = random.sample(list(Tag.objects.filter(tag_type=1).values_list('id',  flat=True)), 1),
            collections = random.sample(list(Tag.objects.filter(tag_type=2).values_list('id',  flat=True)), 2),
            publications = ["paper no 1", "paper no 2", "paper no 3"],
            author = "me, others, wolrd",
            citation_requirements = "citation requirements",
            description = "description description description",
            data_sources = random.sample(list(DataSource.objects.values_list('id',  flat=True)), 2),
            phenotypes_concepts_data =  [
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
                                            "phenotype_id": "PH3",
                                            "phenotype_version_id": 6,
                                            "concept_id": "C717",
                                            "concept_version_id": 2573,
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


            created_by = request.user,
            updated_by = request.user,
            owner = request.user,
            
            group = Group.objects.get(id=5),
            group_access = Permissions.VIEW,
            owner_access = Permissions.VIEW,
            world_access = Permissions.VIEW
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
    pass
    # look at phenotype equivalent



class WorkingSetUpdate(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, UpdateView):
    '''
        Update the current working set.
    '''
    pass
    # look at concept equivalent
    
    
class WorkingSetDelete(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, TemplateResponseMixin, View):
    '''
        Delete a working set.
    '''
    pass
    # look at concept equivalent


class WorkingSetRestore(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, TemplateResponseMixin, View):
    '''
        Restore a deleted working set.
    '''
    pass
    # look at concept equivalent

    
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
    response['Content-Disposition'] = ('attachment; filename="workingset_%(workingset_id)s_ver_%(workingset_history_id)s_codes_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)
    
    
    attributes_titles = []
    if phenotypes_concepts_data:
        attr_sample = phenotypes_concepts_data[0]["Attributes"]
        attributes_titles = [x["name"] for x in attr_sample]

    titles = (    ['code', 'description', 'coding_system']
                + ['concept_id', 'concept_version_id' , 'concept_name']
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
              
        phenotype_id = int(concept["phenotype_id"].replace("PH", ""))
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
                , 'PH' + str(phenotype_id)
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
                , 'PH' + str(phenotype_id)
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
    # look at phenotype equivalent
    

