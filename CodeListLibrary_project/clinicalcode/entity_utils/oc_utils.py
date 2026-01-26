from rest_framework.test import APIRequestFactory, force_authenticate
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from io import StringIO
from http import HTTPStatus

import csv
import json
import time
import logging
import requests

from ..api.views.GenericEntity import create_generic_entity, update_generic_entity

logger = logging.getLogger(__name__)

REF_C_SYS = {
    'readv2': 5,
    'ctv3': 6,
    'icd10': 4,
    'snomedct': 9,
    'dmd': 23,
    'bnf': 11,
    'opcs4': 7
}

REF_LKUP = {
    'readv2': {
        'headers': [{ 'code': 'Readcode', 'desc': 'Disease'}],
    },
    'ctv3': {
        'headers': [
            { 'code': 'id', 'desc': 'term' },
            { 'code': 'code', 'desc': 'term' },
            { 'code': 'code', 'desc': 'description' },
            { 'code': 'ctv3code', 'desc': 'ctv3preferredtermdesc' },
            { 'code': 'ctv3code', 'desc': 'description' },
            { 'code': 'ctv3code', 'desc': 'ctv3_description' },
            { 'code': 'ctv3id', 'desc': 'ctvterm' },
            { 'code': 'ctv3id', 'desc': 'readterm' },
            { 'code': 'ctv3id', 'desc': 'ctv3preferredtermdesc' },
            { 'code': 'ctv3id', 'desc': 'readterm/ctv3preferredtermdesc' },
            { 'code': 'ctv3_id', 'desc': 'ctv3_name' }
        ]
    },
    'icd10': {
        'headers': [
            { 'code': 'code', 'desc': 'term' },
            { 'code': 'icd', 'desc': 'description' },
            { 'code': 'icd10_code', 'desc': 'name' },
            { 'code': 'icd_code', 'desc': 'diag_desc' }
        ]
    },
    'snomedct': {
        'headers': [
            { 'code': 'id', 'desc': 'name' },
            { 'code': 'id', 'desc': 'term' },
            { 'code': 'code', 'desc': 'term' },
            { 'code': 'code', 'desc': None },
            { 'code': 'code', 'desc': 'long_name' },
            { 'code': 'snomedcode', 'desc': 'ethnicity' }
        ]
    },
    'dmd': {
        'headers': [
            { 'code': 'code', 'desc': 'term' }
        ]
    },
    'bnf': {
        'headers': [
            { 'code': 'code', 'desc': 'term' }
        ]
    },
    'opcs4': {
        'headers': [
            { 'code': 'code', 'desc': 'term' },
            { 'code': 'code', 'desc': 'description' }
        ]
    }
}

def query_opencodelist_phenotypes(
    url,
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
    ],
    codelist=False
):
    """
      Attempts to query OpenCodelists Phenotypes API

      Args:
        req_timeout     (int): request timeout (in seconds)
        retry_attempts  (int): max num. of attempts for each page request
        retry_delay     (int): timeout, in seconds, between retry attempts (backoff algo)
        retry_codes    (list): a list of ints specifying HTTP Status Codes from which to trigger retry attempts
        codelist       (bool): boolean flag for retrieving a codelist

      Returns:
        dict containing the assoc. data
    """
    proxy = {
        'http': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/',
        'https': '' if settings.IS_DEVELOPMENT_PC else 'http://proxy:8080/'
    }

    response = None
    retry_attempts = max(retry_attempts, 0) + 1
    for attempts in range(0, retry_attempts, 1):
        try:
            response = requests.get(url, timeout=req_timeout, proxies=proxy)
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

    if not codelist:
        result = response.json()
        if not isinstance(result, dict):
            raise Exception(f'Invalid resultset, expected result as `dict` but got `{type(result)}`')
    else:
        result = []

        data = StringIO(response.text)
        data = csv.DictReader(data)
        data.fieldnames = [x.lower().strip() for x in data.fieldnames]
        for row in data:
            result.append(row)
        
        if not isinstance(result, list):
            raise Exception(f'Invalid resultset, expected result as `list` but got `{type(result)}`')

    return result

