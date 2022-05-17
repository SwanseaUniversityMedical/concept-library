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

# from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def phenotype_list(request):
    '''
        Display the list of phenotypes. This view can be searched and contains paging.
    '''

    search_tag_list = []
    tags = []

    # get page index variables from query or from session
    expand_published_versions = 0  # disable this option
        
    page_size = utils.get_int_value(request.GET.get('page_size', request.session.get('phenotype_page_size', 20)), 20)
    page = utils.get_int_value(request.GET.get('page', request.session.get('phenotype_page', 1)), 1)
    search = request.GET.get('search', request.session.get('phenotype_search', ''))
    tag_ids = request.GET.get('tagids', request.session.get('phenotype_tagids', ''))
    owner = request.GET.get('owner', request.session.get('phenotype_owner', ''))
    author = request.GET.get('author', request.session.get('phenotype_author', ''))
    phenotype_brand = request.GET.get('phenotype_brand', request.session.get('phenotype_brand', ''))  # request.CURRENT_BRAND
    
    show_deleted_phenotypes = request.GET.get('show_deleted_phenotypes', request.session.get('phenotype_show_deleted_phenotypes', 0))
    show_my_phenotypes = request.GET.get('show_my_phenotypes', request.session.get('phenotype_show_my_phenotype', 0))
    show_only_validated_phenotypes = request.GET.get('show_only_validated_phenotypes', request.session.get('show_only_validated_phenotypes', 0))
    phenotype_must_have_published_versions = request.GET.get('phenotype_must_have_published_versions', request.session.get('phenotype_must_have_published_versions', 0))

    show_my_pending_phenotypes = request.GET.get('show_my_pending_phenotypes', request.session.get('phenotype_show_my_pending_phenotype', 0))
    show_mod_pending_phenotypes = request.GET.get('show_mod_pending_phenotypes', request.session.get('phenotype_show_mod_pending_phenotype', 0))
   
    search_form = request.GET.get('search_form', request.session.get('phenotype_search_form', 'basic-form'))


    if bool(request.GET):
        # get posted parameters
        search = request.GET.get('search', '')
        page_size = request.GET.get('page_size', 20)
        page = request.GET.get('page', page)     
        tag_ids = request.GET.get('tagids', '')
        phenotype_brand = request.GET.get('phenotype_brand', '')  # request.CURRENT_BRAND
        search_form = request.GET.get('search_form', 'basic-form')
        
        if search_form !='basic-form': 
            author = request.GET.get('author', '')
            owner = request.GET.get('owner', '')
            show_my_phenotypes = request.GET.get('show_my_phenotypes', 0)
            show_deleted_phenotypes = request.GET.get('show_deleted_phenotypes', 0)
            show_only_validated_phenotypes = request.GET.get('show_only_validated_phenotypes', 0)
            phenotype_must_have_published_versions = request.GET.get('phenotype_must_have_published_versions', 0)
            show_my_pending_phenotypes = request.GET.get('show_my_pending_phenotypes', 0)
            show_mod_pending_phenotypes = request.GET.get('show_mod_pending_phenotypes', 0)
        
        
    # store page index variables to session
    request.session['phenotype_page_size'] = page_size
    request.session['phenotype_page'] = page
    request.session['phenotype_search'] = search  
    request.session['phenotype_tagids'] = tag_ids
    request.session['phenotype_brand'] = phenotype_brand   
   
   #if search_form !='basic-form': 
    request.session['phenotype_author'] = author  
    request.session['phenotype_owner'] = owner     
    request.session['phenotype_show_my_phenotype'] = show_my_phenotypes
    request.session['phenotype_show_mod_pending_phenotype'] = show_mod_pending_phenotypes
    request.session['phenotype_show_deleted_phenotypes'] = show_deleted_phenotypes
    request.session['show_only_validated_phenotypes'] = show_only_validated_phenotypes
    request.session['phenotype_show_pending_phenotype'] = show_my_pending_phenotypes
    request.session['phenotype_must_have_published_versions'] = phenotype_must_have_published_versions
    
    request.session['phenotype_search_form'] = search_form
    
    if search_form == 'basic-form':     
        owner = '' 
        author = ''
        show_my_phenotypes = 0
        show_deleted_phenotypes = 0
        show_only_validated_phenotypes = 0
        phenotype_must_have_published_versions = 0
        show_my_pending_phenotypes = 0
        show_mod_pending_phenotypes = 0
            

    # remove leading and trailing spaces from text search params
    search = search.strip()
    owner = owner.strip()
    author = author.strip()
    
        
    filter_cond = " 1=1 "
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published

    if tag_ids:
        # split tag ids into list
        search_tag_list = [str(i) for i in tag_ids.split(",")]
        tags = Tag.objects.filter(id__in=search_tag_list)
        filter_cond += " AND tags && '{" + ','.join(search_tag_list) + "}' "

    # check if it is the public site or not
    if request.user.is_authenticated:
        # ensure that user is only allowed to view/edit the relevant phenotype

        get_live_and_or_published_ver = 3
        if phenotype_must_have_published_versions == "1":
            get_live_and_or_published_ver = 2

        # show only phenotype created by the current user
        if show_my_phenotypes == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)

        if show_my_pending_phenotypes == "1":
            filter_cond += " AND is_approved=1"
            filter_cond += " AND owner_id=" + str(request.user.id)

        if show_mod_pending_phenotypes == "1":
            filter_cond += " AND is_approved=1"

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

    phenotype_srch = db_utils.get_visible_live_or_published_phenotype_versions(
                                                                                request,
                                                                                get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                                                searchByName=search,
                                                                                author=author,
                                                                                exclude_deleted=exclude_deleted,
                                                                                filter_cond=filter_cond,
                                                                                show_top_version_only=show_top_version_only)
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
        tag_ids_list = [int(t) for t in tag_ids.split(',')]

    brand_associated_collections = db_utils.get_brand_associated_collections(request, concept_or_phenotype='phenotype')
    brand_associated_collections_ids = list(brand_associated_collections.values_list('id', flat=True))

    author = request.session.get('phenotype_author')  
    owner = request.session.get('phenotype_owner')       
    show_my_phenotypes = request.session.get('phenotype_show_my_phenotype')
    show_mod_pending_phenotypes = request.session.get('phenotype_show_mod_pending_phenotype')
    show_deleted_phenotypes = request.session.get('phenotype_show_deleted_phenotypes')
    show_only_validated_phenotypes = request.session.get('show_only_validated_phenotypes') 
    show_my_pending_phenotypes = request.session.get('phenotype_show_pending_phenotype') 
    phenotype_must_have_published_versions = request.session.get('phenotype_must_have_published_versions') 
    
    return render(
        request,
        'clinicalcode/phenotype/index.html',
        {
            'page': page,
            'page_size': str(page_size),
            'page_obj': p,
            'search': search,
            'author': author,
            'show_my_phenotypes': show_my_phenotypes,
            'show_deleted_phenotypes': show_deleted_phenotypes,
            'show_my_pending_phenotypes': show_my_pending_phenotypes,
            'show_mod_pending_phenotypes': show_mod_pending_phenotypes,
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
            'all_collections_selected': all(item in tag_ids_list for item in brand_associated_collections_ids)

        })


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
    is_approved = checkIfapproved(Phenotype, pk, phenotype_history_id)

    # ----------------------------------------------------------------------

    phenotype = db_utils.getHistoryPhenotype(phenotype_history_id)
    # The history phenotype contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the phenotype.
    if phenotype['owner_id'] is not None:
        phenotype['owner'] = User.objects.get(id=int(phenotype['owner_id']))

    if phenotype['group_id'] is not None:
        phenotype['group'] = Group.objects.get(id=int(phenotype['group_id']))

    phenotype_history_date = phenotype['history_date']

    tags = Tag.objects.filter(pk=-1)
    phenotype_tags = phenotype['tags']
    if phenotype_tags:
        tags = Tag.objects.filter(pk__in=phenotype_tags)

    data_sources = DataSource.objects.filter(pk=-1)
    data_sources_comp = db_utils.getHistoryDataSource_Phenotype(pk, phenotype_history_date)
    if data_sources_comp:
        ds_list = [i['datasource_id'] for i in data_sources_comp if 'datasource_id' in i]
        data_sources = DataSource.objects.filter(pk__in=ds_list)

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
    is_latest_pending_version = None

    if len(PublishedPhenotype.objects.filter(phenotype_id=pk)) > 0:
        is_latest_pending_version = (int(phenotype_history_id) == PublishedPhenotype.objects.filter(phenotype_id=pk).first().phenotype_history_id)
        print(is_latest_pending_version)


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
    published_historical_ids = list(PublishedPhenotype.objects.filter(phenotype_id=pk, is_approved=2).values_list('phenotype_history_id', flat=True))

    # history
    other_versions = Phenotype.objects.get(pk=pk).history.all()
    other_historical_versions = []

    for ov in other_versions:
        ver = db_utils.getHistoryPhenotype(ov.history_id)
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(Phenotype, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedPhenotype.objects.get(phenotype_id=ver['id'], phenotype_history_id=ver['history_id'], is_approved=2).created
        else:
            ver['publish_date'] = None

        if request.user.is_authenticated:
            if allowed_to_edit(request, Phenotype, pk) or allowed_to_view(request, Phenotype, pk):
                other_historical_versions.append(ver)
            else:
                if is_this_version_published:
                    other_historical_versions.append(ver)
        else:
            if is_this_version_published:
                other_historical_versions.append(ver)

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
        'history': other_historical_versions,
        'live_ver_is_deleted': Phenotype.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'is_approved': is_approved,
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
        'page_canonical_path': get_canonical_path_by_brand(request, Phenotype, pk, phenotype_history_id)                              
    }

    return render(request, 
                  'clinicalcode/phenotype/detail_combined.html',
                  context)


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

    # codes_count = "0"
    # try:
    #     codes_count = str(len(codes))
    # except:
    #     codes_count = "0"
    # data['codes_count'] = codes_count
    # data['html_uniquecodes_list'] = render_to_string(
    #                                                 'clinicalcode/phenotype/get_concept_codes.html',
    #                                                 {'codes': codes,
    #                                                 'showConcept': True
    #                                                 }
    #                                                 )

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
                                            'showConcept': False
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


