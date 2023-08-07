
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponse
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from celery import shared_task

import json
import csv

from .. import db_utils, utils, tasks
from ..models import *
from ..permissions import *
from .View import *

logger = logging.getLogger(__name__)

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

    titles = ['Phenotype_id', 'collections', 'portal.caliberresearch.org', 'is_Caliber' , 'phenotypes.healthdatagateway.org']
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
                        p.id,
                        list(tags.filter(id__in=p.collections).values_list('description', flat=True)),
                        p.source_reference, 
                        is_Caliber,
                        redirect_url
                        ]
                    )

    return response
