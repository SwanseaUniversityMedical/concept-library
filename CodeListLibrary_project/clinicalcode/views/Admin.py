import time
import datetime

from clinicalcode.api.views.Concept import published_concepts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import \
    LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction  # , models, IntegrityError
from django.http import \
    HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
#from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView  # , DeleteView
from simple_history.models import HistoricalRecords

from .. import db_utils, utils, tasks
#from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models import *
from ..permissions import *
from .View import *

logger = logging.getLogger(__name__)

import json
import os

from django.core.exceptions import PermissionDenied
from django.db import connection, connections  # , transaction



def run_statistics(request):

    """
        save HDR-UK home page statistics
    """
    #     if not request.user.is_superuser:
    #         raise PermissionDenied

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        stat = save_statistics(request)
        return render(request, 'clinicalcode/admin/run_statistics.html', {
            'successMsg': ['HDR-UK statistics saved'],
            'stat': stat
        })


def save_statistics(request):
    stat = get_HDRUK_statistics(request)

    if Statistics.objects.all().filter(org__iexact='HDRUK',
                                       type__iexact='landing-page').exists():
        HDRUK_stat = Statistics.objects.get(org__iexact='HDRUK',
                                            type__iexact='landing-page')
        HDRUK_stat.stat = stat
        HDRUK_stat.updated_by = [None,
                                 request.user][request.user.is_authenticated]
        HDRUK_stat.modified = datetime.datetime.now()
        HDRUK_stat.save()

        return [stat, HDRUK_stat.id]
    else:
        obj, created = Statistics.objects.get_or_create(
            org='HDRUK',
            type='landing-page',
            stat=stat,
            created_by=[None, request.user][request.user.is_authenticated])

        return [stat, obj.id]


def get_HDRUK_statistics(request):
    '''
        get HDRUK statistics for display in the HDR UK homepage.
    '''

    HDRUK_brand_collection_ids = db_utils.get_brand_collection_ids('HDRUK')
    HDRUK_brand_collection_ids = [str(i) for i in HDRUK_brand_collection_ids]

    HDRUK_published_concepts = db_utils.get_visible_live_or_published_concept_versions(
        request,
        get_live_and_or_published_ver=
        2  # 1= live only, 2= published only, 3= live+published 
        ,
        exclude_deleted=True,
        show_top_version_only=False,
        force_brand='HDRUK',
        force_get_live_and_or_published_ver=2  # get published data
    )

    HDRUK_published_concepts_ids = db_utils.get_list_of_visible_entity_ids(
        HDRUK_published_concepts, return_id_or_history_id="id")

    HDRUK_published_concepts_id_version = db_utils.get_list_of_visible_entity_ids(
        HDRUK_published_concepts, return_id_or_history_id="both")

    #--------------------------

    HDRUK_published_phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(
        request,
        get_live_and_or_published_ver=
        2  # 1= live only, 2= published only, 3= live+published
        ,
        exclude_deleted=True,
        show_top_version_only=False,
        force_brand='HDRUK',
        force_get_live_and_or_published_ver=2  # get published data
    )


    HDRUK_published_phenotypes_ids = db_utils.get_list_of_visible_entity_ids(
        HDRUK_published_phenotypes, return_id_or_history_id="id")



    return {
        # ONLY PUBLISHED COUNTS HERE (count original entity, not versions)
        'published_concept_count':
        len(
            HDRUK_published_concepts_ids
        ),  
        'published_phenotype_count':
        len(
            HDRUK_published_phenotypes_ids
        ),  
        'published_clinical_codes':
        get_published_clinical_codes(HDRUK_published_concepts_id_version),
        'datasources_component_count':
        get_dataSources_count(HDRUK_published_phenotypes_ids
                              ),  #    DataSource.objects.all().count(),
        'clinical_terminologies':
        get_codingSystems_count(
            HDRUK_published_phenotypes
        )  # number of coding systems used in published phenotypes

    }







