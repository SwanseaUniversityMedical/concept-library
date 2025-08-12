"""DOI-related utilities to manage registration & other assoc. tasks"""
from http import HTTPStatus
from base64 import b64encode
from celery import shared_task
from functools import cache as memcache
from django.db import connection
from contextlib import suppress
from django.conf import settings
from celery.utils.log import get_task_logger

import json
import enum
import requests
import traceback

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.Brand import Brand
from clinicalcode.models.QueuedDOI import QueuedDOI
from clinicalcode.models.GenericEntity import GenericEntity

"""Formattable template for resultant DOI URLs"""
DOI_FORMAT = 'https://doi.org/%(id)s'

"""Formattable template to query known DOIs"""
DOI_QUERY = 'https://api.datacite.org/dois?prefix=%(prefix)s&query=alternateIdentifier:%(identifier)s'

"""Registration request timeout in seconds"""
REQ_TIMEOUT = 30

"""Req. Proxy URLs dependent on env"""
PROXIES_URL = {
  'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
  'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
}

class DataciteEndpoints(str, enum.Enum):
  """
  Datacite API endpoint

  > Note: See ref @ https://support.datacite.org/reference/

  """
  PROD = 'https://api.datacite.org/dois'
  TEST = 'https://api.test.datacite.org/dois'

def is_success(status):
  """Det. whether a status code describes a successful request"""
  return 200 <= status <= 299

def is_client_err(status):
  """Det. whether a status code describes a client request error"""
  return 400 <= status <= 499

def is_server_err(status):
  """Det. whether a status code describes an (internal) server error"""
  return 500 <= status <= 599

@memcache
def compute_token(username, password):
  """
  Computes the base64 encoded authorisation token

  Args:
    username (str): DataCite username (from env ideally)
    password (str): DataCite password (from env ideally)

  Returns:
    (str): Base64-encoded authorisation token (ascii encoding)
  """
  return b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')

def update_doi(entity, doi_url):
  """
  Attempts to update both the live & historical DOI field of the specified entity

  Note:
    - Live entity's DOI is only updated if it matches the historical version being published

  Args:
    entity (HistoricalGenericEntity): the entity to be registered with the DOI service
    doi_url                    (str): the registered DOI URL target
  """
  with connection.cursor() as cursor:
    cursor.execute(
      '''
      do $tx$
      declare
        v_version integer := -1;
      begin
        update public.clinicalcode_historicalgenericentity as trg
           set doi = %(url)s
				where trg.id = %(id)s
          and trg.history_id = %(ver)s;

        select max(hge.history_id)
          into v_version
          from public.clinicalcode_historicalgenericentity as hge
         where hge.id = %(id)s;

        if v_version = %(ver)s then
          update public.clinicalcode_genericentity as trg
            set doi = %(url)s
          where trg.id = %(id)s;
        end if;
      end;
      $tx$ language plpgsql;
      ''',
      params={
        'id': entity.id,
        'ver': entity.history_id,
        'url': doi_url,
      }
    )

