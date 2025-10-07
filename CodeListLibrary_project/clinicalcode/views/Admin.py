from http import HTTPStatus
from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models.query import QuerySet
from django.core.exceptions import BadRequest
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

import time
import math
import logging
import numbers
import requests

from clinicalcode.entity_utils import gen_utils, permission_utils, stats_utils
from clinicalcode.models.DataSource import DataSource


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
            'stat': stat,
            'successMsg': ['Filter statistics for Concepts/Phenotypes saved'],
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
                'stat': stat,
                'successMsg': ['Homepage statistics saved'],
            }
        )

    raise BadRequest


##### Datasources
def query_hdruk_datasource(
    page=1,
    per_page=20,
    req_timeout=30,
    retry_attempts=3,
    retry_delay=2,
    retry_codes=[
        HTTPStatus.REQUEST_TIMEOUT.value,
        HTTPStatus.TOO_MANY_REQUESTS.value,
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
        HTTPStatus.INTERNAL_SERVER_ERROR.value,
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
    proxy = {
        'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
        'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/'
    }

    url = f'https://api.healthdatagateway.org/api/v1/datasets/?page={page}'
    if isinstance(per_page, numbers.Number) and math.isfinite(per_page) and not math.isnan(per_page):
        url += f'&per_page={per_page}'

    response = None
    retry_attempts = max(retry_attempts, 0) + 1
    for attempts in range(0, retry_attempts, 1):
        try:
            response = requests.get(url, req_timeout, proxies=proxy)
        except requests.exceptions.ConnectionError:
            response = None

        if retry_attempts - attempts > 0 and (not response or (retry_codes and response.status_code in retry_codes)):
            time.sleep(retry_delay*pow(2, attempts - 1))
            continue

        if response:
            break

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
        pid = ds.get('pid')
        if not isinstance(pid, str):
            continue

        meta = ds.get('latest_metadata')
        idnt = ds.get('id')
        uuid = ds.get('mongo_pid')
        status = ds.get('status')
        if not isinstance(meta, dict) or not isinstance(idnt, int):
            continue

        meta = meta.get('metadata').get('metadata') if isinstance(meta.get('metadata'), dict) else None
        meta = meta.get('summary') if isinstance(meta, dict) else None
        if meta is None or not isinstance(meta.get('title'), str):
            continue

        name = meta.get('title')
        if not isinstance(name, str) or gen_utils.is_empty_string(name):
            continue

        sources[pid] = {
            'id': idnt,
            'pid': pid,
            'uuid': uuid,
            'name': name[:500].strip(),
            'description': meta.get('description').strip() if isinstance(meta.get('description'), str) else None,
            'url': f'https://healthdatagateway.org/en/dataset/{idnt}',
            'status': status,
        }

    return sources


def get_hdruk_datasources():
    """
      Attempts to collect HDRUK datasources via its API

      Returns:
        A tuple variant specifying the resulting datasources, specified as a dict, and an optional err message, defined as a string, if an err occurs
    """
    try:
        result = query_hdruk_datasource(page=1, per_page=5)
    except Exception as e:
        msg = f'Unable to sync HDRUK datasources, failed to reach api with err:\n\n{str(e)}'
        logger.warning(msg)

        return {}, msg

    datasources = collect_datasources(result.get('data'))
    for page in range(2, result.get('last_page') + 1, 1):
        try:
            result = query_hdruk_datasource(page=page, per_page=5)
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

    to_create = []
    to_update = []
    for pid, datasource in hdruk_datasources.items():
        uid = datasource.get('uuid')
        idnt = datasource.get('id')
        name = datasource.get('name')
        status = datasource.get('status')

        if not isinstance(status, str):
            status = 'UNKNOWN'
            is_active = False
        else:
            is_active = status.lower() == 'active'

        if not is_active:
            continue

        try:
            if isinstance(uid, str):
                qry = Q(uid__iexact=uid)
            else:
                qry = Q(name__iexact=name) & (Q(uid__isnull=True) | Q(uid=''))

            internal_datasource = DataSource.objects.filter(qry)
        except DataSource.DoesNotExist:
            internal_datasource = None

        if not isinstance(internal_datasource, QuerySet) or not internal_datasource.exists():
            new_datasource = DataSource()
            new_datasource.uid = uid if isinstance(uid, str) else None
            new_datasource.url = datasource['url']
            new_datasource.name = name
            new_datasource.description = datasource['description'] if datasource['description'] else ''
            new_datasource.datasource_id = idnt
            new_datasource.source = 'HDRUK'
            to_create.append(new_datasource)
            continue

        for internal in internal_datasource.all():
            if internal.source != 'HDRUK':
                continue

            desc = datasource['description'] if isinstance(datasource['description'], str) else internal.description

            update_id = str(internal.datasource_id) != str(idnt)
            update_uid = isinstance(uid, str) and internal.uid != uid
            update_url = internal.url != datasource['url']
            update_name = internal.name != name
            update_desc = internal.description != desc

            if update_id or update_uid or update_url or update_name or update_desc:
                internal.uid = uid
                internal.url = datasource['url']
                internal.name = name
                internal.description = desc
                internal.datasource_id = idnt
                to_update.append(internal)

    if len(to_update) > 0:
        DataSource.objects.bulk_update(to_update, ['uid', 'url', 'name', 'description', 'datasource_id'])
        to_update = [{ 'id': x.id, 'ds_id': x.datasource_id, 'name': x.name } for x in to_update]

    if len(to_create) > 0:
        to_create = DataSource.objects.bulk_create(to_create)
        to_create = [{ 'id': x.id, 'ds_id': x.datasource_id, 'name': x.name } for x in to_create]

    return {
        'created': to_create,
        'updated': to_update,
    }


@login_required
def run_datasource_sync(request):
    """Manual run of the DataSource sync"""
    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    if not request.user.is_superuser:
        raise PermissionDenied

    if not permission_utils.is_member(request.user, 'system developers'):
        raise PermissionDenied

    if request.method == 'GET':
        results = create_or_update_internal_datasources()
        
        message = {
            'result': results,
            'successMsg': ['HDR-UK datasources synced'],
        }

        if isinstance(results, str):
            message = { 'errorMsg': [results] }

        return render(
            request, 
            'clinicalcode/admin/run_datasource_sync.html', 
            message
        )


@shared_task(bind=True)
def run_celery_datasource(self):
    """Celery cron task, used to synchronise DataSources on a schedule"""
    results = create_or_update_internal_datasources()
    return True, results
