from http import HTTPStatus
from celery import shared_task
from django.conf import settings
from django.test import RequestFactory
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView
from django.core.exceptions import BadRequest
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required

import time
import logging
import requests

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.DataSource import DataSource

from ..entity_utils import permission_utils, stats_utils

logger = logging.getLogger(__name__)

### Entity Statistics
class EntityStatisticsView(TemplateView):
    """Admin job panel to save statistics for templates across entities"""
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied

        stat = stats_utils.collect_statistics(request)
        return render(request, 'clinicalcode/admin/run_statistics.html', {
            'successMsg': ['Filter statistics for Concepts/Phenotypes saved'],
            'stat': stat,
        })


def run_homepage_statistics(request):
    """Manual run for administrators to save home page statistics"""
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
                'stat': stat,
            }
        )

    raise BadRequest


##### Datasources
def query_hdruk_datasource(
    page=1,
    req_timeout=30,
    retry_attempts=3,
    retry_delay=2,
    retry_codes=[
        HTTPStatus.REQUEST_TIMEOUT.value,
        HTTPStatus.TOO_MANY_REQUESTS.value,
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
    ]
):
    """
      Attempts to query HDRUK HealthDataGateway API

      Args:
        page            (int): the page id to query
        req_timeout     (int): request timeout (in seconds)
        retry_attempts  (int): max num. of attempts for each page request
        retry_delay     (int): timeout, in seconds, between retry attempts (backoff algo)
        retry_codes    (list): a list of ints specifying HTTP Status Codes from which to trigger retry attempts

      Returns:
        A dict containing the assoc. data and page bounds, if applicable
    """
    url = f'https://api.healthdatagateway.org/api/v1/datasets/?page={page}'
    proxy = {
        'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
        'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/'
    }

    response = None
    retry_attempts = max(retry_attempts, 0) + 1
    for attempts in range(0, retry_attempts, 1):
        try:
            response = requests.get(url, req_timeout, proxies=proxy)
            if retry_attempts - attempts > 0 and (not retry_codes or response.status_code in retry_codes):
                time.sleep(retry_delay*pow(2, attempts - 1))
                continue
        except requests.exceptions.ConnectionError:
            pass

    if not response or response.status_code != 200:
        status = response.status_code if response else 'INT_ERR'
        raise Exception(f'Err response from server, Status<code: {status}, attempts_made: {retry_attempts}>')

    result = response.json()
    if not isinstance(result, dict):
        raise Exception(f'Invalid resultset, expected result as `dict` but got `{type(result)}`')

    last_page = result.get('last_page')
    if not isinstance(last_page, int):
        raise TypeError(f'Invalid resultset, expected `last_page` as `int` but got `{type(last_page)}`')

    data = result.get('data')
    if not isinstance(data, list):
        raise TypeError(f'Invalid resultset, expected `data` as `list` but got `{type(last_page)}`')

    return { 'data': data, 'last_page': last_page, 'page': page }


def collect_datasources(data):
    """
      Safely parses datasource records from a resultset page

      Args:
        data (list): a list specifying the datasources contained by a resultset 

      Returns:
        A dict containing the parsed data
    """
    sources = {}
    for ds in data:
        meta = ds.get('latest_metadata')
        idnt = ds.get('id')
        uuid = ds.get('pid')

        if not isinstance(meta, dict) or not isinstance(idnt, int) or not isinstance(uuid, str):
            continue

        meta = meta.get('metadata').get('metadata') if isinstance(meta.get('metadata'), dict) else None
        meta = meta.get('summary') if isinstance(meta, dict) else None
        if meta is None or not isinstance(meta.get('title'), str):
            continue

        name = meta.get('title')
        if not isinstance(name, str) or gen_utils.is_empty_string(name):
            continue

        sources[uuid] = {
            'id': idnt,
            'uuid': uuid,
            'name': name[:500].strip(),
            'description': meta.get('description').strip()[:500] if isinstance(meta.get('description'), str) else None,
            'url': f'https://healthdatagateway.org/en/dataset/{idnt}',
        }

    return sources

def get_hdruk_datasources():
    """
      Attempts to collect HDRUK datasources via its API

      Returns:
        A tuple variant specifying the resulting datasources, specified as a dict, and an optional err message, defined as a string, if an err occurs
    """
    try:
        result = query_hdruk_datasource(page=1)
    except Exception as e:
        msg = f'Unable to sync HDRUK datasources, failed to reach api with err:\n\n{str(e)}'
        logger.warning(msg)

        return {}, msg

    datasources = collect_datasources(result.get('data'))
    for page in range(2, result.get('last_page') + 1, 1):
        try:
            result = query_hdruk_datasource(page=page)
            datasources |= collect_datasources(result.get('data'))
        except Exception as e:
            logger.warning(f'Failed to retrieve HDRUK DataSource @ Page[{page}] with err:\n\n{str(e)}')

    return datasources, None


def create_or_update_internal_datasources():
    """
      Attempts to sync the DataSource model with those resolved from the HDRUK HealthDataGateway API

      Returns:
        Either (a) an err message (str), or (b) a dict specifying the result of the diff
    """
    hdruk_datasources, error_message = get_hdruk_datasources()
    if error_message:
        return error_message

    results = {
        'created': [],
        'updated': []
    }

    for uid, datasource in hdruk_datasources.items():
        idnt = datasource.get('id')
        name = datasource.get('name')

        try:
            internal_datasource = DataSource.objects.filter(
                Q(uid__iexact=uid) | \
                Q(name__iexact=name) | \
                Q(datasource_id=idnt)
            )
        except DataSource.DoesNotExist:
            internal_datasource = False
        
        if internal_datasource and internal_datasource.exists():
            for internal in internal_datasource.all():
                if internal.source != 'HDRUK':
                    continue

                desc = datasource['description'] if isinstance(datasource['description'], str) else internal.description

                update_id = internal.datasource_id != idnt
                update_uid = internal.uid != uid
                update_url = internal.url != datasource['url']
                update_name = internal.name != name
                update_description = internal.description != desc

                if update_id or update_uid or update_url or update_name or update_description:
                    internal.uid = uid
                    internal.url = datasource['url']
                    internal.name = name
                    internal.description = desc
                    internal.datasource_id = idnt
                    internal.save()
                    results['updated'].append({ 'id': idnt, 'name': name })
        else:
            new_datasource = DataSource()
            new_datasource.uid = uid
            new_datasource.url = datasource['url']
            new_datasource.name = name
            new_datasource.description = datasource['description'] if datasource['description'] else ''
            new_datasource.datasource_id = idnt
            new_datasource.source = 'HDRUK'
            new_datasource.save()
            results['created'].append({ 'id': idnt, 'name': name })

    return results


def run_datasource_sync(request):
    """Manual run of the DataSource sync"""
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
    """Celery cron task, used to synchronise DataSources on a schedule"""
    request_factory = RequestFactory()
    my_url = r'^admin/run-datasource-sync/$'
    request = request_factory.get(my_url)
    request.user = AnonymousUser()

    request.CURRENT_BRAND = ''
    if request.method == 'GET':
        results = create_or_update_internal_datasources()
        return True, results