def publish_doi(entity, timeout=REQ_TIMEOUT, compute_brand=True, use_proxy=True, use_debug=False):
  """
  Attempts to synchronously register & publish a DOI for the given entity

  Args:
    entity (HistoricalGenericEntity): the entity to be registered with the DOI service
    timeout                 (number): request timeout duration in seconds; defaults to `30s` (_i.e._ `REQ_TIMEOUT` global const)
    compute_brand             (bool): optionally specify whether to compute the `Brand` context from the `entity`; defaults to `True`
    use_proxy                 (bool): optionally specify whether to use HTTP/S proxy targets; defaults to `True`
    use_debug                 (bool): optionally specify whether to register in debug mode, utilising the DataCite API test server; defaults to `True`

  Returns:
    (bool): reflects successful state of the operation

  Raises:
    RuntimeError: raised in all known cases
    BaseException: raised in unhandled cases
  """
  url = DataciteEndpoints.TEST.value if use_debug else DataciteEndpoints.PROD.value
  proxies = PROXIES_URL if use_proxy else None
  identifier = '%s/%d' % (entity.id, entity.history_id)
  auth_token = compute_token(settings.DOI_USERNAME, settings.DOI_PASSWORD)

  brand_trg = None
  if compute_brand:
    brand_trg = entity.brands if isinstance(entity.brands, list) else []
    brand_trg = Brand.objects.filter(pk=brand_trg[0]) if len(brand_trg) > 0 else None
    if brand_trg is not None and brand_trg.exists():
      brand_trg = brand_trg.first().name

  if not isinstance(brand_trg, str) or gen_utils.is_empty_string(brand_trg):
    rel_target = settings.DOI_RELATION
    url_target = '%s%s' % (settings.DOI_REFERRER, identifier)
  else:
    rel_target = '%s%s/' % (settings.DOI_RELATION, brand_trg)
    url_target = '%s%s/%s' % (settings.DOI_REFERRER, brand_trg, identifier)

  with connection.cursor() as cursor:
    cursor.execute(
      '''
      with
        rels as (
          select
                concept.id,
                concept.history_id,
                concept.phenotype_owner_id,
                rank() over (
                  partition by phenotype_owner_id
                      order by concept.history_date desc
                ) as ranking
            from public.clinicalcode_historicalgenericentity as entity,
                 json_array_elements(entity.template_data::json->'concept_information') as concepts
            join public.clinicalcode_historicalconcept as concept
              on cast(concepts->>'concept_id' as integer) = concept.id and cast(concepts->>'concept_version_id' as integer) = concept.history_id
            where entity.id = %(id)s
              and entity.history_id = %(history_id)s
              and concept.phenotype_owner_id != %(id)s
        )
      select json_agg(json_build_object(
          'relatedIdentifier', %(url)s || rels.phenotype_owner_id,
          'relatedIdentifierType', 'URL',
          'relationType', 'IsDerivedFrom',
          'resourceTypeGeneral', 'Model'
        )) as relations
        from rels
       where ranking = 1;
      ''',
      params={
        'id': entity.id,
        'history_id': entity.history_id,
        'url': rel_target,
      }
    )

    columns = [col[0] for col in cursor.description]
    relations = [dict(zip(columns, row)) for row in cursor.fetchall()]
    relations = relations[0].get('relations') if len(relations) > 0 and relations[0].get('relations') is not None else []

  status = None
  try:
    response = requests.post(
      url,
      json={
        'data': {
          'type': 'dois',
          'attributes': {
            'event': 'publish',
            'prefix': settings.DOI_PREFIX,
            'version': '1.0',
            'creators': [
              {
                'name': entity.author,
              }
            ],
            'titles': [
              {
                'title': entity.name
              }
            ],
            'publisher': 'PhenotypeLibrary',
            'publicationYear': gen_utils.parse_int(entity.updated.year),
            'types': {
              'resourceTypeGeneral': 'Model'
            },
            'url': url_target,
            'alternateIdentifier': identifier,
            'alternateIdentifierType': 'Phenotype Library Identifier',
            'relatedIdentifiers': relations,
          }
        }
      },
      headers={
        'accept': 'application/vnd.api+json',
        'content-type': 'application/json',
        'Authorization': 'Basic %s' % auth_token,
      },
      proxies=proxies,
      timeout=timeout
    )

    status = next((x for x in list(HTTPStatus) if x.value == response.status_code), HTTPStatus.BAD_REQUEST)
    if response.ok and is_success(status):
      # Success
      result = response.json()
      doi_id = response.get('data', {}).get('id')
      if gen_utils.is_empty_string(doi_id):
        raise RuntimeError(
          '[DOI<id: %s>::RuntimeError] Data Integrity:\n\t- No `data.id` associated with response\n' % (
            identifier
          )
        )

      doi_url = DOI_FORMAT % { 'id': doi_id }
      return update_doi(entity, doi_url)
    elif is_client_err(status):
      # Client error
      result = response.json()
      raise RuntimeError(
        '[DOI<id: %s>::ClientError<code: %d>] Client Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2)
        )
      )
    elif is_server_err(status):
      # Server error
      raise RuntimeError(
        '[DOI<id: %s>::ServerError<code: %d>] Server Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2),
        ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        )
      )
  except json.decoder.JSONDecodeError as e:
    raise RuntimeError(
      '[DOI<id: %s>::JsonError] [HttpStatus: %d] Failed to decode JSON:\n\t- Phrase: %s\n\t- Trace:\n%s' % (
        identifier,
        status.value,
        status.phrase or '',
        ''.join(traceback.format_exception(type(e), e, e.__traceback__))
      )
    )
  except requests.exceptions.RequestException as e:
    raise RuntimeError(
      '[DOI<id: %s>::RequestException] Failed to make Request:\n\t- Trace:\n%s' % (
        identifier,
        ''.join(traceback.format_exception(type(e), e, e.__traceback__))
      )
    )
  except Exception as e:
    raise e

