"""DOI-related utilities to manage registration & other assoc. tasks"""
from http import HTTPStatus
from base64 import b64encode
from functools import cache as memcache
from django.db import connection
from contextlib import suppress
from django.conf import settings

import json
import enum
import celery
import logging
import requests
import traceback

from clinicalcode.entity_utils import (gen_utils, constants)
from clinicalcode.models.Brand import Brand
from clinicalcode.models.QueuedDOI import QueuedDOI


logger = logging.getLogger(__name__)


# Constant(s)
"""Formattable template to query known DOIs"""
DOI_QUERY = '?prefix=%(prefix)s&query=identifiers.identifier:%(identifier)s'

"""Registration request timeout in seconds"""
REQ_TIMEOUT = 5

"""Req. Proxy URLs dependent on env"""
PROXIES_URL = {
  'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
  'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
}


# Result template(s)
class DataciteFormats(str, enum.Enum):
  """
  Datacite registration result format template(s)

  > Note: See ref @ https://support.datacite.org/reference/

  """
  PROD = 'https://doi.org/%(id)s'
  TEST = 'https://handle.test.datacite.org/%(id)s'


# Endpoint target(s)
class DataciteEndpoints(str, enum.Enum):
  """
  Datacite API endpoint

  > Note: See ref @ https://support.datacite.org/reference/

  """
  PROD = 'https://api.datacite.org/dois'
  TEST = 'https://api.test.datacite.org/dois'


# Http utilities
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

def is_success(status):
  """
  Det. whether a status code describes a successful request; see `MDN's "Successful" response codes`_

  Args:
    status (HttpStatus|int): the `HttpStatus` code

  Returns:
    (bool): specifies whether the provided `HttpStatus` code describes a successful response

  .. _MDN's "Successful" response codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status#successful_responses
  """
  return 200 <= status <= 299

def is_response_err(status):
  """
  Det. whether a status code describes any response error type; see `MDN's "Error" response codes`_

  Args:
    status (HttpStatus|int): the `HttpStatus` code

  Returns:
    (bool): specifies whether the provided `HttpStatus` code describes any error response

  .. _MDN's "Error" response codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status
  """
  return 400 <= status <= 599

def is_client_err(status):
  """
  Det. whether a status code describes a client request error; see `MDN's "Client Error" response codes`_

  Args:
    status (HttpStatus|int): the `HttpStatus` code

  Returns:
    (bool): specifies whether the provided `HttpStatus` code describes a client error

  .. _MDN's "Client Error" response codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status#client_error_responses
  """
  return 400 <= status <= 499

def is_server_err(status):
  """
  Det. whether a status code describes an (internal) server error; see `MDN's "Server Error" response codes`_

  Args:
    status (HttpStatus|int): the `HttpStatus` code

  Returns:
    (bool): specifies whether the provided `HttpStatus` code describes a server error

  .. _MDN's "Server Error" response codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status#server_error_responses
  """
  return 500 <= status <= 599