def collect_opencodelist_concept(data, full_slug):
    """
      Safely parses an OpenCodelist phenotype and formats to required CL format

      Args:
        data (dict): OpenCodelist concept data
        full_slug (text): OpenCodelist phenotype version slug

      Returns:
        A dict containing the parsed data
    """
    coding_system = data.get('coding_system_id')
    coding_system_id = REF_C_SYS.get(coding_system)
    if not coding_system_id:
        msg = f'Unable to sync OpenCodelist phenotype, failed to match coding system'
        logger.warning(msg)
        return None

    result = {
        'details': {
            'name': f'{full_slug} - Codes',
            'coding_system': coding_system_id,
            'code_attribute_header': []
        },
        'components': [],
        'is_new': True
    }

    try:
        codes = query_opencodelist_phenotypes(
            f'https://www.opencodelists.org/codelist/{full_slug}/download.csv',
            codelist=True
        )
    except Exception as e:
        msg = f'Unable to sync OpenCodelist phenotype, failed to download codelist:\n\n{str(e)}'
        logger.warning(msg)
        return None
    
    if len(codes) < 1:
        return None

    code_headers = list(codes[0].keys())

    code_column = None
    description_column = None
    for header in REF_LKUP.get(coding_system).get('headers'):
        ch = header.get('code') and header.get('code')
        dh = header.get('desc') and header.get('desc')
        if ch in code_headers and (not dh or dh in code_headers):
            code_column = ch
            description_column = dh
            break
    
    attribute_headers = [
        header for header in code_headers if header not in [code_column, description_column]
    ]
    attribute_headers = [
        header for header in attribute_headers if codes[0].get(header) is not None and not header.lower().startswith('unnamed')
    ]

    new_codes = []
    for code in codes:
        new_codes.append({
            'code': str(code.get(code_column)),
            'description': '' if not description_column else code.get(description_column),
            'attributes': [code.get(header) for header in attribute_headers]
        })

    result['details']['code_attribute_header'] = attribute_headers
    result['components'] = [{
        'name': f'{full_slug}',
        'logical_type': 'INCLUDE',
        'source_type': 'FILE_IMPORT',
        'codes': new_codes,
        'is_new': True
    }]

    return result

def collect_opencodelist_phenotype(
    data, 
    entity_id=None, 
    entity_version=None, 
    should_update=False
):
    """
      Safely parses an OpenCodelist phenotype and formats to required CL format

      Args:
        data (dict): OpenCodelist phenotype data
        entity_id (str): The id of the phenotype
        entity_version (int): The version id of the phenotype
        should_update (bool): Whether the phenotype should be formatted to update an existing one or not

      Returns:
        A dict containing the parsed data
    """
    full_slug = data.get('full_slug')

    version = data.get('versions')
    version = version[-1]
    version_slug = version.get('full_slug')

    definition = data.get('description')
    formatted_definition = 'This codelist was taken from [OpenCodelists](https://www.opencodelists.org/), created by [OpenSAFELY](https://www.opensafely.org/). We recommend viewing this Phenotype on the OpenCodelist website to view the most recent version.'
    if definition is not None and len(definition) > 1:
        formatted_definition += f'\n\n {definition}'
    formatted_definition += '\n\n © University of Oxford for the Bennett Institute for Applied Data Science 2025. This work may be copied freely for non-commercial research and study.'

    references = data.get('references')
    formatted_references = [
        { 'title': x.get('text'), 'url': x.get('url') } for x in references
    ]

    concept_information = collect_opencodelist_concept(data, version_slug)
    if concept_information is None:
        return None

    phenotype = {
        'method': 2 if should_update else 1,
        'data': {
            'name': data.get('name'),
            'author': data.get('organisation'),
            'definition': formatted_definition,
            'methodology': data.get('methodology'),
            'collections': [18, 31],
            'tags': [],
            'source_reference': f'https://www.opencodelists.org/codelist/{version_slug}',
            'references': formatted_references,
            'signed_off': [],
            'open_codelist_id': full_slug,
            'open_codelist_version_id': version.get('hash'),
            'open_codelist_version_tag': version.get('tag'),
            'coding_system_release': None,
            'concept_information': [concept_information],
            'organisation': 1
        },
        'template': {
            'id': 3,
            'version': 1
        }
    }

    if should_update:
        phenotype |= {
            "entity": {
                "id": entity_id,
                "version_id": entity_version
            }
        }

    return phenotype

