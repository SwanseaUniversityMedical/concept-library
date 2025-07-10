from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly

import math
import psycopg2

from ...entity_utils import (
    api_utils, permission_utils,
    concept_utils, gen_utils, constants
)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concepts(request):
    """
        Get all Concepts accessible to the user, optionally provide parameters to filter the resultset.

        Available API parameters can be derived from the [Reference Data](/reference-data/) page, _e.g._ in the case of `tag` or `collection` ID identifiers.

        Endpoint query parameters:

        | Param           | Type                        | Default            | Desc                                                                                                                          |
        |-----------------|-----------------------------|--------------------|-------------------------------------------------------------------------------------------------------------------------------|
        | search          | `str`                       | `NULL`             | Full-text search across Concept `name` and `description` fields (trigram, fuzzy)                                              |
        | page            | `number`                    | `1`                | Page cursor                                                                                                                   |
        | page_size       | `enum`/`int`                | `1` (_20_ results) | Page size enum, where `1` = 20, `2` = 50 & `3` = 100 rows                                                                     |
        | no_pagination   | `[empty]`                   | `NULL`             | You can append this parameter to your query to disable pagination                                                             |
        | phenotype_id    | `str`/`str[]`               | `NULL`             | Either (a) a Phenotype ID or (b) a list of comma-delimited Phenotype IDs                                                      |
        | phenotype_owner | `str`/`str[]`               | `NULL`             | An alias of the `phenotype_id` parameter; see `phenotype_id` above                                                            |
        | tags            | `int`/`int[]`               | `NULL`             | Either (a) a Tag ID or (b) a list of comma-delimited Tag IDs                                                                  |
        | collections     | `int`/`int[]`               | `NULL`             | Either (a) a Collection ID or (b) a list of comma-delimited Collection IDs                                                    |
        | coding_system   | `int`/`int[]`               | `NULL`             | Either (a) a Coding System ID or (b) a list of comma-delimited Coding System IDs                                              |
        | owner           | `int`/`str`/`str[]`/`int[]` | `NULL`             | A reference to the Owner ID/Name, either (a) a Name `str` / ID `int` or (b) a comma-delimited list of either type             |
        | organisation    | `int`/`str`/`str[]`/`int[]` | `NULL`             | A reference to the Organisation ID/Name, either (a) a Slug/Name `str` / ID `int` or (b) a comma-delimited list of either type |
    """

    # Handle valid query parameters
    query_targets = {}
    query_clauses = []

    phenotype_owner = request.query_params.get('phenotype_id') or request.query_params.get('phenotype_owner')
    if not gen_utils.is_empty_string(phenotype_owner):
        query_targets.update({ 'phenotype_id': phenotype_owner.upper().split(',') })
        query_clauses.append(psycopg2.sql.SQL('''concept.phenotype_id = any(%(phenotype_id)s)'''))

    tags = request.query_params.get('tags')
    if not gen_utils.is_empty_string(tags):
        tags = gen_utils.parse_as_int_list(tags)
        if len(tags) > 0:
            query_targets.update({ 'tags_id': tags })
            query_clauses.append(psycopg2.sql.SQL('''entity.tags && %(tags_id)s::int[]'''))

    collections = request.query_params.get('collections')
    if not gen_utils.is_empty_string(collections):
        collections = gen_utils.parse_as_int_list(collections)
        if len(collections) > 0:
            query_targets.update({ 'collections_id': collections })
            query_clauses.append(psycopg2.sql.SQL('''entity.collections && %(collections_id)s::int[]'''))

    coding_system = request.query_params.get('coding_system')
    if not gen_utils.is_empty_string(coding_system):
        coding_system = gen_utils.parse_as_int_list(coding_system)
        if len(coding_system) > 0:
            query_targets.update({ 'coding_system_ids': coding_system })
            query_clauses.append(psycopg2.sql.SQL('''historical.coding_system_id = any(%(coding_system_ids)s::int[])'''))

    owner = request.query_params.get('owner')
    if not gen_utils.is_empty_string(owner):
        owner = owner.lower().split(',')
        owner_ids = []
        owner_names = []
        for val in owner:
            idnt = gen_utils.parse_int(val, default=None)
            if idnt:
                owner_ids.append(idnt)
                continue
            owner_names.append(val)

        if len(owner_ids) > 0 and len(owner_names) > 0:
            query_targets.update({ 'owner_ids': owner_ids, 'owner_names': owner_names })
            query_clauses.append(psycopg2.sql.SQL('''(owner.id is not null and (owner.id = any(%(owner_ids)s::int[]) or lower(owner.username) = any(%(owner_names)s)))'''))
        elif len(owner_ids) > 0:
            query_targets.update({ 'owner_ids': owner_ids })
            query_clauses.append(psycopg2.sql.SQL('''entity.owner_id = any(%(owner_ids)s::int[])'''))
        elif len(owner_names) > 0:
            query_targets.update({ 'owner_names': owner_names })
            query_clauses.append(psycopg2.sql.SQL('''(owner.id is not null and lower(owner.username) = any(%(owner_names)s))'''))

    orgs = request.query_params.get('organisation')
    if not gen_utils.is_empty_string(orgs):
        orgs = orgs.lower().split(',')
        org_ids = []
        org_names = []
        for val in orgs:
            idnt = gen_utils.parse_int(val, default=None)
            if idnt:
                org_ids.append(idnt)
                continue
            org_names.append(val)

        if len(org_ids) > 0 and len(org_names) > 0:
            query_targets.update({ 'org_ids': org_ids, 'org_names': org_names })
            query_clauses.append(psycopg2.sql.SQL('''(org.id is not null and (org.id = any(%(org_ids)s::int[]) or lower(org.name) = any(%(org_names)s) or lower(org.slug) = any(%(org_names)s)))'''))
        elif len(org_ids) > 0:
            query_targets.update({ 'org_ids': org_ids })
            query_clauses.append(psycopg2.sql.SQL('''(org.id is not null and org.id = any(%(org_ids)s::int[]))'''))
        elif len(org_names) > 0:
            query_targets.update({ 'org_names': org_names })
            query_clauses.append(psycopg2.sql.SQL('''(org.id is not null and lower(org.name) = any(%(org_names)s) or lower(org.slug) = any(%(org_names)s))'''))

    search = request.query_params.get('search')
    if gen_utils.is_empty_string(search) or len(search) < 3:
        search = None
    else:
        query_targets.update({ 'search_query': search })
        query_clauses.append(psycopg2.sql.SQL('''(
            setweight(to_tsvector('pg_catalog.english', coalesce(historical.name,'')), 'A') ||
            setweight(to_tsvector('pg_catalog.english', coalesce(historical.description,'')), 'B')
        ) @@ to_tsquery('pg_catalog.english', replace(to_tsquery('pg_catalog.english', concat(regexp_replace(trim(%(search_query)s), '\W+', ':* & ', 'gm'), ':*'))::text, '<->', '|'))
        '''))

    # Resolve pagination behaviour
    page = request.query_params.get('page', None)
    page = gen_utils.try_value_as_type(page, 'int')
    page = max(page, 1) if isinstance(page, int) else 1

    page_size = None
    page_details = None
    should_paginate = 'no_pagination' not in request.query_params.keys()
    if should_paginate:
        page_size = request.query_params.get('page_size', None)
        page_size = gen_utils.try_value_as_type(page_size, 'int', default=None)

        if isinstance(page_size, int):
            tmp = constants.PAGE_RESULTS_SIZE.get(str(page_size), None)
            if isinstance(tmp, int):
                page_size = tmp
            elif page_size not in list(constants.PAGE_RESULTS_SIZE.values()):
                page_size = None

        if not isinstance(page_size, int):
            page_size = constants.PAGE_RESULTS_SIZE.get('1')

        should_paginate = True

        page_details = {
            'offset_start': (page - 1)*page_size,
            'offset_end': page*page_size,
            'page_size': page_size,
        }

    user = request.user
    if not user or not user.is_authenticated:
        user_id = None
        cte = psycopg2.sql.SQL('''
        with
          visible_concepts as (
            select
                id as phenotype_id,
                cast(concepts->>'concept_id' as integer) as concept_id,
                cast(concepts->>'concept_version_id' as integer) as concept_version_id,
                true as is_published
              from (
                select id,
                       concepts
                  from public.clinicalcode_historicalgenericentity as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                 where
                   not exists (
                      select *
                        from public.clinicalcode_genericentity as ge
                       where ge.is_deleted = true and ge.id = entity.id
                   )
                   and entity.publish_status = %(publish_status)s
              ) results
          ),
          accessible_concepts as (
            select
                phenotype_id,
                concept_id,
                max(concept_version_id) as concept_version_id
              from visible_concepts
             group by phenotype_id, concept_id
          )
        ''')
    else:
        user_id = user.id
        cte = psycopg2.sql.SQL('''
        with
          matched_concepts as (
            select
			    entity.id as phenotype_id,
				concept.id as concept_id,
				concept.history_id as concept_version_id,
                (entity.publish_status = 2) as is_published
			  from public.clinicalcode_historicalconcept as concept
			  join public.clinicalcode_genericentity as entity
			    on entity.id = concept.phenotype_owner_id
             where entity.publish_status = %(publish_status)s
                or (
                  exists (
                    select 1
                      from public.auth_user_groups as t
                     where t.user_id = %(user_id)s and t.group_id = entity.group_id
                  )
                  and entity.group_access = %(gaccess)s
                )
                or entity.owner_id = %(user_id)s
                or entity.world_access = %(waccess)s
          ),
          unmatched_concepts as (
            select
                cast(null as varchar(50)) as phenotype_id,
                live.id as concept_id,
                historical.history_id as concept_version_id,
                false as is_published
              from public.clinicalcode_concept as live
              join public.clinicalcode_historicalconcept as historical
                using (id)
              left join matched_concepts as mtchs
                on mtchs.concept_id = live.id
             where live.owner_id = %(user_id)s
               and mtchs.concept_id is null
          ),
          visible_concepts as (
            select *
              from matched_concepts
             union
            select *
              from unmatched_concepts
          ),
          accessible_concepts as (
            select
                phenotype_id,
                concept_id,
                max(concept_version_id) as concept_version_id
              from visible_concepts
             group by phenotype_id, concept_id
          )
        ''')

    selection = psycopg2.sql.SQL('''
          selected_concepts as (
            select
                historical.name,
                concept.phenotype_id,
                concept.concept_id,
                concept.concept_version_id,
                historical.history_date,
                json_build_object(
                    'id', coding.id,
                    'name', coding.name,
                    'description', coding.description
                ) as coding_system,
                row_number() over (order by concept.concept_id asc) as rn
              from accessible_concepts as concept
              join public.clinicalcode_historicalconcept as historical
                on historical.id = concept.concept_id and historical.history_id = concept.concept_version_id
              join public.clinicalcode_codingsystem as coding
                on coding.id = historical.coding_system_id
              left join public.clinicalcode_genericentity as entity
                on entity.id = concept.phenotype_id
              left join public.auth_user as owner
                on owner.id = entity.owner_id
              left join public.auth_group as org
                on org.id = entity.group_id''')

    if len(query_clauses) > 0:
        selection += psycopg2.sql.SQL('''\n             where ''') \
            + psycopg2.sql.SQL('and ').join(query_clauses)

    selection += psycopg2.sql.SQL('''
          ),
          total_count as (
            select max(rn) as row_count
              from selected_concepts
          )
    ''')

    versions = psycopg2.sql.SQL('''
          concept_versions as (
            select distinct on (visible.concept_version_id)
                concept.phenotype_id,
                concept.concept_id,
                visible.concept_version_id,
                json_build_object(
                    'version_id', visible.concept_version_id,
                    'is_published', (visible.is_published),
                    'is_latest', (visible.concept_version_id = concept.concept_version_id)
                ) as version_history
              from selected_concepts as concept
              join visible_concepts as visible
                on visible.concept_id = concept.concept_id
          )
    ''')

    query_targets |= {
        'user_id': user_id,
        'publish_status': 2,
        'gaccess': 2,
        'waccess': 2
    }

    with connection.cursor() as cursor:
        if should_paginate:
            sql = psycopg2.sql.SQL('''
            select
                (select t.row_count from total_count as t) as total_rows,
                qry.data
              from (
                select
                    json_agg(json_build_object(
                        'name', sel.name,
                        'friendly_id', concat('C', sel.concept_id::text),
                        'concept_id', sel.concept_id,
                        'concept_version_id', sel.concept_version_id,
                        'history_date', sel.history_date,
                        'phenotype_owner', sel.phenotype_id,
                        'coding_system', sel.coding_system,
                        'version_history', ver.version_history
                    ) order by sel.rn asc) as data
                  from selected_concepts as sel
                  left join (
                    select 
                        phenotype_id,
                        concept_id,
                        json_agg(version_history) as version_history
                      from concept_versions
                     group by phenotype_id, concept_id
                  ) as ver
                    on sel.concept_id = ver.concept_id and sel.phenotype_id = ver.phenotype_id
                 where sel.rn >= %(offset_start)s and sel.rn < %(offset_end)s
                 limit %(page_size)s
              ) as qry;
            ''')

            query_targets |= page_details
        else:
            sql = psycopg2.sql.SQL('''
            select
                (select t.row_count from total_count as t) as total_rows,
                qry.data
              from (
                select
                    json_agg(json_build_object(
                        'name', sel.name,
                        'concept_id', sel.concept_id,
                        'concept_version_id', sel.concept_version_id,
                        'history_date', sel.history_date,
                        'phenotype_owner', sel.phenotype_id,
                        'coding_system', sel.coding_system,
                        'version_history', ver.version_history
                    ) order by sel.rn asc) as data
                  from selected_concepts as sel
                  left join (
                    select 
                        phenotype_id,
                        concept_id,
                        json_agg(version_history) as version_history
                      from concept_versions
                     group by phenotype_id, concept_id
                  ) as ver
                    on sel.concept_id = ver.concept_id and sel.phenotype_id = ver.phenotype_id
              ) as qry;
            ''')

        sql = psycopg2.sql.Composed([
            psycopg2.sql.SQL(',').join([cte, selection, versions]),
            sql,
        ])

        cursor.execute(sql, params=query_targets)

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        results = results[0] if len(results) > 0 else {}

        rows = results.get('data', list())
        if should_paginate:
            row_count = gen_utils.parse_int(results.get('total_rows', 0), default=0)
            page_size = page_size if isinstance(page_size, int) else row_count
            total_pages = math.ceil(row_count / page_size)

            results = {
                'page': min(page, total_pages),
                'total_pages': total_pages,
                'page_size': page_size,
                'data': rows
            }
        else:
            results = rows

        return Response(
            data=results,
            status=status.HTTP_200_OK
        )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concept_detail(request, concept_id, version_id=None, export_codes=False, export_component=False):
    """
        Get the detail of specified Concept by `concept_id`, optionally target a specific version using the `version_id` endpoints, and/or export the Concept codelist/components.
    """
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    # Get historical concept
    historical_concept_response = api_utils.exists_historical_concept(
        request, concept_id, historical_id=version_id
    )
    if isinstance(historical_concept_response, Response):
        return historical_concept_response
    historical_concept = historical_concept_response

    # Check if the user has the permissions to view this concept version
    user_can_access = permission_utils.can_user_view_concept(request, historical_concept)
    if not user_can_access:
        return Response(
            data={
                'message': 'Entity version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )

    if export_codes:
        # Build only the codelist
        concept_codes = concept_utils.get_concept_codelist(
            historical_concept.id,
            historical_concept.history_id,
            incl_attributes=True
        )
        for code in concept_codes:
            attributes = code.get('attributes')
            headers = historical_concept.code_attribute_header
            if attributes is not None and headers is not None:
                code['attributes'] = dict(zip(
                    headers, attributes
                ))
        
        return Response(
            data=concept_codes,
            status=status.HTTP_200_OK
        )
    elif export_component:
        # Build component data
        entity_id = request.query_params.get('requested_entity', None)
        entity_id = gen_utils.try_value_as_type(entity_id, 'string', default=None)

        concept_data = concept_utils.get_clinical_concept_data(
            historical_concept.id,
            historical_concept.history_id,
            remove_userdata=True,
            hide_user_details=True,
            include_component_codes=False,
            include_attributes=True,
            requested_entity_id=entity_id,
            include_reviewed_codes=True,
            derive_access_from=request
        )

        return Response(
            data=concept_data,
            status=status.HTTP_200_OK
        )
    
    # Build the whole concept detail
    concept_data = concept_utils.get_clinical_concept_data(
        historical_concept.id,
        historical_concept.history_id,
        include_attributes=True,
        format_for_api=True
    )

    # Append concept version information
    concept_data['version_history'] = api_utils.get_concept_version_history(
        request, concept_id
    )

    return Response(
        data=concept_data,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_concept_version_history(request, concept_id):
    """
        Get version history of a specific Concept, using `concept_id`
    """
    # Check concept with this id exists
    concept_response = api_utils.exists_concept(concept_id)
    if isinstance(concept_response, Response):
        return concept_response
    
    return Response(
        data=api_utils.get_concept_version_history(request, concept_id), 
        status=status.HTTP_200_OK
    )