def get_codingSystems_count(published_phenotypes):
    """
        get only coding systems count used in (published) phenotypes
    """

    coding_systems_ids = []

    for p in published_phenotypes:
        if p['clinical_terminologies'] is not None:
            coding_systems_ids = list(
                set(coding_systems_ids + p['clinical_terminologies']))

    unique_coding_systems_ids = list(set(coding_systems_ids))
    # make sure coding system exists
    unique_coding_systems_ids_list = list(
        CodingSystem.objects.filter(
            id__in=unique_coding_systems_ids).values_list('id', flat=True))

    return len(unique_coding_systems_ids_list)


def get_dataSources_count(published_phenotypes_ids):
    """
        get only data-sources count used in (published) phenotypes
    """

    ds_ids = PhenotypeDataSourceMap.objects.filter(
        phenotype_id__in=published_phenotypes_ids).values(
            'datasource_id').distinct()

    unique_ds_ids = list(set([i['datasource_id'] for i in ds_ids]))
    # make sure data-source exists
    unique_ds_ids_list = list(
        DataSource.objects.filter(id__in=unique_ds_ids).values_list('id',
                                                                    flat=True))

    return len(unique_ds_ids_list)


def get_published_clinical_codes(published_concepts_id_version):
    """
        count (none distinct) the clinical codes 
        in published concepts and phenotypes
        (using directly published concepts of HDRUK
    """

    count = 0

    # count codes in published concepts
    # (to publish a phenotype you need to publish its concepts first)
    # so this count will also include any code in published phenotypes as well.

    #published_concepts_id_version = PublishedConcept.objects.values_list('concept_id' , 'concept_history_id')
    for c in published_concepts_id_version:
        #codecount = len(db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id = c[0], concept_history_id = c[1]))
        codecount = get_published_concept_codecount(concept_id=c[0],
                                                    concept_history_id=c[1])
        count = count + codecount

    return count


def get_published_concept_codecount(concept_id, concept_history_id):
    """
        return the code count of a published concept version.
        will save this count in PublishedConcept table if not already so.
    """

    codecount = 0

    published_concept = PublishedConcept.objects.get(
        concept_id=concept_id, concept_history_id=concept_history_id)
    saved_codecount = published_concept.code_count
    if saved_codecount is None or saved_codecount == '':
        codecount = len(
            db_utils.getGroupOfCodesByConceptId_HISTORICAL(
                concept_id=concept_id, concept_history_id=concept_history_id))
        published_concept.code_count = codecount
        published_concept.save()
        return codecount
    else:
        return saved_codecount


def run_statistics_collections(request):
    """
        save collection stat for brands (phenotypes/concepts)
    """
    brands = Brand.objects.all()
    brand_list = list(brands.values_list('name', flat=True))

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        for brand in brand_list:
            save_statistics_collections(request, 'concept', brand)
            save_statistics_collections(request, 'phenotype', brand)

        # save for all data
        save_statistics_collections(request, 'concept', brand='ALL')
        save_statistics_collections(request, 'phenotype', brand='ALL')

    return render(request, 'clinicalcode/admin/run_statistics.html', {
        'successMsg': ['Collections for concepts/Phenotypes statistics saved'],
    })