def sync_opencodelist_phenotypes():
    """
      Attempts to sync the OpenCodelist phenotypes with those found through the OpenCodelist phenotypes API
    """
    try:
        result = query_opencodelist_phenotypes(
            url='https://www.opencodelists.org/api/v1/codelist/?description&methodology&references'
        )
    except Exception as e:
        msg = f'Unable to sync OpenCodelist phenotypes, failed to reach api with err:\n\n{str(e)}'
        logger.warning(msg)

        return {}, msg

    data = result.get('codelists')
    if not isinstance(data, list):
        msg = f'Invalid resultset, expected `codelists` as `list` but got `{type(data)}`'
        logger.warning(msg)

        return {}, msg

    datamap = {}
    phenotypes_to_check = []
    for current in data:
        full_slug = current.get('full_slug')

        latest_version = current.get('versions')
        latest_version = latest_version[-1]
        version_hash = latest_version.get('hash')

        is_version_downloadable = latest_version.get('downloadable')
        is_version_published = latest_version.get('status') == 'published'
        if not is_version_downloadable or not is_version_published:
            continue

        datamap[full_slug] = current
        phenotypes_to_check.append({
            'open_codelist_id': full_slug,
            'open_codelist_version_id': version_hash
        })

    with connection.cursor() as cursor:
        sql = '''
            with entities as (
                select
                    ge.id,
                    hge.history_id,
                    ge.template_data->>'open_codelist_id'::text as open_codelist_id,
                    ge.template_data->>'open_codelist_version_id'::text as open_codelist_version_id
                from public.clinicalcode_genericentity as ge
                join (
                    select id, max(history_id) as history_id
                    from public.clinicalcode_historicalgenericentity
                    group by id
                ) as hge
                  on ge.id = hge.id
                where ge.template_id = 3 
                  and ge.template_data ? 'open_codelist_id'
            ),
            datasource as (
                select *
                from jsonb_to_recordset(%(target)s::jsonb) as t(
                    open_codelist_id text,
                    open_codelist_version_id text
                )
            ),
            to_create as (
                select json_agg(json_build_object(
                        'open_codelist_id', ds.open_codelist_id,
                        'open_codelist_version_id', ds.open_codelist_version_id
                    )) as objs
                from datasource as ds
                left join entities as ent
                    on ent.open_codelist_id = ds.open_codelist_id
                where ent.id is null
            ),
            to_update as (
                select json_agg(json_build_object(
                        'entity_id', ent.id,
                        'version_id', ent.history_id,
                        'open_codelist_id', ds.open_codelist_id,
                        'open_codelist_version_id', ds.open_codelist_version_id
                    )) as objs
                from datasource as ds
                join entities as ent
                  on ent.open_codelist_id = ds.open_codelist_id
                 and ent.open_codelist_version_id <> ds.open_codelist_version_id
            )
            select 
                (select objs from to_create) as to_create,
                (select objs from to_update) as to_update;
        '''
        cursor.execute(sql, params={
            'target': json.dumps(phenotypes_to_check)
        })

        columns = [col[0] for col in cursor.description]
        result = dict(zip(columns, cursor.fetchone()))

        to_create = result.get('to_create')
        to_update = result.get('to_update')

        has_create = isinstance(to_create, list) and len(to_create) > 0
        has_update = isinstance(to_update, list) and len(to_update) > 0
        if not has_create and not has_update:
            return

        user = User.objects.get(id=1)
        factory = APIRequestFactory()

        if has_create:
            for row in to_create:
                form = collect_opencodelist_phenotype(
                    datamap.get(row.get('open_codelist_id'))
                )
                if not form:
                    continue

                request = factory.post(
                    '/api/v1/phenotypes/create?publish=true', 
                    form, 
                    content_type='application/json'
                )
                force_authenticate(request, user=user)
                create_generic_entity(request)

        if has_update:
            for row in to_update:
                entity_id = row.get('entity_id')
                entity_version_id = row.get('version_id')

                form = collect_opencodelist_phenotype(
                    datamap.get(row.get('open_codelist_id')),
                    entity_id=entity_id,
                    entity_version=entity_version_id,
                    should_update=True
                )
                if not form:
                    continue

                request = factory.put(
                    f'/api/v1/phenotypes/update?publish=true', 
                    form, 
                    content_type='application/json'
                )
                force_authenticate(request, user=user)
                update_generic_entity(request)
