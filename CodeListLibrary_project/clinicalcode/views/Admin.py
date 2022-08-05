import time
import datetime

from celery import shared_task

from clinicalcode.api.views.Concept import published_concepts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User, AnonymousUser
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction  # , models, IntegrityError
from django.http import HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
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
from django.test import RequestFactory
import csv
from django.db.models import Min, Max
from collections import Counter


##### Datasources
def get_hdruk_datasources():
    try:
        result = requests.get(
            'https://api.www.healthdatagateway.org/api/v2/datasets',
            proxies={
                'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
                'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/'
            }
        )
    except Exception as e:
        return {}, 'Unable to sync HDRUK datasources, failed to reach api'

    datasources = {}
    if result.status_code == 200:
        datasets = json.loads(result.content)['datasets']

        for dataset in datasets:
            if 'pid' in dataset and 'datasetv2' in dataset:
                dataset_name = dataset['datasetv2']['summary']['title'].strip()
                dataset_uid = dataset['pid'].strip()
                dataset_url = 'https://web.www.healthdatagateway.org/dataset/%s' % dataset_uid
                dataset_description = dataset['datasetv2']['summary']['abstract'].strip()

                datasources[dataset_uid] = {
                    'name': dataset_name if dataset_name != '' else dataset['datasetfields']['metadataquality']['title'].strip(),
                    'url': dataset_url,
                    'description': dataset_description
                }
    return datasources, None

def create_or_update_internal_datasources():
    hdruk_datasources, error_message = get_hdruk_datasources()
    if error_message:
        return error_message

    results = {
        'created': [],
        'updated': []
    }
    for uid, datasource in hdruk_datasources.items():
        try:
            internal_datasource = DataSource.objects.filter(Q(uid__iexact=uid) | Q(name__iexact=datasource['name']))
        except DataSource.DoesNotExist:
            internal_datasource = False
        
        if internal_datasource:
            for internal in internal_datasource:
                if internal.source == 'HDRUK':
                    update_uid = internal.uid != uid
                    update_name = internal.name != datasource['name']
                    update_url = internal.url != datasource['url']
                    update_description = internal.description != datasource['description'][:500]

                    if update_uid or update_name or update_url or update_description:
                        internal.uid = uid
                        internal.name = datasource['name']
                        internal.url = datasource['url']
                        internal.description = datasource['description']
                        internal.save()

                        results['updated'].append({
                            'uid': uid,
                            'name': datasource['name']
                        })
        else:
            new_datasource = DataSource()
            new_datasource.uid = uid
            new_datasource.name = datasource['name']
            new_datasource.url = datasource['url']
            new_datasource.description = datasource['description']
            new_datasource.source = 'HDRUK'
            new_datasource.save()

            new_datasource.datasource_id = new_datasource.id
            new_datasource.save()

            results['created'].append({
                'uid': uid,
                'name': datasource['name']
            })

    return results

def run_datasource_sync(request):
    if settings.CLL_READ_ONLY:
        raise PermissionDenied
    
    if request.method == 'GET':
        results = create_or_update_internal_datasources()
        
        message = {
            'successMsg': ['HDR-UK datasources synced'],
            'result': results
        }
        if isinstance(results, str):
            message = {
                'errorMsg': [results]
            }

        return render(
            request, 
            'clinicalcode/admin/run_datasource_sync.html', 
            message
        )

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
        return render(request, 'clinicalcode/admin/run_statistics.html', 
                    {
                        'successMsg': ['HDR-UK statistics saved'],
                        'stat': stat
                    })


def save_statistics(request):
    stat = get_HDRUK_statistics(request)

    if Statistics.objects.all().filter(org__iexact='HDRUK', type__iexact='landing-page').exists():
        HDRUK_stat = Statistics.objects.get(org__iexact='HDRUK', type__iexact='landing-page')
        HDRUK_stat.stat = stat
        HDRUK_stat.updated_by = [None, request.user][request.user.is_authenticated]
        HDRUK_stat.modified = datetime.datetime.now()
        HDRUK_stat.save()

        clear_statistics_history()
        return [stat, HDRUK_stat.id]
    else:
        obj, created = Statistics.objects.get_or_create(org='HDRUK',
                                                        type='landing-page',
                                                        stat=stat,
                                                        created_by=[None, request.user][request.user.is_authenticated]
                                                        )

        clear_statistics_history()
        return [stat, obj.id]