@shared_task(name='publish_doi_task')
def publish_doi_task(entity, timeout=REQ_TIMEOUT):
  """
  Async DOI publishing job registered with Celery

  Args:
    entity (HistoricalGenericEntity): the entity to be registered with the DOI service
    timeout                 (number): request timeout duration in seconds; defaults to `30s` (_i.e._ `REQ_TIMEOUT` global const)

  Returns:
    (bool): reflecting the success status of this async operation
  """
  if not settings.DOI_ACTIVE:
    return True

  logger = get_task_logger('cll')
  entity = QueuedDOI.resolve_entity(entity)
  try:
    publish_doi(entity, timeout=timeout)
  except Exception as e:
    logger.warning(
      '[DOI::Entity<id: %(id)s, history_id: %(ver)s>] DOI registration added to queue after failure of async DOI publish job with exception:\n\n%(err)s\n' % {
        'id': entity.id,
        'ver': entity.history_id,
        'err': ''.join(traceback.format_exception(type(e), e, e.__traceback__))
      }
    )

    reg = QueuedDOI.register(entity, bubble_errors=True)
    err = reg.get('errors')
    if isinstance(err, dict):
      for x in err.values():
        logger.error(
          '[DOI::Entity<id: %(id)s, history_id: %(ver)s>] Failed to register entity on failure queue:\n\n%(err)s\n' % {
            'id': entity.id,
            'ver': entity.history_id,
            'err': x,
          }
        )

    return False
  else:
    logger.info(
      '[DOI::Entity<id: %(id)s, history_id: %(ver)s>] Successfully registered DOI' % {
        'id': entity.id,
        'ver': entity.history_id,
      }
    )

    QueuedDOI.unregister(entity)
    return True

@shared_task(bind=True)
def cron_publish_retry(self):
  """
  Asyn cronjob to retry tasks failed DOI registrations

  Returns:
    (bool): reflects the success status of the op
  """
  if not settings.DOI_ACTIVE:
    return False

  queue = QueuedDOI.get_queued()
  if not isinstance(queue, list) or len(queue) < 1:
    return True

  logger = get_task_logger('cll')

  registrable = []
  unregistrable = []
  for ent in queue:
    idents = {
      'id': ent.get('trg_id'),
      'history_id': ent.get('trg_ver'),
    }

    entity = QueuedDOI.resolve_entity(idents)
    if not entity:
      continue

    is_deleted = False
    recorded_doi = None
    with connection.cursor() as cursor:
      cursor.execute(
        '''
        select ge.is_deleted, hge.doi
          from public.clinicalcode_genericentity as ge
          join public.clinicalcode_historicalgenericentity as hge
            on hge.id = ge.id
         where ge.id = %(id)s
           and hge.history_id = %(history_id)s
         limit 1;
        ''',
        params=idents
      )

      if cursor.rowcount > 0:
        row = cursor.fetchone()
        is_deleted = not not row[0]
        recorded_doi = row[1] if isinstance(row[1], str) and not gen_utils.is_empty_string(row[1]) else None

    if is_deleted or recorded_doi is not None:
      unregistrable.append(entity)
      continue

    try:
      registered = publish_doi_task(entity)
    except:
      registered = False

    register = unregistrable if registered else registrable
    register.append(entity)

  if len(registrable) > 0:
    with suppress(BaseException):
      QueuedDOI.register(*registrable)
      logger.info('[DOI::CronJob::Failure] Reregistred failed task queue of size: %d' % len(registrable))

  if len(unregistrable) > 0:
    with suppress(BaseException): 
      QueuedDOI.unregister(*unregistrable)
      logger.info('[DOI::CronJob::Success] Unregistred failed task queue of size: %d' % len(registrable))
  return True
