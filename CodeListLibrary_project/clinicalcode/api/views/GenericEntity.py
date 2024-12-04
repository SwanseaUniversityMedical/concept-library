from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings
from django.core.exceptions import BadRequest

from ...models import GenericEntity, Template
from ...entity_utils import permission_utils
from ...entity_utils import template_utils
from ...entity_utils import search_utils
from ...entity_utils import model_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

""" Create/Update GenericEntity """

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_generic_entity(request):
    """
        Create a generic entity from request body, must be formatted in terms
          of a specific layout and is validated against it
    """
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.CREATE.value
    )
    if isinstance(form, Response):
        return form
        
    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully created entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_generic_entity(request):
    """
        Update a generic entity from request body, must be formatted in terms
          of a specific layout and is validated against it

    """
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.UPDATE.value
    )
    if isinstance(form, Response):
        return form

    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully updated entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

""" Get GenericEntity version history """

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entity_version_history(request, phenotype_id=None):
    """
        Get version history of specific entity, using phenotype_id

    """    
    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(phenotype_id)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(phenotype_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    return Response(
        data=api_utils.get_entity_version_history(request, phenotype_id), 
        status=status.HTTP_200_OK
    )

""" Get GenericEntities """

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
@gen_utils.measure_perf
def get_generic_entities(request, should_paginate=True):
    """
        Get all generic entities accessible to the API user; see [Reference Data](/reference-data/) page
        for available API parameters for individual templates.

        Other available parameters:
          - `page` (`int`) - the page cursor
          - `page_size` (`int`) - the desired page size from one `20`, `50`, `100` (or the enum value of `1`, `2`, `3`)
          - `should_paginate` (`bool`) - optionally turn off pagination; defaults to `True`

    """

    # Base params
    params = { key: value for key, value in request.query_params.items() }
    tmpl_clauses = []
    accessible_clauses = []

    search = params.pop('search', None)

    page = params.pop('page', None)
    page = gen_utils.try_value_as_type(page, 'int')
    page = max(page, 1) if isinstance(page, int) else 1

    page_size = None
    if page:
        page_size = params.pop('page_size', None)
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

    # Filter by template id and version
    template_id = params.pop('template_id', None)
    template_id = gen_utils.try_value_as_type(template_id, 'int')

    template_version_id = params.pop('template_version_id', None)
    template_version_id = gen_utils.try_value_as_type(template_version_id, 'int')

    if isinstance(template_id, int):
        template = Template.objects.filter(id=template_id)
        if not template.exists():
            return Response(
                data={
                    'message': 'Template with specified id does not exist'
                },
                content_type='json',
                status=status.HTTP_404_NOT_FOUND
            )

        template = template.first()
        if isinstance(template_version_id, int):
            template = template.history.filter(template_version=template_version_id)
            if not template.exists():
                return Response(
                    data={
                        'message': 'Template with specified version id does not exist'
                    },
                    content_type='json',
                    status=status.HTTP_404_NOT_FOUND
                )

            tmpl_clauses.append('''(template.id = %(template_id)s and template.template_version = %(template_version_id)s)''')
        else:
            tmpl_clauses.append('''template.id = %(template_id)s''')

    # Finalise accessibility clause(s)
    user_id = None
    brand_id = None
    group_ids = None

    brand = model_utils.try_get_brand(request)
    if brand is not None:
        brand_id = brand.id
        accessible_clauses.append('''%(brand_id)s = any(entity.brands)''')

    user = request.user if request.user and not request.user.is_anonymous else None
    user_clause = '''entity.publish_status = 2'''
    if user:
        user_id = user.id
        user_clause = f'''({user_clause} or entity.world_access = 2) or entity.owner_id = %(user_id)s'''

        groups = list(user.groups.all().values_list('id', flat=True))
        if len(groups) > 0:
            group_ids = [ gen_utils.parse_int(group) for group in groups ]
            user_clause = f'''{user_clause} or (entity.group_id = any(%(group_ids)s) and entity.group_access = any(array[2, 3]))'''

    accessible_clauses.append(f'({user_clause})')

    # Cache base params
    base_params = {
        'user_id': user_id,
        'brand_id': brand_id,
        'group_ids': group_ids,
        'template_id': template_id,
        'template_version_id': template_version_id,
    }

    # Query associated template(s)
    if len(tmpl_clauses) > 0:
        tmpl_clauses = 'and ' + ' and '.join(tmpl_clauses)
    else:
        tmpl_clauses = ''

    if len(accessible_clauses) > 0:
        accessible_clauses = 'and ' + ' and '.join(accessible_clauses)
    else:
        accessible_clauses = ''

    templates = Template.objects.raw(
        raw_query='''
            select t0.id, t0.template_version, t0.history_id
              from (
                select
                    template.id,
                    template.template_version,
                    template.history_id,
                    row_number() over (
                      partition by template.id, template.template_version
                      order by template.history_id desc
                    ) as rn_ref_n
                  from public.clinicalcode_historicaltemplate as template
                  join public.clinicalcode_historicalgenericentity as entity
                    on entity.template_id = template.id and entity.template_version = template.template_version
                 where (entity.is_deleted is null or entity.is_deleted = false)
                   %s
                   %s
              ) as t0
             where t0.rn_ref_n = 1
        ''' % (tmpl_clauses, accessible_clauses,),
        params=base_params
    )

    # Build parameter list
    param_keys = set(params.keys())
    metadata_filters = set([ key for key, value in constants.metadata.items() if 'search' in value ])
    metadata_filters = param_keys.intersection(metadata_filters)
    template_filters = param_keys.difference(metadata_filters)

    is_authed = not not user_id

    # Build metadata param(s)
    metadata_params = { }
    metadata_clauses = [ ]
    for key in metadata_filters:
        data = params.get(key)
        if data is None:
            continue

        field_data = constants.metadata.get(key)
        if not field_data or not field_data.get('active') or field_data.get('ignore'):
            continue

        if field_data.get('requires_auth') and not is_authed:
            continue

        validation = field_data.get('validation')
        field_type = validation.get('type') if validation is not None else None
        if not field_type:
            continue

        success, query, query_params = api_utils.build_query_string_from_param(
            key, data, validation, field_type,
            prefix='mt', is_dynamic=False
        )

        if success:
            metadata_params |= query_params
            metadata_clauses.append(query)

    if len(metadata_clauses) > 0:
        metadata_clauses = ' and '.join(metadata_clauses)
    else:
        metadata_clauses = None

    # Build template param(s)
    template_params = { }
    template_clauses = [ ]
    for template in templates:
        merged_definition = template_utils.get_merged_definition(template, default={})
        template_fields = template_utils.try_get_content(merged_definition, 'fields')

        opts = { }
        clauses = [ ]

        prefix = f'{template.id}_{template.template_version}'
        for key in template_filters:
            field_data = template_utils.try_get_content(template_fields, key)
            if field_data is not None:
                if not field_data.get('active') or not field_data.get('search') or field_data.get('ignore'):
                    continue

                if field_data.get('requires_auth') and not is_authed:
                    continue

                data = params.get(key)

                validation = field_data.get('validation')
                field_type = validation.get('type') if validation is not None else None
                if not field_type:
                    continue

                success, query, query_params = api_utils.build_query_string_from_param(
                    key, data, validation, field_type,
                    prefix=prefix, is_dynamic=True
                )

                if success:
                    opts |= query_params
                    clauses.append(query)
            else:
                query_opts = key.split('_')
                if query_opts[0] == field_data and len(query_opts) > 1:
                    continue

                field_ref = query_opts[0]
                subquery_ref = query_opts[1]

                field_data = template_utils.try_get_content(template_fields, field_ref)
                if field_data is None:
                    continue
                
                if not field_data.get('active') or not field_data.get('search') or field_data.get('ignore'):
                    continue

                if field_data.get('requires_auth') and not is_authed:
                    continue

                data = params.get(key)
                validation = field_data.get('validation')

                source = validation.get('source') if validation is not None else None
                field_type = validation.get('type') if validation is not None else None
                if source is None or field_type is None:
                    continue

                subqueries = source.get('subquery')
                valid_subquery = isinstance(subqueries.get(subquery_ref), dict) if subqueries is not None else False
                if not valid_subquery:
                    continue

                success, results = api_utils.build_template_subquery_from_string(
                    key, data, field_ref, subquery_ref,
                    validation, opts=query_opts[2:], prefix=prefix
                )

                if success:
                    opts |= results[1]
                    clauses.append(results[0])

        if len(clauses) > 0:
            clauses = ' and '.join(clauses)
            clauses = f'''(
                entity.template_id = {template.id}
                and entity.template_version = {template.template_version}
                and ({clauses})
            )'''

            template_params |= opts
            template_clauses.append(clauses)

    template_len = len(template_clauses)
    if template_len > 1:
        template_clauses = f'''( { ' or '.join(template_clauses) } )'''
    elif template_len > 0:
        template_clauses = ' or '.join(template_clauses)
    else:
        template_clauses = None

    # Query entities
    query_params = base_params | metadata_params | template_params

    query_clauses = 'where '
    if metadata_clauses and template_clauses:
        query_clauses = query_clauses + f'{metadata_clauses} and {template_clauses}'
    elif metadata_clauses:
        query_clauses = query_clauses + metadata_clauses
    elif template_clauses:
        query_clauses = query_clauses + template_clauses
    else:
        query_clauses = ''

    query = '''
    select *
      from entities t
    '''

    if isinstance(search, str) and len(search) > 0:
        query = query + '''
         where t.search_vector @@ to_tsquery(
            'pg_catalog.english',
            replace(websearch_to_tsquery('pg_catalog.english', %(search)s)::text || ':*', '<->', '|')
         )
        '''
        query_params.update({ 'search': search })

    try:
        if not user:
            accessible = f'''
            select t1.*
              from (
                select
                      entity.id,
                      entity.history_id,
                      row_number() over (
                      partition by entity.id
                        order by entity.history_id desc
                      ) as rn_ref_n
                  from public.clinicalcode_historicalgenericentity as entity
                  join public.clinicalcode_genericentity as live_entity
                    on entity.id = live_entity.id
                  join public.clinicalcode_historicaltemplate as template
                    on entity.template_id = template.id and entity.template_version = template.template_version
                  join public.clinicalcode_template as live_tmpl
                    on template.id = live_tmpl.id
                 where (live_entity.is_deleted is null or live_entity.is_deleted = false)
                   and (entity.is_deleted is null or entity.is_deleted = false)
                   and entity.publish_status = 2
                   {tmpl_clauses}
              ) as t0
              join public.clinicalcode_historicalgenericentity as t1
                on t0.id = t1.id
               and t0.history_id = t1.history_id
             where t0.rn_ref_n = 1
            '''
        else:
            accessible = f'''
            select t1.*
            from (
                select
                    entity.id,
                    entity.history_id,
                    row_number() over (
                        partition by entity.id
                        order by entity.history_id desc
                    ) as rn_ref_n
                 from public.clinicalcode_historicalgenericentity as entity
                 left join public.clinicalcode_genericentity as live_entity
                   on entity.id = live_entity.id
                 join public.clinicalcode_historicaltemplate as template
                   on entity.template_id = template.id and entity.template_version = template.template_version
                 join public.clinicalcode_template as live_tmpl
                   on template.id = live_tmpl.id
                where (live_entity.id is not null and (live_entity.is_deleted is null or live_entity.is_deleted = false))
                  and (entity.is_deleted is null or entity.is_deleted = false)
                    {accessible_clauses}
                    {tmpl_clauses}
             ) as t0
             join public.clinicalcode_historicalgenericentity as t1
               on t0.id = t1.id
              and t0.history_id = t1.history_id
            where t0.rn_ref_n = 1
            '''

        entities = GenericEntity.history.raw(
            raw_query='''
            with
                accessible as (
                    %(accessible)s
                ),
                entities as (
                    select *
                    from accessible as entity
                    %(clauses)s
                )

            %(query)s
             order by cast(regexp_replace(id::text, '[a-zA-Z]+', '') as integer) asc;

            ''' % {
                'query': query,
                'clauses': query_clauses,
                'accessible': accessible,
            },
            params=query_params
        )

        # Paginate results
        if should_paginate:
            entities = search_utils.try_get_paginated_results(
                request, entities, page, page_size=page_size
            )

        # Get details of each entity
        formatted_entities = []
        for entity in entities:
            entity_detail = api_utils.get_entity_detail(
                request, 
                entity.id, 
                entity, 
                is_authed, 
                fields_to_ignore=constants.ENTITY_LIST_API_HIDDEN_FIELDS, 
                return_data=True
            )

            if not isinstance(entity_detail, Response):
                formatted_entities.append(entity_detail)

        result = formatted_entities if not should_paginate else {
            'page': min(entities.paginator.num_pages, page),
            'total_pages': entities.paginator.num_pages,
            'page_size': page_size,
            'data': formatted_entities
        }

    except Exception as e:
        # log exception?
        raise BadRequest('Invalid request, failed to perform query')
    else:
        return Response(
            data=result,
            status=status.HTTP_200_OK
        )


""" Get GenericEntity detail """

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_entity_detail(request, phenotype_id, version_id=None, field=None):
    """
        Get detail of specified entity by phenotype_id, optionally target a specific
          version using version_id and/or target a specific entity field using
          field parameters
    """
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True

    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(phenotype_id)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(phenotype_id)
    if isinstance(entity_response, Response):
        return entity_response
    
    # Find latest historical id if not provided, and get first matching historical entity
    historical_entity_response = api_utils.exists_historical_entity(
        phenotype_id, request.user, historical_id=version_id
    )
    if isinstance(historical_entity_response, Response):
        return historical_entity_response
    historical_entity = historical_entity_response

    # Check if the user has the permissions to view this entity version
    user_can_access = permission_utils.can_user_view_entity(
        request, historical_entity.id, historical_entity.history_id
    )
    if not user_can_access:
        return Response(
            data={
                'message': 'Entity version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if field is not None:
        if template_utils.is_valid_field(historical_entity, field):
            return api_utils.get_entity_detail(
                request, 
                phenotype_id, 
                historical_entity, 
                user_authed, 
                target_field=field, 
                return_data=False
            )
        
        if field == 'codes':
            return api_utils.get_codelist_from_entity(historical_entity)
        
        return Response(
            data={
                'message': 'Field does not exist'
            }, 
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return api_utils.get_entity_detail(
        request, phenotype_id, historical_entity, user_authed
    )