def get_HDRUK_statistics(request):
    '''
        get HDRUK statistics for display in the HDR UK homepage.
    '''

    HDRUK_brand_collection_ids = db_utils.get_brand_collection_ids('HDRUK')
    HDRUK_brand_collection_ids = [str(i) for i in HDRUK_brand_collection_ids]

    HDRUK_published_concepts = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                                        get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published
                                                                                        exclude_deleted=True,
                                                                                        show_top_version_only=False,
                                                                                        force_brand='HDRUK',
                                                                                        force_get_live_and_or_published_ver=2  # get published data
                                                                                    )

    HDRUK_published_concepts_ids = db_utils.get_list_of_visible_entity_ids(HDRUK_published_concepts, return_id_or_history_id="id")

    HDRUK_published_concepts_id_version = db_utils.get_list_of_visible_entity_ids(HDRUK_published_concepts, return_id_or_history_id="both")

    #--------------------------

    HDRUK_published_phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                                            get_live_and_or_published_ver=
                                                                                            2,  # 1= live only, 2= published only, 3= live+published
                                                                                            exclude_deleted=True,
                                                                                            show_top_version_only=False,
                                                                                            force_brand='HDRUK',
                                                                                            force_get_live_and_or_published_ver=2  # get published data
                                                                                        )


    HDRUK_published_phenotypes_ids = db_utils.get_list_of_visible_entity_ids(HDRUK_published_phenotypes, return_id_or_history_id="id")


    return {
        # ONLY PUBLISHED COUNTS HERE (count original entity, not versions)
        'published_concept_count': len(HDRUK_published_concepts_ids),
        'published_phenotype_count': len(HDRUK_published_phenotypes_ids),
        'published_clinical_codes': get_published_clinical_codes(HDRUK_published_concepts_id_version),
        'datasources_component_count': get_dataSources_count(HDRUK_published_phenotypes_ids),  
        'clinical_terminologies': get_codingSystems_count(HDRUK_published_phenotypes)  # number of coding systems used in published phenotypes
    }



def get_codingSystems_count(published_phenotypes):
    """
        get only coding systems count used in (published) phenotypes
    """

    coding_systems_ids = []

    for p in published_phenotypes:
        if p['clinical_terminologies'] is not None:
            coding_systems_ids = list(set(coding_systems_ids + p['clinical_terminologies']))

    unique_coding_systems_ids = list(set(coding_systems_ids))
    # make sure coding system exists
    unique_coding_systems_ids_list = list(CodingSystem.objects.filter(id__in=unique_coding_systems_ids).values_list('id', flat=True))

    return len(unique_coding_systems_ids_list)


def get_dataSources_count(published_phenotypes_ids):
    """
        get only data-sources count used in (published) phenotypes
    """

    ds_ids = PhenotypeDataSourceMap.objects.filter(phenotype_id__in=published_phenotypes_ids).values('datasource_id').distinct()

    unique_ds_ids = list(set([i['datasource_id'] for i in ds_ids]))
    # make sure data-source exists
    unique_ds_ids_list = list(DataSource.objects.filter(id__in=unique_ds_ids).values_list('id', flat=True))

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
        codecount = get_published_concept_codecount(concept_id=c[0], concept_history_id=c[1])
        count = count + codecount

    return count


def get_published_concept_codecount(concept_id, concept_history_id):
    """
        return the code count of a published concept version.
        will save this count in PublishedConcept table if not already so.
    """

    codecount = 0

    published_concept = PublishedConcept.objects.get(concept_id=concept_id, concept_history_id=concept_history_id)
    saved_codecount = published_concept.code_count
    if saved_codecount is None or saved_codecount == '':
        codecount = len(db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=concept_id, concept_history_id=concept_history_id))
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

    clear_statistics_history()
    
    return render(request, 'clinicalcode/admin/run_statistics.html',
                {
                    'successMsg': ['Collections for concepts/Phenotypes statistics saved'],
                })