# Entity-related utilities
def update_doi(entity, doi_url):
  """
  Internal utility func. that attempts to safely update both the live & historical DOI field of the specified entity

  Note:
    - Live entity's DOI is only updated if it matches the historical version being published

  Args:
    entity  (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` specifying the entity to publish
    doi_url               (str): the registered DOI URL target

  Returns:
    (bool): a boolean describing the successful operation of this func; used for downstream confirmation
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

  return True


# Registration & publication utilities
@memcache
def is_debug_env():
  """
  Determines whether the env has defined debug flags, and thus, whether the test endpoints should be used

  Returns:
    (bool): specifying whether the env has defined debug flags
  """
  return (
    settings.DEBUG
    or settings.IS_DEMO
    or settings.IS_DEVELOPMENT_PC
  )

def is_publish_target_registrable(form_valid=False, approval_status=constants.APPROVAL_STATUS.ANY):
  """
  Determines whether the target (entity) being published can have its DOI registered.

  Note:
    - This function will always resolve `False` if the `DOI_ACTIVE` app config variable evaluates to `False`

  Args:
    form_valid      (bool): specifies whether the target's form was successfully processed; defaults to `False`
    approval_status (Enum): specifies whether the target's downstream publish status; defaults to `APPROVAL_STATUS.ANY`

  Returns:
    (bool): specifies whether the publish target can have its DOI registered
  """
  if not settings.DOI_ACTIVE:
    return False

  form_valid = form_valid if isinstance(form_valid, bool) else False

  if isinstance(approval_status, int) and approval_status in constants.APPROVAL_STATUS:
    approval_status = constants.APPROVAL_STATUS(approval_status)
  elif not isinstance(approval_status, constants.APPROVAL_STATUS):
    approval_status = constants.APPROVAL_STATUS.ANY

  return form_valid and approval_status == constants.APPROVAL_STATUS.APPROVED


# DOI query request callable(s)
def find_registered_ident(entity, timeout=REQ_TIMEOUT, use_proxy=True, force_debug=False):
  """
  Attempts to find the identifier of the DOI registred for the specified entity

  Args:
    entity        (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` specifying the entity of interest
    timeout                  (number): request timeout duration in seconds; defaults to `5s` (_i.e._ `REQ_TIMEOUT` global const)
    use_proxy                  (bool): optionally specify whether to use HTTP/S proxy targets; defaults to `True`
    force_debug                (bool): optionally specify whether to require debug mode, forcing the use of the DataCite API test server; defaults to `False`

  Returns:
    (str|None): if found then (a) a `str` describing the DOI Identifier registred for this entity, or if not found, (b) a `NoneType` value

  Raises:
    ValueError: raised on entity resolution failure
    RuntimeError: raised for data integrity error(s)
  """
  target = QueuedDOI.resolve_entity(entity)
  if target is None:
    raise ValueError(
      '[DOI::FindIdent::Invalid] Failed to resolve entity, expected `dict`|`HistoricalGenericEntity` but got %s' % (
        type(entity).__name__ if entity is not None else 'NoneType'
      )
    )

  obj = find_registered_doi(target, timeout=timeout, use_proxy=use_proxy, force_debug=force_debug)
  if not isinstance(obj, dict):
    return None

  doi_id = obj.get('id')
  if not isinstance(doi_id, str) or gen_utils.is_empty_string(doi_id):
    raise RuntimeError(
      '[DOI<id: %s/%s>::FindIdent::RuntimeError] Data Integrity:\n\t- No valid `obj.id` associated with response\n' % (
        target.id,
        str(target.history_id)
      )
    )

  return doi_id

def find_registered_doi(entity, timeout=REQ_TIMEOUT, use_proxy=True, force_debug=False):
  """
  Attempts to find a DOI object registred for the specified entity 

  Args:
    entity        (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` specifying the entity of interest
    timeout                  (number): request timeout duration in seconds; defaults to `5s` (_i.e._ `REQ_TIMEOUT` global const)
    use_proxy                  (bool): optionally specify whether to use HTTP/S proxy targets; defaults to `True`
    force_debug                (bool): optionally specify whether to require debug mode, forcing the use of the DataCite API test server; defaults to `False`

  Returns:
    (Dict|None): if found then (a) a `Dict[Str,Any]` describing the DOI object registred for this entity, or if not found, (b) a `NoneType` value

  Raises:
    ValueError: raised on entity resolution failure
    RuntimeError: raised for known, handled error cases in `try-catch` block
    BaseException: raised as a result of unhandled errors in `try-catch` block
  """
  target = QueuedDOI.resolve_entity(entity)
  if target is None:
    raise ValueError(
      '[DOI::FindReg::Invalid] Failed to resolve entity, expected `dict`|`HistoricalGenericEntity` but got %s' % (
        type(entity).__name__ if entity is not None else 'NoneType'
      )
    )

  proxies = PROXIES_URL if use_proxy else None
  identifier = '%s%%2F%d' % (target.id, target.history_id)
  auth_token = compute_token(settings.DOI_USERNAME, settings.DOI_PASSWORD)

  dbg = is_debug_env() if not force_debug else True
  url = (
    (DataciteEndpoints.TEST.value if dbg else DataciteEndpoints.PROD.value) \
    + (DOI_QUERY % {
      'prefix': settings.DOI_PREFIX,
      'identifier': identifier,
    })
  )

  status = None
  try:
    response = requests.get(
      url,
      headers={
        'accept': 'application/vnd.api+json',
        'content-type': 'application/json',
        'Authorization': 'Basic %s' % auth_token,
      },
      proxies=proxies,
      timeout=timeout
    )

    status = next((x for x in list(HTTPStatus) if x.value == response.status_code), None)

    # Successful cases
    if response.ok and isinstance(status, HTTPStatus) and is_success(status):
      result = response.json()
      print(result)
      result = result.get('data', None) if isinstance(result, dict) else None

      if not isinstance(result, list):
        raise RuntimeError(
          '[DOI<id: %s>::FindReg::RuntimeError] Data Integrity:\n\t- Expected `data` key-value pair describing `list` but got %s\n' % (
            identifier,
            type(result).__name__
          )
        )

      if len(result) < 1:
        return None

      result = result.pop(0)
      if not isinstance(result, dict):
        raise RuntimeError(
          '[DOI<id: %s>::FindReg::RuntimeError] Data Integrity:\n\t- Expected `data[0]` to specify a `dict` but got %s\n' % (
            identifier,
            type(result).__name__
          )
        )

      doi_id = result.get('id')
      if not isinstance(doi_id, str) or gen_utils.is_empty_string(doi_id):
        raise RuntimeError(
          '[DOI<id: %s>::FindReg::RuntimeError] Data Integrity:\n\t- No valid `data[0].id` associated with response\n' % (
            identifier,
          )
        )

      return result

    # Failure cases
    if not isinstance(status, HTTPStatus) or not is_response_err(status):
      # Unknown, unexpected response/error
      body = ''
      with suppress(BaseException):
        body = response.text

      if not isinstance(body, str) or gen_utils.is_empty_string(body):
        body = 'No response `text` available'

      raise Exception(
        '[DOI<id: %s>::FindReg::UnknownError<status: %s>] Unknown Error:\n\t- Phrase: %s\n\t- Text Response:\n%s' % (
          identifier,
          str(status.value) if isinstance(status, HTTPStatus) else 'UNDEF',
          status.phrase or '' if isinstance(status, HTTPStatus) else 'UNDEF',
          body,
        )
      )
    elif is_client_err(status):
      # Client error
      result = response.json()
      raise RuntimeError(
        '[DOI<id: %s>::FindReg::ClientError<status: %d>] Client Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2),
        )
      )
    elif is_server_err(status):
      # Server error
      result = response.json()
      raise RuntimeError(
        '[DOI<id: %s>::FindReg::ServerError<status: %d>] Server Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2),
        )
      )
  except json.decoder.JSONDecodeError as e:
    raise RuntimeError(
      '[DOI<id: %s>::FindReg::JsonError] Failed to decode JSON:\n\t- HttpStatus: %d\n\t- Phrase: %s\n\t- Trace:\n%s' % (
        identifier,
        status.value,
        status.phrase or '',
        ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
      )
    )
  except requests.exceptions.RequestException as e:
    raise RuntimeError(
      '[DOI<id: %s>::FindReg::RequestException] Failed to make Request:\n\t- Trace:\n%s' % (
        identifier,
        ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
      )
    )
  except Exception as e:
    raise e


# DOI registration request callable(s)
def register_doi(entity, timeout=REQ_TIMEOUT, compute_brand=True, use_proxy=True, force_debug=False):
  """
  Attempts to synchronously register & publish a DOI for the given entity

  Args:
    entity        (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` specifying the entity to publish
    timeout                  (number): request timeout duration in seconds; defaults to `5s` (_i.e._ `REQ_TIMEOUT` global const)
    compute_brand              (bool): optionally specify whether to compute the `Brand` context from the `entity`; defaults to `True`
    use_proxy                  (bool): optionally specify whether to use HTTP/S proxy targets; defaults to `True`
    force_debug                (bool): optionally specify whether to require debug mode, forcing the use of the DataCite API test server; defaults to `False`

  Returns:
    (bool): reflects successful state of the operation

  Raises:
    ValueError: raised on entity resolution failure
    RuntimeError: raised for known, handled error cases in `try-catch` block
    BaseException: raised as a result of unhandled errors in `try-catch` block
  """
  target = QueuedDOI.resolve_entity(entity)
  if target is None:
    raise ValueError(
      '[DOI::Reg::Invalid] Failed to resolve entity, expected `dict`|`HistoricalGenericEntity` but got %s' % (
        type(entity).__name__ if entity is not None else 'NoneType'
      )
    )

  dbg = is_debug_env() if not force_debug else True
  fmt = DataciteFormats.TEST.value if dbg else DataciteFormats.PROD.value
  url = DataciteEndpoints.TEST.value if dbg else DataciteEndpoints.PROD.value

  ref = find_registered_ident(target, timeout=timeout, use_proxy=use_proxy, force_debug=force_debug)
  if isinstance(ref, str) and not gen_utils.is_empty_string(ref):
    doi_url = fmt % { 'id': ref }
    return update_doi(target, doi_url)

  proxies = PROXIES_URL if use_proxy else None
  identifier = '%s/%d' % (target.id, target.history_id)
  auth_token = compute_token(settings.DOI_USERNAME, settings.DOI_PASSWORD)

  brand_trg = None
  if compute_brand:
    brand_trg = target.brands if isinstance(target.brands, list) else []
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
        'id': target.id,
        'history_id': target.history_id,
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
                'name': target.author,
              }
            ],
            'titles': [
              {
                'title': target.name
              }
            ],
            'publisher': 'PhenotypeLibrary',
            'publicationYear': gen_utils.parse_int(target.updated.year),
            'types': {
              'resourceTypeGeneral': 'Model'
            },
            'url': url_target,
            'alternateIdentifiers': [
              {
                'alternateIdentifier': target.id,
                'alternateIdentifierType': 'Phenotype Library PHID',
              },
              {
                'alternateIdentifier': identifier,
                'alternateIdentifierType': 'Phenotype Library Identifier',
              }
            ],
            'relatedIdentifiers': relations,
          },
        },
      },
      headers={
        'accept': 'application/vnd.api+json',
        'content-type': 'application/json',
        'Authorization': 'Basic %s' % auth_token,
      },
      proxies=proxies,
      timeout=timeout
    )

    status = next((x for x in list(HTTPStatus) if x.value == response.status_code), None)

    # Successful cases
    if response.ok and isinstance(status, HTTPStatus) and is_success(status):
      result = response.json()
      doi_id = result.get('data', {}).get('id')
      if not isinstance(doi_id, str) or gen_utils.is_empty_string(doi_id):
        raise RuntimeError(
          '[DOI<id: %s>::Reg::RuntimeError] Data Integrity:\n\t- No valid `data.id` associated with response\n' % (
            identifier,
          )
        )

      doi_url = fmt % { 'id': doi_id }
      return update_doi(target, doi_url)

    # Failure cases
    if not isinstance(status, HTTPStatus) or not is_response_err(status):
      # Unknown, unexpected response/error
      body = ''
      with suppress(BaseException):
        body = response.text

      if not isinstance(body, str) or gen_utils.is_empty_string(body):
        body = 'No response `text` available'

      raise Exception(
        '[DOI<id: %s>::Reg::UnknownError<status: %s>] Unknown Error:\n\t- Phrase: %s\n\t- Text Response:\n%s' % (
          identifier,
          str(status.value) if isinstance(status, HTTPStatus) else 'UNDEF',
          status.phrase or '' if isinstance(status, HTTPStatus) else 'UNDEF',
          body,
        )
      )
    elif is_client_err(status):
      # Client error
      result = response.json()
      raise RuntimeError(
        '[DOI<id: %s>::Reg::ClientError<status: %d>] Client Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2),
        )
      )
    elif is_server_err(status):
      # Server error
      result = response.json()
      raise RuntimeError(
        '[DOI<id: %s>::Reg::ServerError<status: %d>] Server Error:\n\t- Phrase: %s\n\t- JSON Response:\n%s' % (
          identifier,
          status.value,
          status.phrase or '',
          json.dumps(result, indent=2),
        )
      )
  except json.decoder.JSONDecodeError as e:
    raise RuntimeError(
      '[DOI<id: %s>::Reg::JsonError] Failed to decode JSON:\n\t- HttpStatus: %d\n\t- Phrase: %s\n\t- Trace:\n%s' % (
        identifier,
        status.value,
        status.phrase or '',
        ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
      )
    )
  except requests.exceptions.RequestException as e:
    raise RuntimeError(
      '[DOI<id: %s>::Reg::RequestException] Failed to make Request:\n\t- Trace:\n%s' % (
        identifier,
        ''.join(traceback.format_exception(type(e), e, e.__traceback__)),
      )
    )
  except Exception as e:
    raise e


# DOI registration & publication task(s)
@celery.shared_task(name='publish_doi_task')
def publish_doi_task(entity, timeout=REQ_TIMEOUT, upd_register=True):
  """
  Async DOI publishing job registered with Celery

  Args:
    entity  (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` specifying the entity to publish
    timeout            (number): request timeout duration in seconds; defaults to `5s` (_i.e._ `REQ_TIMEOUT` global const)
    upd_register         (bool): specifies whether the register should be immediately updated after operation; defaults to `True`

  Returns:
    (bool): reflecting the success status of this async operation
  """
  if not settings.DOI_ACTIVE:
    return True

  task_log = celery.utils.log.get_task_logger('cll')

  target = QueuedDOI.resolve_entity(entity)
  if target is None:
    task_log.warning(
      '[DOI::PublishTask::Invalid] Failed to resolve entity, expected `dict`|`HistoricalGenericEntity` but got %s' % (
        type(entity).__name__ if entity is not None else 'NoneType'
      )
    )
    return False

  try:
    register_doi(target, timeout=timeout)
  except Exception as e:
    task_log.warning(
      '[DOI::PublishTask::Entity<id: %(id)s, history_id: %(ver)s>] DOI registration added to queue after failure of async DOI publish job with exception:\n\n%(err)s\n' % {
        'id': target.id,
        'ver': target.history_id,
        'err': ''.join(traceback.format_exception(type(e), e, e.__traceback__))
      }
    )

    if upd_register:
      reg = QueuedDOI.register(target, bubble_errors=True)
      err = reg.get('errors')
      if isinstance(err, dict):
        for x in err.values():
          task_log.error(
            '[DOI::PublishTask::Entity<id: %(id)s, history_id: %(ver)s>] Failed to register entity on failure queue:\n\n%(err)s\n' % {
              'id': target.id,
              'ver': target.history_id,
              'err': x,
            }
          )

    return False
  else:
    task_log.info(
      '[DOI::PublishTask::Entity<id: %(id)s, history_id: %(ver)s>] Successfully registered DOI' % {
        'id': target.id,
        'ver': target.history_id,
      }
    )

    if upd_register:
      QueuedDOI.unregister(target)
    return True

@celery.shared_task(bind=True)
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

  task_log = celery.utils.log.get_task_logger('cll')
  registrable = []
  unregistrable = []
  for index, ent in enumerate(queue):
    if not isinstance(ent, dict):
      task_log.warning(
        '[DOI::CronJob::Invalid] Expected queued entity at Index<%d> as typeof `dict` but got type<`%s`>' % (
          index,
          type(ent).__name__,
        )
      )
      continue

    idents = {
      'id': ent.get('trg_id', None),
      'history_id': ent.get('trg_ver', None),
    }

    entity = QueuedDOI.resolve_entity(idents)
    if entity is None:
      task_log.warning(
        '[DOI::CronJob::Invalid] Failed to resolve entity at Index<%d> where recorded idents:\n%s\n' % (
          index,
          json.dumps(idents, indent=2),
        )
      )
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
      registered = publish_doi_task(entity, upd_register=False)
    except:
      registered = False

    register = unregistrable if registered else registrable
    register.append(entity)

  if len(registrable) > 0:
    with suppress(BaseException):
      QueuedDOI.register(*registrable)
      task_log.info('[DOI::CronJob::Failure] Reregistred failed task queue of size: %d' % len(registrable))

  if len(unregistrable) > 0:
    with suppress(BaseException): 
      QueuedDOI.unregister(*unregistrable)
      task_log.info('[DOI::CronJob::Success] Unregistred failed task queue of size: %d' % len(registrable))

  return True
