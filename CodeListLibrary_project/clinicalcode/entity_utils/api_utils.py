from django.db import connection
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.db.models.functions import JSONObject
from django.db.models import ForeignKey, F
from rest_framework.renderers import JSONRenderer

from ..models.GenericEntity import GenericEntity
from ..models.Template import Template
from ..models.Concept import Concept
from . import model_utils
from . import template_utils
from . import permission_utils
from . import concept_utils
from . import search_utils
from . import create_utils
from . import gen_utils
from . import constants

""" REST renderer """
class PrettyJsonRenderer(JSONRenderer):
    def get_indent(self, accepted_media_type, renderer_context):
        return 2

""" Parameter validation """

def is_malformed_entity_id(primary_key):
    """
      Checks whether primary key is malformed

      Args:
        primary_key (string): string containing primary key to be checked

      Returns:
        If primary key is malformed, returns 406 response, else returns split id
        i.e. PH123 -> 'PH', '123'
    """
    entity_id_split = model_utils.get_entity_id(primary_key)
    if not entity_id_split:
        return Response(
            data={
                'message': 'Malformed entity id'
            },
            content_type='json',
            status=status.HTTP_406_NOT_ACCEPTABLE
        )

    return entity_id_split

def exists_entity(entity_id):
    """
      Checks whether an entity with given entity_id exists

      Args:
        entity_id (string): Id of entity to be checked

      Returns:
        If entity exists, returns entity, else returns 404 response
    """
    entity = model_utils.try_get_instance(
        GenericEntity, id=entity_id
    )

    if not entity:
        return Response(
            data={
                'message': 'Entity does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    return entity

def exists_historical_entity(entity_id, user, historical_id=None):
    """
      Checks whether a historical version of an entity exists

      Args:
        entity_id (string): entity id
        user (User): User object
        historical_id (Integer): historical id

      Returns:
        If exists, returns first instance of historical entity, otherwise 
        returns response 404
    """
    if not historical_id:
        historical_id = permission_utils.get_latest_entity_historical_id(
            entity_id, user
        )

    historical_entity = model_utils.try_get_instance(
        GenericEntity,
        id=entity_id
    ).history.filter(history_id=historical_id)

    if not historical_entity.exists():
        return Response(
            data={
                'message': 'Historical entity version does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    return historical_entity.first()

def exists_concept(concept_id):
    """
      Checks whether a concept with given concept_id exists

      Args:
        concept_id (string): Id of the concept to be checked

      Returns:
        If concept exists, returns concept, else returns 404 response
    """
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )

    if not concept:
        return Response(
            data={
                'message': 'Concept does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    return concept

def exists_historical_concept(request, concept_id, historical_id=None):
    """
      Checks whether a historical version of a concept exists

      Args:
        request (RequestContext): the HTTPRequest
        concept_id (string): concept id
        historical_id (Integer): historical id of the concept

      Returns:
        If exists, returns first instance of historical concept, otherwise 
        returns response 404
    """
    historical_concept = None
    if not historical_id:
        historical_concept = concept_utils.get_latest_accessible_concept(request, concept_id)
    else: 
        historical_concept = model_utils.try_get_instance(
            Concept,
            pk=concept_id
        ).history.filter(history_id=historical_id)
        
        if historical_concept.exists():
            historical_concept = historical_concept.first()

    if not historical_concept:
        return Response(
            data={
                'message': 'Historical concept version does not exist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    return historical_concept

""" General helpers """

def get_entity_version_history(request, entity_id):
    """
      Retrieves an entities version history

      Args:
        request (HTTPContext): Request context
        entity_id (string): Entity id

      Returns:
        Dict containing version history of entity
    """
    result = []

    historical_versions = GenericEntity.objects.get(
        id=entity_id
    ).history.all().order_by('-history_id')

    latest = historical_versions.first()
    for version in historical_versions:
        is_published = permission_utils.is_publish_status(
            version, [permission_utils.APPROVAL_STATUS.APPROVED]
        )

        if permission_utils.can_user_view_entity(request, version.id, version.history_id):
            result.append({
                'version_id': version.history_id,
                'version_name': version.name.encode('ascii', 'ignore').decode('ascii'),
                'version_date': version.history_date,
                'is_published': is_published,
                'is_latest': latest.history_id == version.history_id
            })

    return result

def get_concept_version_history(request, concept_id):
    """
      Retrieves a concepts version history

      Args:
        request (HTTPContext): Request context
        concept_id (string): concept id

      Returns:
        Dict containing version history of entity
    """
    result = []

    historical_versions = Concept.objects.get(
        id=concept_id
    ).history.all().order_by('-history_id')

    latest = historical_versions.first()
    for version in historical_versions:
        if not permission_utils.can_user_view_concept(request, version):
            continue

        is_published = concept_utils.is_concept_published(concept_id, version.history_id)
        result.append({
            'version_id': version.history_id,
            'version_name': version.name.encode('ascii', 'ignore').decode('ascii'),
            'version_date': version.history_date,
            'is_published': is_published,
            'is_latest': latest.history_id == version.history_id
        })

    return result

""" Formatting helpers """

def get_layout_from_entity(entity):
    """
      Retrieve the layout of an entity

      Args:
        entity (GenericEntity): Entity object

      Returns:
        Layout of entity if entity exists, otherwise 404 response
    """
    layout = entity.template
    if not layout:
        return Response(
            data={
                'message': 'Entity template is missing'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    if not template_utils.is_layout_safe(layout):
        return Response(
            data={
                'message': 'Entity layout is empty'
            },
            content_type='json',
            status=status.HTTP_204_NO_CONTENT
        )

    version = template_utils.try_get_content(entity.template_data, 'version')
    if not version:
        version = getattr(entity, 'template_version')

    if version:
        template_version = Template.history.filter(
            id=entity.template.id,
            template_version=version
        ).order_by('-history_id')

        if template_version:
            template_version = template_version.first()
            return template_version

    return Response(
        data={
            'message': 'Entity template version does not exist'
        },
        content_type='json',
        status=status.HTTP_404_NOT_FOUND
    )

def build_template_subquery_from_string(param, data, top_ref, sub_ref, validation, opts=None, prefix=''):
    """
        Derives a valid query from the given
        query and contextual subquery parameters

      [!] NOTE: Parameters & types should be validated _BEFORE_ calling this function

      Args:
        param (string): the name of the request param that's been mapped to the template

        data (any): the value portion of the key-value pair param

        top_ref (string): the top-most field reference name

        sub_ref (string): the subquery field reference name

        validation (dict): validation dictionary defined by the template

        opts (list): (optional) an optional list of modifiers as derived from the query params

        prefix (str): (optional) used to vary the names across template version(s)

      Returns:

        1. boolean - reflects the success status of the call

        2. list|None - if successful, will return a list where the 1st index is the query;
                       and the 2nd is the derived query dataset

    """
    # Validate query
    if not isinstance(validation, dict):
        return False, None

    if len(prefix) > 0:
        prefix = prefix + '_'

    source = validation.get('source')
    if source is None:
        return False, None

    model = source.get('model')
    subqueries = source.get('subquery')
    sub_validation = subqueries.get(sub_ref) if subqueries is not None else None
    if not isinstance(model, str) or not isinstance(sub_validation, dict):
        return False, None

    # Prepare modifier(s)
    tree_data = source.get('trees') if source and 'trees' in validation.get('source') else None
    tree_clause = ''
    next_clause = 'where'

    dataset = { }
    if isinstance(tree_data, list) and len(tree_data) > 0:
        next_clause = 'and'
        tree_clause = f'''
            where t1.type_id = any(%({prefix}{param}_trlink)s)
        '''
        dataset.update({ f'{prefix}{param}_trlink': tree_data })

    modifiers = sub_validation.get('modifiers') or []
    sub_type = sub_validation.get('type')
    sub_field = sub_validation.get('field')
    sub_field_type = sub_validation.get('field_type')

    if sub_field_type == 'jsonb':
        # Handle json subquqery
        #   i.e. we need to match on a key-value pair within each
        #        of the ontological tags
        #

        key_field = sub_validation.get('key')
        if not isinstance(key_field, str):
            return False, None

        ltype = None
        datatype = None
        processor = ''
        if sub_type == 'int_array':
            data = [ int(x) for x in data.split(',') if isinstance(gen_utils.parse_int(x, default=None), int) ]
            ltype = '::bigint'
            datatype = '::bigint'
        elif sub_type == 'string_array':
            data = [ str(x).lower() for x in data.split(',') if gen_utils.try_value_as_type(x, 'string') is not None ]
            ltype = '::text'
            datatype = ''
            processor = 'lower'

        if not isinstance(datatype, str):
            return False, None

        if 'descendants' in opts and (isinstance(modifiers, list) and 'descendants' in modifiers):
            # Match first, then perform query
            matched_records = []
            with connection.cursor() as cursor:
                sql = f'''
                select
                        t.id
                from public.clinicalcode_{model.lower()} as t
                where {processor}(t.{sub_field}::jsonb->>'{key_field}'::text{datatype}) = any(%(data)s{ltype}[])
                '''
                cursor.execute(sql, params={
                    'data': data,
                })

                matched_records = [ row[0] for row in cursor.fetchall() ]

            query = f'''
            exists(
                select 1
                    from (
                    select mid::bigint as val
                        from jsonb_array_elements(
                        case jsonb_typeof(entity.template_data->'{top_ref}')
                        when 'array'
                            then entity.template_data->'{top_ref}'
                            else '[]'
                        end
                        ) as mid
                    ) as t0
                    join public.clinicalcode_{model.lower()} as t1
                    on t0.val = t1.id
                    {tree_clause}
                    {next_clause} (
                        t1.id::bigint = any(%({prefix}{param}_data)s::bigint[])
                        or is_ontological_descendant(%({prefix}{param}_data)s::bigint[], array[t1.id]::bigint[])
                    )
                limit 1
            )
            '''
            dataset.update({ f'{prefix}{param}_data': matched_records })
            return True, [ query, dataset ]

        query = f'''
        exists(
            select 1
                from (
                select mid::bigint as val
                    from jsonb_array_elements(
                    case jsonb_typeof(entity.template_data->'{top_ref}')
                    when 'array'
                        then entity.template_data->'{top_ref}'
                        else '[]'
                    end
                    ) as mid
                ) as t0
                join public.clinicalcode_{model.lower()} as t1
                  on t0.val = t1.id
                {tree_clause}
                {next_clause} (
                    {processor}(t1.{sub_field}::jsonb->>'{key_field}'::text{datatype}) = any(%({prefix}{param}_data)s{ltype}[])
                )
                limit 1
        )
        '''
        dataset.update({ f'{prefix}{param}_data': data })

        return True, [ query, dataset ]
    elif sub_type == 'int_array' and sub_field == 'id':
        # Handle top-level field
        #   i.e. we can skip cursor check since 
        #        we already have the descendant search field
        #

        data = [ int(x) for x in data.split(',') if isinstance(gen_utils.parse_int(x, default=None), int) ]
        dataset.update({ f'{prefix}{param}_data': data })

        if 'descendants' in opts and (isinstance(modifiers, list) and 'descendants' in modifiers):
            query = f'''
            exists(
                select 1
                  from (
                    select mid::bigint as val
                      from jsonb_array_elements(
                        case jsonb_typeof(entity.template_data->'{top_ref}')
                        when 'array'
                            then entity.template_data->'{top_ref}'
                            else '[]'
                        end
                      ) as mid
                  ) as t0
                  join public.clinicalcode_{model.lower()} as t1
                    on t0.val = t1.id
                  {tree_clause}
                  {next_clause} (
                    t1.{sub_field}::bigint = any(%({prefix}{param}_data)s::bigint[])
                    or is_ontological_descendant(%({prefix}{param}_data)s::bigint[], array[t0.val]::bigint[])
                  )
                limit 1
            )
            '''
        else:
            query = f'''
            exists(
                select 1
                  from (
                    select mid::bigint as val
                      from jsonb_array_elements(
                        case jsonb_typeof(entity.template_data->'{top_ref}')
                        when 'array'
                            then entity.template_data->'{top_ref}'
                            else '[]'
                        end
                      ) as mid
                  ) as t0
                  join public.clinicalcode_{model.lower()} as t1
                    on t0.val = t1.id
                  {tree_clause}
                  {next_clause} (
                    t1.{sub_field}::bigint = any(%({prefix}{param}_data)s::bigint[])
                  )
                limit 1
            )
            '''

        return True, [ query, dataset ]


    # Match via cursor
    #   i.e. if we need to match descendants, we need to perform
    #        a query in advance of the search to ensure we have the match id(s)
    #        so that we can meet the parameter requirements of `is_ontological_descendants`
    #

    datatype = None
    processor = ''
    if sub_type == 'int_array':
        data = [ int(x) for x in data.split(',') if isinstance(gen_utils.parse_int(x, default=None), int) ]
        datatype = 'bigint'
    elif sub_type == 'string_array':
        data = [ str(x).lower() for x in data.split(',') if gen_utils.try_value_as_type(x, 'string') is not None ]
        datatype = 'text'
        processor = 'lower'

    if not isinstance(datatype, str):
        return False, None

    if 'descendants' in opts and (isinstance(modifiers, list) and 'descendants' in modifiers):
        # Match first, then perform query
        matched_records = []
        with connection.cursor() as cursor:
            sql = f'''
            select
                    t.id
              from public.clinicalcode_{model.lower()} as t
             where {processor}(t.{sub_field}::{datatype}) = any(%(data)s::{datatype}[]);
            '''
            cursor.execute(sql, params={
                'data': data,
            })

            matched_records = [ row[0] for row in cursor.fetchall() ]

        query = f'''
        exists(
            select 1
                from (
                select mid::bigint as val
                    from jsonb_array_elements(
                    case jsonb_typeof(entity.template_data->'{top_ref}')
                    when 'array'
                        then entity.template_data->'{top_ref}'
                        else '[]'
                    end
                    ) as mid
                ) as t0
                join public.clinicalcode_{model.lower()} as t1
                  on t0.val = t1.id
                {tree_clause}
                {next_clause} (
                    t1.id::bigint = any(%({prefix}{param}_data)s::bigint[])
                    or is_ontological_descendant(%({prefix}{param}_data)s::bigint[], array[t1.id]::bigint[])
                )
                limit 1
        )
        '''
        dataset.update({ f'{prefix}{param}_data': matched_records })
    else:
        # Simple query, we can advance without deriving
        # appropriate match id(s)
        #

        query = f'''
        exists(
            select 1
                from (
                select mid::bigint as val
                    from jsonb_array_elements(
                    case jsonb_typeof(entity.template_data->'{top_ref}')
                    when 'array'
                        then entity.template_data->'{top_ref}'
                        else '[]'
                    end
                    ) as mid
                ) as t0
                join public.clinicalcode_{model.lower()} as t1
                  on t0.val = t1.id
                {tree_clause}
                {next_clause} (
                    {processor}(t1.{sub_field}::{datatype}) = any(%({prefix}{param}_data)s::{datatype}[])
                )
                limit 1
        )
        '''
        dataset.update({ f'{prefix}{param}_data': data })

    return True, [ query, dataset ]

def build_query_string_from_param(param, data, validation, field_type, is_dynamic=False, prefix=''):
    """
      Builds query (terms and where clauses) based on a template

      [!] NOTE: Parameters & types should be validated _BEFORE_ calling this function

      Args:
        param (string): the name of the request param that's been mapped to the template

        data (any): the value portion of the key-value pair param

        validation (dict): validation dictionary defined by the template

        field_type (str): the associated field type as defined by the template

        is_dynamic (boolean): (defaults to false) whether the query parameter is a metadata field or found within the template

        prefix (str): (optional) used to vary the names across template version(s)

      Returns:

        1. boolean - reflects the success status of the call

        2. string|None - the query string if successful

        3. dict|None - the processed data if successful

    """
    if len(prefix) > 0:
        prefix = prefix + '_'

    query = None
    if field_type == 'int' or field_type == 'enum':
        if 'options' in validation or 'source' in validation:
            data = [ int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None) is not None ]

            if is_dynamic:
                query = f'''(entity.template_data::json->>'{param}'::text)::int = any(%({prefix}{param}_data)s)'''
            else:
                query = f'''entity.{param}::int = any(%({prefix}{param}_data)s)'''
        else:
            data = data.split(',')
            if is_dynamic:
                query = f'''entity.template_data::json->>'{param}'::text = any(%({prefix}{param}_data)s)'''
            else:
                query = f'''entity.{param}::text = any(%({prefix}{param}_data)s)'''

        return True, query, { f'{prefix}{param}_data': data }
    elif field_type == 'int_array':
        if is_dynamic:
            source = validation.get('source')
            trees = source.get('trees') if source and 'trees' in validation.get('source') else None
            if trees:
                data = [ str(x) for x in data.split(',') if gen_utils.try_value_as_type(x, 'string') is not None ]
                model = source.get('model') if isinstance(source.get('model'), str) else None

                if model:
                    # query by `id` or `search_vector`
                    #
                    #   _i.e._ matches one of:
                    #
                    #         - directly via `id`
                    #     OR;
                    #         - the associated `name` +/- other properties via `search_vector`
                    #
                    query = f'''
                    exists(
                        select 1
                          from (
                            select mid::text as val
                              from jsonb_array_elements(
                                case jsonb_typeof(entity.template_data->'{param}')
                                when 'array'
                                    then entity.template_data->'{param}'
                                    else '[]'
                                end
                              ) as mid
                          ) as t0
                          join public.clinicalcode_{model.lower()} as t1
                            on t0.val::int = t1.id
                         where t1.type_id = any(%({prefix}{param}_trlink)s)
                           and (
                                t0.val = any(%({prefix}{param}_data)s)
                                or (
                                    t1.search_vector
                                    @@ to_tsquery(
                                        'pg_catalog.english',
                                        replace(
                                            websearch_to_tsquery('pg_catalog.english', %({prefix}{param}_trsearch)s)::text
                                            || ':*', '<->', '|'
                                        )
                                    )
                                )
                           )
                    )
                    '''
                    return True, query, {
                        f'{prefix}{param}_data': data,
                        f'{prefix}{param}_trlink': trees,
                        f'{prefix}{param}_trsearch': ' '.join(data),
                    }
                else:
                    query = f'''
                    exists(
                        select 1
                        from (
                            select mid::text as val
                            from jsonb_array_elements(
                                case jsonb_typeof(entity.template_data->'{param}')
                                when 'array'
                                    then entity.template_data->'{param}'
                                    else '[]'
                                end
                            ) as mid
                        ) t
                        where val = any(%({prefix}{param}_data)s)
                    )
                    '''
            else:
                query = f'''
                exists(
                    select 1
                      from jsonb_array_elements(
                            case jsonb_typeof(entity.template_data->'{param}')
                            when 'array'
                                then entity.template_data->'{param}'
                                else '[]'
                            end
                      ) as val
                     where val::text = any(%({prefix}{param}_data)s)
                )
                '''
        else:
            data = [ int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None) is not None ]
            query = f'''entity.{param} && %({prefix}{param}_data)s'''

        return True, query, { f'{prefix}{param}_data': data }
    elif field_type == 'datetime':
        data = [ gen_utils.parse_date(x) for x in data.split(',') if gen_utils.parse_date(x) ]
        if len(data) > 1 and not is_dynamic:
            data = gen_utils.get_start_and_end_dates(data[:2])
            query = f'''(entity.{param}::timestamp >= %({prefix}{param}_start_data)s and entity.{param}::timestamp <= %({prefix}{param}_end_data)s)'''
            return True, query, { f'{prefix}{param}_start_data': data[0], f'{prefix}{param}_end_data': data[1] }
    elif field_type == 'string':
        if is_dynamic:
            query = f'''entity.template_data::json->>'{param}'::text = %({prefix}{param}_data)s'''
        else:
            query = f'''entity.{param} = %({prefix}{param}_data)s'''
        return True, query, { f'{prefix}{param}_data': data }

    return False, None, None

def build_query_from_template(request, user_authed, template=None):
    """
      Builds query (terms and where clauses) based on a template

      Args:
        request (HTTPContext): Request context
        user_authed (boolean): Whether the user making the request is 
          authenticated
        template (dict): Template object

      Returns:
        Terms and where clause built from the template
    """
    is_dynamic = True

    terms = {}
    where = []
    params = []
    for key, value in request.GET.items():
        is_dynamic = True
        layout = template

        field_data = template_utils.try_get_content(template, key)
        if field_data is not None:
            is_base_field = template_utils.try_get_content(
                field_data, 'is_base_field')
            if not is_base_field:
                is_active = template_utils.try_get_content(
                    field_data, 'active')
                if not is_active:
                    continue

                requires_auth = template_utils.try_get_content(
                    field_data, 'requires_auth')
                if requires_auth and not user_authed:
                    continue

                can_search = template_utils.try_get_content(
                    field_data, 'search')
                if can_search:
                    can_search = template_utils.try_get_content(
                        field_data['search'], 'api')
                    if not can_search:
                        continue
                else:
                    continue
            else:
                is_dynamic = False
                layout = constants.metadata

            search_utils.apply_param_to_query(
                terms, where, params, layout, key, value,
                is_dynamic=is_dynamic, force_term=True, is_api=True
            )

    return terms, where, params

def get_entity_detail_from_layout(
    entity, fields, user_authed, fields_to_ignore=[], target_field=None
):
    """
      Retrieves entity detail in the format required for detail API endpoint,
        specifically from a template 

      Args:
        entity (GenericEntity): Entity object to get the detail for
        fields (dict): dict containing layout of the entity
        user_authed (boolean): Whether the user is authenticated
        fields_to_ignore (list of strings): List of fields to remove from output
        target_field (string): Field to be targeted, i.e. only build the detail
          for this particular field

      Returns:
        Dict containing details of the entity specified
    """
    result = {}
    for field, field_definition in fields.items():
        if target_field is not None and target_field.lower() != field.lower():
            continue

        if field.lower() in fields_to_ignore:
            continue

        is_active = template_utils.try_get_content(field_definition, 'active')
        if is_active == False:
            continue

        requires_auth = template_utils.try_get_content(
            field_definition, 'requires_auth')
        if requires_auth and not user_authed:
            continue

        if template_utils.is_metadata(entity, field):
            validation = template_utils.get_field_item(
                constants.metadata, field, 'validation', {}
            )

            is_source = validation.get('source')
            if is_source:
                if template_utils.is_metadata(entity, field=field):
                    value = template_utils.get_metadata_value_from_source(
                        entity, field, default=None
                    )
                else:
                    value = template_utils.get_entity_field(entity, field)

                result[field] = value
            continue

        if field == 'concept_information':
            value = template_utils.get_entity_field(entity, field)
            if value:
                result[field] = build_final_codelist_from_concepts(
                    entity, 
                    concept_information=value, 
                    inline=False, 
                    include_concept_detail=False,
                    include_headers=True
                )
        else:
            value = template_utils.get_template_data_values(
                entity, fields, field, default=None, hide_user_details=True
            )
            if value is None:
                value = template_utils.get_entity_field(entity, field)

            result[field] = value

    return result

def get_entity_detail_from_meta(entity, data, fields_to_ignore=[], target_field=None):
    """
      Retrieves entity detail in the format required for detail API endpoint,
        specifically from metadata fields, e.g. constants

      Args:
        entity (GenericEntity): Entity object to get the detail for
        data (dict): dict containing previously built detail
        fields_to_ignore (list of strings): List of fields to remove from output
        target_field (string): Field to be targeted, i.e. only build the detail
          for this particular field

      Returns:
        Dict containing details of the entity specified
    """
    result = {}
    for field in entity._meta.fields:
        field_name = field.name
        if target_field is not None and target_field.lower() != field_name.lower():
            continue

        if field_name.lower() in data or field_name.lower() in fields_to_ignore:
            continue

        field_type = field.get_internal_type()
        if field_type and field_type in constants.STRIPPED_FIELDS:
            continue

        if field_name in constants.API_HIDDEN_FIELDS:
            continue

        field_value = template_utils.get_entity_field(entity, field_name)
        if field_value is None:
            result[field_name] = None
            continue

        if isinstance(field, ForeignKey):
            model = field.target_field.model
            model_type = str(model)
            if model_type in constants.USERDATA_MODELS:
                if model_type == str(User):
                    result[field_name] = template_utils.get_one_of_field(
                        field_value, ['username', 'name'])
                else:
                    result[field_name] = {
                        'id': field_value.id,
                        'name': template_utils.get_one_of_field(field_value, ['username', 'name'])
                    }
                continue

        if field_name in constants.API_MAP_FIELD_NAMES:
            field_name = constants.API_MAP_FIELD_NAMES.get(field_name)

        result[field_name] = field_value

    return result

def get_ordered_entity_detail(
    fields, layout, layout_version, entity_versions, data
):
    """
      Orders entity detail and appends template and version history to the detail
        dict

      Args:
        fields (dict): Dict of fields from a template object
        layout (dict): Layout object
        layout_version (integer): Layout version
        entity_versions (dict): Dict containing entity version information
        data (dict): Entity detail built so far

      Returns:
        Ordered entity detail with appended template and version history fields
    """
    ordered_keys = list(fields.keys())
    ordered_keys.extend(key for key in data.keys() if key not in ordered_keys)
    ordered_result = {}
    for key in ordered_keys:
        if key in data:
            ordered_result[key] = data[key]

    ordered_result = ordered_result | {
        'template': {
            'id': layout.id,
            'name': layout.name,
            'description': layout.description,
            'version_id': layout_version
        },
        'versions': entity_versions
    }

    return ordered_result

def get_entity_detail(
    request,
    entity_id,
    entity,
    user_authed,
    fields_to_ignore=['deleted', 'created_by',
                      'updated_by', 'deleted_by', 'brands'],
    target_field=None,
    return_data=False
):
    """
      Gets entity detail

      Args:
        request (HTTPContext): Request context
        entity_id (integer): Entity id
        entity (GenericEntity): Entity object
        user_authed (boolean): Whether the user is authenticated or not
        fields_to_ignore (list of strings): Fields that should be ignored from result
        target_field (string): Field to target and break early if required
        return_data (boolean): Optionally return data or response

      Returns:
        Returns response containing entity detail if return_data is False,
          otherwise returns dict containing built entity detail
    """
    layout_response = get_layout_from_entity(entity)
    if isinstance(layout_response, Response):
        return layout_response

    layout = layout_response
    layout_definition = template_utils.get_merged_definition(
        layout, default={})
    layout_version = layout.template_version

    fields = template_utils.try_get_content(layout_definition, 'fields')
    if fields is None:
        return None

    result = get_entity_detail_from_layout(
        entity, fields, user_authed, fields_to_ignore=fields_to_ignore, target_field=target_field
    )

    result = result | get_entity_detail_from_meta(
        entity, result, fields_to_ignore=fields_to_ignore, target_field=target_field
    )

    entity_versions = get_entity_version_history(request, entity_id)
    if target_field is None:
        result = get_ordered_entity_detail(
            fields, layout, layout_version, entity_versions, result)

    if return_data:
        return result

    return Response(
        data=[{'phenotype_id': entity.id,
               'phenotype_version_id': entity.history_id} | result],
        status=status.HTTP_200_OK
    )

def build_final_codelist_from_concepts(
        entity, 
        concept_information, 
        inline=True,
        include_concept_detail=True, 
        include_headers=False):
    """
      Builds the final codelist from all entity concepts

      Args:
        entity (GenericEntity): Entity object
        concept_information {list of ints}: List of concept ids
        inline (boolean): Optionally format the response to be a list

      Returns:
        Dict object containing final codelist if inline is False, otherwise, returns
          list containing final codelist
    """
    result = []
    for concept in concept_information:
        concept_id = concept['concept_id']
        concept_version = concept['concept_version_id']

        # Get concept entity for additional data, skip if we're not able to find it
        concept_entity = Concept.history.get(
            id=concept_id, history_id=concept_version
        )
        if not concept_entity:
            continue

        concept_data = {
            'concept_id': concept_id,
            'concept_version_id': concept_version,
            'concept_name': concept_entity.name,
            'coding_system': model_utils.get_coding_system_details(concept_entity.coding_system),
            'phenotype_id': entity.id,
            'phenotype_version_id': entity.history_id,
            'phenotype_name': entity.name
        }

        if include_headers:
            concept_data |= { 'code_attribute_header': concept_entity.code_attribute_header}

        # Get codes
        concept_codes = concept_utils.get_concept_codelist(
            concept_id,
            concept_version,
            incl_attributes=True
        )
        for i, code in enumerate(concept_codes):
            if not include_concept_detail:
                concept_codes[i] = {
                    'code': code.get('code'),
                    'description': code.get('description'),
                    'attributes': code.get('attributes')
                }

            if concept_entity.code_attribute_header is not None and code.get('attributes') is not None:
                concept_codes[i]['attributes'] = dict(zip(
                    concept_entity.code_attribute_header, code.get('attributes')
                ))

        if inline:
            concept_codes = [data | concept_data for data in concept_codes]
            result += concept_codes
        else:
            result += [concept_data | {'codes': concept_codes}]

    return result

def get_codelist_from_entity(entity):
    """
      Retrieves final codelist from an entity

      Args:
        entity (GenericEntity): Entity object

      Returns:
        If the entity contains a codelist, returns the final codelist, otherwise
          returns 400/404 response depending on status within the template/entity
    """
    layout_response = get_layout_from_entity(entity)
    if isinstance(layout_response, Response):
        return layout_response
    layout = layout_response
    fields = template_utils.try_get_content(layout.definition, 'fields')

    concept_field = None
    for field, definition in fields.items():
        validation = template_utils.try_get_content(definition, 'validation')
        if validation is None:
            continue

        field_type = template_utils.try_get_content(validation, 'type')
        if field_type is None or field_type != 'concept':
            continue

        concept_field = field
        break

    if not concept_field:
        return Response(
            data={
                'message': 'Entity template does not contain a codelist'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    concept_information = template_utils.try_get_content(
        entity.template_data, 'concept_information'
    )
    if not concept_information:
        return Response(
            data={
                'message': 'Entity does not contain a codelist'
            },
            content_type='json',
            status=status.HTTP_404_NOT_FOUND
        )

    codes = build_final_codelist_from_concepts(entity, concept_information)

    return Response(
        data=codes,
        status=status.HTTP_200_OK
    )

def populate_entity_version_id(form):
    """
      Populates entity version id in entity form dict

      Args:
        form (dict): Entity form dict

      Returns:
        Form with entity version based on entity_id
    """
    form_entity = form.get('entity')
    if form_entity is not None:
        form['entity']['version_id'] = None

        entity = GenericEntity.objects.get(id=form_entity['id'])
        if entity is not None:
            historical_version = entity.history.all().order_by('-history_id')
            historical_version = historical_version.first()
            form['entity']['version_id'] = historical_version.history_id

    return form

def validate_api_create_update_form(request, method):
    """
      Validates entity form dict

      Args:
        request (HTTPContext): Request context
        method (Integer): Represents create/update, see constants.FORM_METHODS enum

      Returns:
        Validated form if successful, otherwise returns 400 response
    """
    form_errors = []
    form = gen_utils.get_request_body(request)
    form = populate_entity_version_id(form)
    form = create_utils.validate_entity_form(
        request, form, form_errors, method=method
    )

    if form is None:
        return Response(
            data={
                'message': 'Invalid form',
                'errors': form_errors
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    return form

def create_update_from_api_form(request, form):
    """
      Create or updates an entity from an entity form dict

      Args:
        request (HTTPContext): Request context
        form (dict): Dict containing entity information

      Returns:
        Created/Updated entity if validation succeeds, otherwise returns
          400 response
    """
    form_errors = []
    entity = create_utils.create_or_update_entity_from_form(
        request, form, form_errors)
    if entity is None:
        return Response(
            data={
                'message': 'Data submission is invalid',
                'errors': form_errors
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    return entity

def get_concept_versions_from_entity(entity):
    """
      Retrieves concept versions for an entity

      Args:
        entity (GenericEntity): Entity object

      Returns:
        Dict containing all concept_ids and concept_version_ids associated with 
          the entity passed
    """
    result = {}

    concept_information = template_utils.try_get_content(
        entity.template_data, 'concept_information'
    )
    for concept in concept_information:
        concept_id = concept['concept_id']
        concept_version_id = concept['concept_version_id']

        concept_entity = Concept.history.get(
            id=concept_id, history_id=concept_version_id
        )
        if not concept_entity:
            continue

        result[concept_entity.name] = {
            'id': concept_id,
            'version_id': concept_version_id
        }

    return result

def get_template_versions(template_id):
    """
      Retrieves version history of a template from template_id

      Args:
        template_id (Integer): Template id

      Returns:
        List containing version history of template
    """
    template_versions = Template.objects.get(
        id=template_id
    ).history.all().order_by('-template_version')

    template_versions = list(template_versions.values('template_version'))

    return list(set([version['template_version'] for version in template_versions]))

def get_formatted_concept_codes(concept, concept_codelist, headers=None):
    """
      Formats concept codelist and attribute data in the format required for API

      Args:
        concept (Concept): Concept object
        concept_codelist (dict): Dict containing codelist data
        headers (list of strings): List containing attribute headers

      Returns:
        Dict containing formatted concept codelist information 
    """
    concept_codes = []
    for code in concept_codelist:
        attributes = code.get('attributes')
        if attributes is not None and headers is not None:
            attributes = dict(zip(headers, attributes))

        concept_codes.append({
            'code': code.get('code'),
            'description': code.get('description'),
            'concept_id': concept.id,
            'concept_version_id': concept.history_id,
            'coding_system': model_utils.get_coding_system_details(concept.coding_system),
            'attributes': attributes
        })

    return concept_codes

def annotate_linked_entities(entities):
    """
        Annotates linked entities with phenotype and template details

        Args:
            entities (QuerySet): Entities queryset
        
        Returns:
            Queryset containing annotated entities
    """
    return entities.annotate(
        phenotype_id=F('id'),
        phenotype_version_id=F('history_id'),
        phenotype_name=F('name')
    ) \
    .values(
        'phenotype_id', 
        'phenotype_version_id', 
        'phenotype_name'
    ) \
    .annotate(
        template=JSONObject(
            id=F('template__id'),
            version_id=F('template_version'),
            name=F('template__name')
        )
    )