def save_statistics_collections(request, concept_or_phenotype, brand):
    """
        Function to insert statistics to the table clinicalcode_statistics.
        This will include the number of collections associated with each brand for phenotypes/concepts.
    """

    if concept_or_phenotype == 'concept':
        concept_stat = get_brand_collections(request, 'concept', force_brand=brand)

        if Statistics.objects.all().filter(org__iexact=brand, type__iexact='concept_collections').exists():
            concept_stat_update = Statistics.objects.get(org__iexact=brand, type__iexact='concept_collections')
            concept_stat_update.stat = concept_stat
            concept_stat_update.updated_by = [None, request.user][request.user.is_authenticated]
            concept_stat_update.modified = datetime.datetime.now()
            concept_stat_update.save()
            return [concept_stat, concept_stat_update.id]
        else:
            obj, created = Statistics.objects.get_or_create(org=brand,
                                                            type='concept_collections',
                                                            stat=concept_stat,
                                                            created_by=[None, request.user][request.user.is_authenticated]
                                                            )
            return [concept_stat, obj.id]

    else:
        if concept_or_phenotype == 'phenotype':
            phenotype_stat = get_brand_collections(request, 'phenotype', force_brand=brand)

            if Statistics.objects.all().filter(org__iexact=brand, type__iexact='phenotype_collections').exists():
                phenotype_stat_update = Statistics.objects.get(org__iexact=brand, type__iexact='phenotype_collections')
                phenotype_stat_update.stat = phenotype_stat
                phenotype_stat_update.updated_by = [None, request.user][request.user.is_authenticated]
                phenotype_stat_update.modified = datetime.datetime.now()
                phenotype_stat_update.save()
                return [phenotype_stat, phenotype_stat_update.id]
            else:
                obj, created = Statistics.objects.get_or_create(org=brand,
                                                                type='phenotype_collections',
                                                                stat=phenotype_stat,
                                                                created_by=[None, request.user][request.user.is_authenticated]
                                                                )
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
        data = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                        get_live_and_or_published_ver=3,  # 1= live only, 2= published only, 3= live+published 
                                                                        exclude_deleted=False,
                                                                        force_brand=force_brand,
                                                                        force_get_live_and_or_published_ver=3  # get live + published data
                                                                    )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                                get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published 
                                                                                exclude_deleted=True,
                                                                                force_brand=force_brand,
                                                                                force_get_live_and_or_published_ver=2  # get published data
                                                                            )
    elif concept_or_phenotype == 'phenotype':
        # to be shown with login
        data = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                        get_live_and_or_published_ver=3,  # 1= live only, 2= published only, 3= live+published 
                                                                        exclude_deleted=False,
                                                                        force_brand=force_brand,
                                                                        force_get_live_and_or_published_ver=3  # get live + published data
                                                                    )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                                    get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published 
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
    unique_tags_ids_list = list(Tag.objects.filter(id__in=unique_tags_ids, tag_type=2).values_list('id', flat=True))

    unique_tags_ids_published = list(set(Tag_List_Published))
    unique_tags_ids_published_list = list(Tag.objects.filter(id__in=unique_tags_ids_published, tag_type=2).values_list('id', flat=True))

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


def clear_statistics_history():
    """
        leave only the last record per day for each statistics category
    """
    with connection.cursor() as cursor:
        sql = """ 
                WITH tbl AS (
                            SELECT *
                            FROM
                            (
                                SELECT 
                                    ROW_NUMBER () OVER (PARTITION BY org, type, date(history_date) ORDER BY history_date DESC) rn
                                    , *
                                FROM clinicalcode_historicalstatistics 
                            )t
                )
                DELETE FROM clinicalcode_historicalstatistics WHERE history_id NOT IN(SELECT history_id FROM tbl WHERE rn = 1) ;
             """
        cursor.execute(sql)

 

@shared_task(bind=True)
def run_celery_datasource(self):
    request_factory = RequestFactory()
    my_url = r'^admin/run-datasource-sync/$'
    request = request_factory.get(my_url)
    request.user = AnonymousUser()

    request.CURRENT_BRAND = ''
    if request.method == 'GET':
        results = create_or_update_internal_datasources()

        return True,results

@shared_task(bind=True)
def run_celery_statistics(self):
    request_factory = RequestFactory()
    my_url = r'^admin/run-stat/$'
    request = request_factory.get(my_url)
    request.user = AnonymousUser()


    request.CURRENT_BRAND = ''
    if request.method == 'GET':
        stat = save_statistics(request)
        # print("Celery_statistics finished" + str(stat))
        return True, stat