def save_statistics_collections(request, concept_or_phenotype, brand):
    """
        Function to insert statistics to the table clinicalcode_statistics.
        This will include the number of collections associated with each brand for phenotypes/concepts.
    """

    if concept_or_phenotype == 'concept':
        concept_stat = get_brand_collections(request,
                                             'concept',
                                             force_brand=brand)

        if Statistics.objects.all().filter(
                org__iexact=brand,
                type__iexact='concept_collections').exists():
            concept_stat_update = Statistics.objects.get(
                org__iexact=brand, type__iexact='concept_collections')
            concept_stat_update.stat = concept_stat
            concept_stat_update.updated_by = [None, request.user
                                              ][request.user.is_authenticated]
            concept_stat_update.modified = datetime.datetime.now()
            concept_stat_update.save()
            return [concept_stat, concept_stat_update.id]
        else:
            obj, created = Statistics.objects.get_or_create(
                org=brand,
                type='concept_collections',
                stat=concept_stat,
                created_by=[None, request.user][request.user.is_authenticated])
            return [concept_stat, obj.id]

    else:
        if concept_or_phenotype == 'phenotype':
            phenotype_stat = get_brand_collections(request,
                                                   'phenotype',
                                                   force_brand=brand)

            if Statistics.objects.all().filter(
                    org__iexact=brand,
                    type__iexact='phenotype_collections').exists():
                phenotype_stat_update = Statistics.objects.get(
                    org__iexact=brand, type__iexact='phenotype_collections')
                phenotype_stat_update.stat = phenotype_stat
                phenotype_stat_update.updated_by = [
                    None, request.user
                ][request.user.is_authenticated]
                phenotype_stat_update.modified = datetime.datetime.now()
                phenotype_stat_update.save()
                return [phenotype_stat, phenotype_stat_update.id]
            else:
                obj, created = Statistics.objects.get_or_create(
                    org=brand,
                    type='phenotype_collections',
                    stat=phenotype_stat,
                    created_by=[None,
                                request.user][request.user.is_authenticated])
                return [phenotype_stat, obj.id]


def get_brand_collections(request, concept_or_phenotype, force_brand=None):
    """
        For each brand this function will add a new row to the table "Statistics" which will list all of the
        collection IDs in a dictionary for when they are listed as published or not.
    """

    if force_brand == 'ALL':
        force_brand = ''

    if concept_or_phenotype == 'concept':
        # to be shown with login
        data = db_utils.get_visible_live_or_published_concept_versions(
            request,
            get_live_and_or_published_ver=
            3  # 1= live only, 2= published only, 3= live+published 
            ,
            exclude_deleted=False,
            force_brand=force_brand,
            force_get_live_and_or_published_ver=3  # get live + published data
        )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_concept_versions(
            request,
            get_live_and_or_published_ver=
            2  # 1= live only, 2= published only, 3= live+published 
            ,
            exclude_deleted=True,
            force_brand=force_brand,
            force_get_live_and_or_published_ver=2  # get published data
        )
    elif concept_or_phenotype == 'phenotype':
        # to be shown with login
        data = db_utils.get_visible_live_or_published_phenotype_versions(
            request,
            get_live_and_or_published_ver=
            3  # 1= live only, 2= published only, 3= live+published 
            ,
            exclude_deleted=False,
            force_brand=force_brand,
            force_get_live_and_or_published_ver=3  # get live + published data
        )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_phenotype_versions(
            request,
            get_live_and_or_published_ver=
            2  # 1= live only, 2= published only, 3= live+published 
            ,
            exclude_deleted=True,
            force_brand=force_brand,
            force_get_live_and_or_published_ver=2  # get published data
        )

    # Creation of two lists, one for all data and the other for published data
    Tag_List = []
    Tag_List_Published = []

    for i in data:
        if i['tags'] is not None:
            Tag_List = list(set(Tag_List + i['tags']))

    for i in data_published:
        if i['tags'] is not None:
            Tag_List_Published = list(set(Tag_List_Published + i['tags']))

    # Create a list for both allData and published.
    unique_tags_ids = list(set(Tag_List))
    unique_tags_ids_list = list(
        Tag.objects.filter(id__in=unique_tags_ids,
                           tag_type=2).values_list('id', flat=True))

    unique_tags_ids_published = list(set(Tag_List_Published))
    unique_tags_ids_published_list = list(
        Tag.objects.filter(id__in=unique_tags_ids_published,
                           tag_type=2).values_list('id', flat=True))

    # Create two distinct dictionaries for both allData and published
    StatsDict_Published = {}
    StatsDict = {}

    StatsDict_Published['Data_Scope'] = 'published_data'
    StatsDict_Published['Collection_IDs'] = unique_tags_ids_published_list

    StatsDict['Data_Scope'] = 'all_data'
    StatsDict['Collection_IDs'] = unique_tags_ids_list

    # Create list of the two created dictionaries above.
    StatsDictFinal = []
    StatsDictFinal.append(StatsDict.copy())
    StatsDictFinal.append(StatsDict_Published.copy())

    return StatsDictFinal