def history_phenotype_codes_to_csv(request, pk, phenotype_history_id):
    """
        Return a csv file of codes for a phenotype for a specific historical version.
    """
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

        if len(PublishedPhenotype.objects.filter(phenotype_id=pk)) > 0:
            is_latest_pending_version = (int(phenotype_history_id) == PublishedPhenotype.objects.filter(
                phenotype_id=pk).first().phenotype_history_id)

        if (len(db_utils.get_phenotype_conceptcodesByVersion(self.request, pk, phenotype_history_id)) == 0):
            allow_to_publish = False
            phenotype_has_codes = False

        has_child_concepts, isOK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors = checkAllChildConcepts4Publish_Historical(request, pk, phenotype_history_id)
        if not isOK:
            allow_to_publish = False

    def get(self, request, pk, phenotype_history_id):
        global errors, allow_to_publish, phenotype_is_deleted, is_owner, is_approved, is_moderator,is_latest_pending_version
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
        is_approved = checkIfapproved(Phenotype, pk, phenotype_history_id)

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
            'is_approved': is_approved,
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
        global errors, allow_to_publish, phenotype_is_deleted, is_owner, phenotype_has_codes, is_approved, is_moderator,\
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
        is_approved = checkIfapproved(Phenotype, pk, phenotype_history_id)

        self.checkPhenotypeTobePublished(request, pk, phenotype_history_id)

        data = dict()

        submitValue = self.validate_request(request)



        if 'decline' == submitValue or (is_approved == 3 and is_moderator):
                return self.update_published(request,pk,phenotype_history_id,submitValue,is_latest_pending_version)

        elif 'publish' == submitValue:
            if not allow_to_publish or (is_published and is_approved == 2):

                data['form_is_valid'] = False
                data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)
                return JsonResponse(data)

            try:
                if (allow_to_publish and not is_published
                        and is_approved is None) or (is_approved == 2 and not is_published):
                    # start a transaction
                    with transaction.atomic():
                        if is_moderator:
                            phenotype = Phenotype.objects.get(pk=pk)
                            print("moder hui")


                            published_phenotype = PublishedPhenotype(
                                phenotype_id=phenotype.id,
                                phenotype_history_id=phenotype_history_id,is_approved = 2,
                                approved_by = request.user,created_by=Phenotype.objects.get(pk=pk).created_by)
                            published_phenotype.save()

                            data['is_approved'] = 2
                            data = self.form_validation(data,phenotype_history_id,pk,phenotype)

                        else:
                            if is_approved == 2:
                                print("user hui publ")
                                phenotype = Phenotype.objects.get(pk=pk)
                                published_phenotype = PublishedPhenotype.objects.filter(phenotype_id=phenotype.id).first()
                                published_phenotype_new = PublishedPhenotype(
                                    phenotype=phenotype,
                                    phenotype_history_id=phenotype_history_id,
                                    is_approved=2,
                                    approved_by = published_phenotype.approved_by,
                                    created_by=request.user)
                                published_phenotype_new.save()
                                data['is_approved'] = 2
                            else:
                                print("user hui not publ")
                                phenotype = Phenotype.objects.get(pk=pk)
                                published_phenotype = PublishedPhenotype(
                                    phenotype=phenotype,
                                    phenotype_history_id=phenotype_history_id,
                                    is_approved=1,
                                    created_by=request.user)
                                published_phenotype.save()
                                data['is_approved'] = 1

                            data = self.form_validation(data,phenotype_history_id,pk,phenotype)

                elif is_approved == 1 and is_moderator:
                    # start a transaction
                    with transaction.atomic():
                        print('moder hui to publ')
                        phenotype = Phenotype.objects.get(pk=pk)
                        published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype.id)
                        published_phenotype.phenotype_history_id = phenotype_history_id
                        published_phenotype.is_approved = 2
                        published_phenotype.approved_by = request.user
                        published_phenotype.created_by = PublishedPhenotype.objects.get(phenotype_id=phenotype.id).created_by
                        published_phenotype.save()

                        data['is_approved'] = 2
                        data = self.form_validation(data,phenotype_history_id,pk,phenotype)

                elif not is_latest_pending_version and not is_moderator:
                    with transaction.atomic():
                        print("is latest")
                        phenotype = Phenotype.objects.get(pk=pk)
                        published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype.id)
                        published_phenotype.phenotype_history_id = phenotype_history_id
                        published_phenotype.is_approved = 1
                        published_phenotype.created_by = PublishedPhenotype.objects.get(
                            phenotype_id=phenotype.id).created_by
                        published_phenotype.save()

                        data['is_approved'] = 1
                        data = self.form_validation(data, phenotype_history_id, pk, phenotype)




            except Exception as e:
                print(e)
                data['form_is_valid'] = False
                data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)

            return JsonResponse(data)

    def form_validation(self,data,phenotype_history_id,pk,phenotype):
        data['form_is_valid'] = True
        data['latest_history_ID'] = phenotype_history_id  # phenotype.history.latest().pk

        # update history list
        data['html_history_list'] = render_to_string(
            'clinicalcode/phenotype/partial_history_list.html',
            {
                'history': phenotype.history.all(),
                'current_phenotype_history_id': int(phenotype_history_id),  # phenotype.history.latest().pk,
                'published_historical_ids':
                    list(PublishedPhenotype.objects.filter(phenotype_id=pk,is_approved=2).values_list('phenotype_history_id',
                                                                                        flat=True))

            },
            request=self.request)

        data['message'] = self.send_message(
            pk, phenotype_history_id, data, phenotype,
            is_approved, is_moderator)['message']
        return data

    def send_message(self, pk, phenotype_history_id, data,phenotype, is_approved,is_moderator):
        if is_approved == 2:
            data['message'] = render_to_string(
                'clinicalcode/phenotype/published.html', {
                    'id': pk,
                    'phenotype_history_id': phenotype_history_id
                }, self.request)
            self.send_email_decision(phenotype,is_approved)
            return data

        elif is_approved == 1:
            data['message'] = render_to_string(
                'clinicalcode/phenotype/published.html', {
                    'id': pk,
                    'phenotype_history_id': phenotype_history_id
                }, self.request)
            self.send_email_decision(phenotype, is_approved)
            return data

        elif is_approved == 3:
            data['message'] = render_to_string(
                'clinicalcode/phenotype/declined.html', {
                    'id': pk,
                    'phenotype_history_id': phenotype_history_id
                }, self.request)
            self.send_email_decision(phenotype, is_approved)
            return data

        elif is_approved is None and is_moderator:
            data['message'] = render_to_string(
                'clinicalcode/phenotype/published.html', {
                    'id': pk,
                    'phenotype_history_id': phenotype_history_id
                }, self.request)
            return data

        elif is_approved is None:
            data['message'] = render_to_string(
                'clinicalcode/phenotype/approve.html', {
                    'id': pk,
                    'phenotype_history_id': phenotype_history_id
                }, self.request)
            return data

    def send_email_decision(self,phenotype,approved):

        if approved == 1:
           db_utils.send_review_email(phenotype,"Published",
                                      "Phenotype has been successfully approved and published on the website")

        elif approved == 2:
            # This line for the case when user want to get notification of same phenotype id but different version
           db_utils.send_review_email(phenotype,"Published",
                                      "Phenotype has been successfully approved and published on the website")
        elif approved == 3:
            db_utils.send_review_email(phenotype, "Rejected",
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
                if submitValue == "decline":

                    is_approved = 3
                    phenotype = Phenotype.objects.get(pk=pk)
                    published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype, phenotype_history_id=phenotype_history_id)
                    published_phenotype.is_approved = is_approved
                    published_phenotype.save()


                elif submitValue == "publish" and not is_latest_pending_version:

                    is_approved = 2
                    phenotype = Phenotype.objects.get(pk=pk)
                    published_phenotype = PublishedPhenotype.objects.filter(phenotype_id=phenotype.id).first()
                    published_phenotype.phenotype = phenotype
                    published_phenotype.phenotype_history_id = phenotype_history_id
                    published_phenotype.is_approved = 2
                    published_phenotype.approved_by = request.user
                    published_phenotype.created_by = Phenotype.objects.get(pk=pk).created_by
                    published_phenotype.save()

                elif submitValue == "publish":

                    is_approved = 2
                    phenotype = Phenotype.objects.get(pk=pk)
                    published_phenotype = PublishedPhenotype.objects.get(phenotype_id=phenotype, phenotype_history_id=phenotype_history_id)
                    published_phenotype.approved_by = request.user
                    published_phenotype.is_approved = is_approved
                    published_phenotype.save()




                data['form_is_valid'] = True
                data[
                    'latest_history_ID'] = phenotype_history_id  # phenotype.history.latest().pk
                data['is_approved'] = is_approved


                # update history list
                data['html_history_list'] = render_to_string(
                    'clinicalcode/phenotype/partial_history_list.html',
                    {
                        'history': phenotype.history.all(),
                        'current_phenotype_history_id':int(phenotype_history_id),  # phenotype.history.latest().pk,
                        'published_historical_ids': list(PublishedPhenotype.objects.filter(phenotype_id=pk,is_approved=is_approved).values_list('phenotype_history_id', flat=True))
                    },
                    request=self.request)

                data['message'] = self.send_message(pk, phenotype_history_id, data, phenotype, is_approved, is_moderator)['message']


        except Exception as e:
            data['form_is_valid'] = False
            print(e)
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