@shared_task(bind=True)
def run_celery_collections(self):
    request_factory = RequestFactory()
    my_url = r'^admin/run-collections/$'
    request = request_factory.get(my_url)
    request.user = AnonymousUser()
    request.CURRENT_BRAND = ''

    brands = Brand.objects.all()
    brand_list = list(brands.values_list('name', flat=True))

    if request.method == 'GET':
        for brand in brand_list:
            save_statistics_collections(request, 'concept', brand)
            save_statistics_collections(request, 'phenotype', brand)

        # save for all data
        stat1 = save_statistics_collections(request, 'concept', brand='ALL')
        stat2 = save_statistics_collections(request, 'phenotype', brand='ALL')
        
        clear_statistics_history()
        
        # print("Celery_collections finished")
        return True, stat1+stat2



@login_required
def get_caliberresearch_url_source(request):
    """
        Return a csv file of HDRUK caliberresearch portal url source
    """
    if not request.user.is_superuser:
        raise PermissionDenied


    phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                            get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published 
                                                                            exclude_deleted=True,
                                                                            force_brand='HDRUK',
                                                                            force_get_live_and_or_published_ver=2  # get published data
                                                                        )

    phenotypes_ids = db_utils.get_list_of_visible_entity_ids(phenotypes, return_id_or_history_id="id")
    
    HDRUK_phenotypes = Phenotype.objects.filter(id__in = phenotypes_ids)
    HDRUK_phenotypes.exclude(source_reference__isnull=True).exclude(source_reference__exact='')
    
    # collections
    # 18    Phenotype Library    
    # 25    ClinicalCodes Repository
    #HDRUK_phenotypes.exclude(tags__contains = [18, 25] , tags__contained_by = [18, 25])
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="HDRUK_caliberresearch_url_source.csv"'
    writer = csv.writer(response)

    titles = ['Phenotype_id', 'collections_tags', 'portal.caliberresearch.org', 'is_Caliber' , 'phenotypes.healthdatagateway.org']
    writer.writerow(titles)


    HDRUK_phenotypes = HDRUK_phenotypes.order_by('id')
    
    tags = Tag.objects.all()
    
    for p in HDRUK_phenotypes:
        #CL_url_base = "https://conceptlibrary.saildatabank.com/HDRUK/old/phenotypes/"
        CL_url_base = "https://phenotypes.healthdatagateway.org/old/phenotypes/"
        redirect_url = CL_url_base + p.source_reference.split('/')[-1]
    
        is_Caliber = 'Y'
        #if set(p.tags) == set([18, 25]):
        if (p.source_reference.lower().startswith('https://portal.caliberresearch.org/phenotypes/') 
            and len(p.source_reference) > len('https://portal.caliberresearch.org/phenotypes/')):
            is_Caliber = 'Y'
        else:
            is_Caliber = 'N'
            
        writer.writerow([
                        'PH' + str(p.id),
                        list(tags.filter(id__in=p.tags).values_list('description', flat=True)),
                        p.source_reference, 
                        is_Caliber,
                        redirect_url
                        ]
                    )

    return response

    
    
    


def run_filter_statistics(request):
    """
        save filter stat for brands (phenotypes/concepts)
    """
    brands = Brand.objects.all()
    brand_list = list(brands.values_list('name', flat=True))

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        for brand in brand_list:
            save_filter_statistics(request, Concept, brand)
            save_filter_statistics(request, Phenotype, brand)

        # save for all data
        save_filter_statistics(request, Concept, brand='ALL')
        save_filter_statistics(request, Phenotype, brand='ALL')

    clear_statistics_history()
    
    return render(request, 'clinicalcode/admin/run_statistics.html',
                {
                    'successMsg': ['Filter statistics for Concepts/Phenotypes saved'],
                })


