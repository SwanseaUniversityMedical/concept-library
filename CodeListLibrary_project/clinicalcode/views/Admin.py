from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.exceptions import BadRequest
from django.test import RequestFactory
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from celery import shared_task

import json
import logging
import requests

from clinicalcode.models.DataSource import DataSource

from ..entity_utils import permission_utils, stats_utils

logger = logging.getLogger(__name__)

### Entity Statistics
class EntityStatisticsView(TemplateView):
    """
        Admin job panel to save statistics for templates across entities
    """
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied

        stats_utils.collect_statistics(request)
        context = {
            'successMsg': ['Filter statistics for Concepts/Phenotypes saved'],
        }

        return render(request, 'clinicalcode/admin/run_statistics.html', context)


def run_homepage_statistics(request):
    """
        save home page statistics
    """
    if not request.user.is_superuser:
        raise PermissionDenied

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if request.method == 'GET':
        stat = stats_utils.save_homepage_stats(request)
        return render(
            request,
            'clinicalcode/admin/run_statistics.html', 
            {
                'successMsg': ['Homepage statistics saved'],
                'stat': stat
            }
        )

    raise BadRequest

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