def save_filter_statistics(request, entity_class, brand):
    """
        save filter stat associated with each brand for phenotypes/concepts.
    """

    if entity_class == Concept:
        concept_stat = get_brand_filter_stat(request, entity_class, force_brand=brand)

        if Statistics.objects.all().filter(org__iexact=brand, type__iexact='concept_filters').exists():
            concept_stat_update = Statistics.objects.get(org__iexact=brand, type__iexact='concept_filters')
            concept_stat_update.stat = concept_stat
            concept_stat_update.updated_by = [None, request.user][request.user.is_authenticated]
            concept_stat_update.modified = datetime.datetime.now()
            concept_stat_update.save()
            return [concept_stat, concept_stat_update.id]
        else:
            obj, created = Statistics.objects.get_or_create(org=brand,
                                                            type='concept_filters',
                                                            stat=concept_stat,
                                                            created_by=[None, request.user][request.user.is_authenticated]
                                                            )
            return [concept_stat, obj.id]

    else:
        if entity_class == Phenotype:
            phenotype_stat = get_brand_filter_stat(request, entity_class, force_brand=brand)

            if Statistics.objects.all().filter(org__iexact=brand, type__iexact='phenotype_filters').exists():
                phenotype_stat_update = Statistics.objects.get(org__iexact=brand, type__iexact='phenotype_filters')
                phenotype_stat_update.stat = phenotype_stat
                phenotype_stat_update.updated_by = [None, request.user][request.user.is_authenticated]
                phenotype_stat_update.modified = datetime.datetime.now()
                phenotype_stat_update.save()
                return [phenotype_stat, phenotype_stat_update.id]
            else:
                obj, created = Statistics.objects.get_or_create(org=brand,
                                                                type='phenotype_filters',
                                                                stat=phenotype_stat,
                                                                created_by=[None, request.user][request.user.is_authenticated]
                                                                )
                return [phenotype_stat, obj.id]

def get_date_from_datetime(datetime):
    return datetime.date() if datetime is not None else datetime

    
def get_brand_filter_stat(request, entity_class, force_brand=None):
    """
        save filter stat for the brand in both cases of published content or not.
    """

    if force_brand == 'ALL':
        force_brand = ''

    if entity_class == Concept:
        # to be shown with login
        data = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                        get_live_and_or_published_ver=3,  # 1= live only, 2= published only, 3= live+published 
                                                                        exclude_deleted=False,
                                                                        force_brand=force_brand,
                                                                        force_get_live_and_or_published_ver=3  # get live + published data
                                                                    )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                                get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published 
                                                                                exclude_deleted=True,
                                                                                force_brand=force_brand,
                                                                                force_get_live_and_or_published_ver=2  # get published data
                                                                            )
    elif entity_class == Phenotype:
        # to be shown with login
        data = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                        get_live_and_or_published_ver=3,  # 1= live only, 2= published only, 3= live+published 
                                                                        exclude_deleted=False,
                                                                        force_brand=force_brand,
                                                                        force_get_live_and_or_published_ver=3  # get live + published data
                                                                    )

        # to be shown without login - publish data only
        data_published = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                                    get_live_and_or_published_ver=2,  # 1= live only, 2= published only, 3= live+published 
                                                                                    exclude_deleted=True,
                                                                                    force_brand=force_brand,
                                                                                    force_get_live_and_or_published_ver=2  # get published data
                                                                                )

    # Creation of two lists, one for all data and the other for published data  
    entity_id_list = []
    entity_id_list_published = []
    
    tag_list = []
    tag_list_published = []
    
    collection_list = []
    collection_list_published = []
    
    codingSystem_list = []
    codingSystem_list_published = []
    
    
    phenotype_types_list = []
    phenotype_types_list_published = []

    for i in data:
        entity_id_list = list(set(entity_id_list + [i['id']]))
        
        if i['tags'] is not None:
            tag_list = tag_list + i['tags']
            collection_list = collection_list + i['tags']
            
        if entity_class == Concept:
            if i['coding_system_id'] is not None:
                codingSystem_list = codingSystem_list + [i['coding_system_id']]
        elif entity_class == Phenotype:
            if i['clinical_terminologies'] is not None:
                codingSystem_list = codingSystem_list + i['clinical_terminologies']
            if i['type'] is not None:
                phenotype_types_list = phenotype_types_list + [i['type'].lower()]



    for i in data_published:
        entity_id_list_published = list(set(entity_id_list_published + [i['id']]))

        if i['tags'] is not None:
            tag_list_published = tag_list_published + i['tags']
            collection_list_published = collection_list_published + i['tags']
            
        if entity_class == Concept:
            if i['coding_system_id'] is not None:
                codingSystem_list_published = codingSystem_list_published + [i['coding_system_id']]
        elif entity_class == Phenotype:
            if i['clinical_terminologies'] is not None:
                codingSystem_list_published = codingSystem_list_published + i['clinical_terminologies']
            if i['type'] is not None:
                phenotype_types_list_published = phenotype_types_list_published + [i['type'].lower()]
                
    # Create a list for both allData and published.
    # tags
    unique_tags_ids_list = list(Tag.objects.filter(id__in=list(set(tag_list)), tag_type=1).values_list('id', flat=True))
    unique_tags_ids_published_list = list(Tag.objects.filter(id__in=list(set(tag_list_published)), tag_type=1).values_list('id', flat=True))

    # collections
    unique_collections_ids_list = list(Tag.objects.filter(id__in=list(set(collection_list)), tag_type=2).values_list('id', flat=True))
    unique_collections_ids_published_list = list(Tag.objects.filter(id__in=list(set(collection_list_published)), tag_type=2).values_list('id', flat=True))

    # data sources
    if entity_class == Phenotype:
        datasources_ids_list = list(PhenotypeDataSourceMap.history.filter(phenotype_id__in=entity_id_list).values_list('datasource_id', flat=True))        
        datasources_ids_published_list = list(PhenotypeDataSourceMap.history.filter(phenotype_id__in=entity_id_list_published).values_list('datasource_id', flat=True))


    # publish_date
    if entity_class == Concept:
        publish_date_dict = PublishedConcept.objects.filter(concept_id__in=entity_id_list).aggregate(Max('created'),Min('created'))
    elif entity_class == Phenotype:
        publish_date_dict = PublishedPhenotype.objects.filter(phenotype_id__in=entity_id_list).aggregate(Max('created'),Min('created'))

            
    min_publish_date = str(get_date_from_datetime(publish_date_dict['created__min']))
    max_publish_date = str(get_date_from_datetime(publish_date_dict['created__max']))

    # create_update_date
    create_update_date_dict = entity_class.objects.filter(id__in=entity_id_list).aggregate(Min('created')
                                                                                        ,Max('created')
                                                                                        ,Min('modified')
                                                                                        ,Max('modified')
                                                                                        )
    min_create_date = str(get_date_from_datetime(create_update_date_dict['created__min']))
    max_create_date = str(get_date_from_datetime(create_update_date_dict['created__max']))
    min_update_date = str(get_date_from_datetime(create_update_date_dict['modified__min']))
    max_update_date = str(get_date_from_datetime(create_update_date_dict['modified__max']))
    

    # Create two distinct dictionaries for both allData and published
    stats_dict = {}
    stats_dict['collections'] = [{"data_scope": "all_data", "collection_ids": [x for x in Counter(collection_list).most_common() if x[0] in unique_collections_ids_list]} 
                                ,{"data_scope": "published_data", "collection_ids": [x for x in Counter(collection_list_published).most_common() if x[0] in unique_collections_ids_published_list]}
                                ]
    
    stats_dict['tags'] = [{"data_scope": "all_data", "tag_ids": [x for x in Counter(tag_list).most_common() if x[0] in unique_tags_ids_list]} 
                         ,{"data_scope": "published_data", "tag_ids": [x for x in Counter(tag_list_published).most_common() if x[0] in unique_tags_ids_published_list]} 
                         ]
        
    stats_dict['coding_systems'] = [{"data_scope": "all_data", "coding_system_ids": Counter(codingSystem_list).most_common()}
                                   ,{"data_scope": "published_data", "coding_system_IDs": Counter(codingSystem_list_published).most_common()} 
                                   ]
    
        
    stats_dict['publish_date'] = {"min_publish_date": min_publish_date, "max_publish_date": max_publish_date}
    stats_dict['create_date'] = {"min_create_date": min_create_date, "max_create_date": max_create_date}
    stats_dict['update_date'] = {"min_update_date": min_update_date, "max_update_date": max_update_date}
    
    if entity_class == Phenotype:
        stats_dict['data_sources'] = [{"data_scope": "all_data", "data_source_ids": Counter(datasources_ids_list).most_common()}
                                     ,{"data_scope": "published_data", "data_source_ids": Counter(datasources_ids_published_list).most_common()}
                                   ]
            
        stats_dict['phenotype_types'] = [{"data_scope": "all_data", "types": Counter(phenotype_types_list).most_common()}
                                        ,{"data_scope": "published_data", "types": Counter(phenotype_types_list_published).most_common()}
                                        ]
    
    
    return stats_dict



    