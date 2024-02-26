from django.apps import apps
from django.db import connection
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.expressions import RawSQL
from django.db.models.query import QuerySet
from django.core.paginator import EmptyPage, Paginator
from django.contrib.postgres.search import TrigramSimilarity, SearchQuery, SearchRank, SearchVector

import re

from ..models.EntityClass import EntityClass
from ..models.Template import Template
from ..models.GenericEntity import GenericEntity
from ..models.Statistics import Statistics
from ..models.CodingSystem import CodingSystem
from . import model_utils, template_utils, constants, gen_utils, permission_utils, concept_utils

def get_template_filters(request, template, default=None):
    """
        Safely gets the filterable fields of a template
    """
    current_brand = request.CURRENT_BRAND or 'ALL'

    layout = template_utils.try_get_layout(template)
    if layout is None:
        return default
    
    layout = template_utils.get_ordered_definition(layout, clean_fields=True)    
    fields = template_utils.try_get_content(layout, 'fields')
    if fields is None:
        return default
    
    filters = [ ]
    for field, packet in fields.items():
        if not packet.get('active'):
            continue
        
        validation = template_utils.try_get_content(packet, 'validation')
        if validation is None:
            continue
        
        search_params = template_utils.try_get_content(packet, 'search')
        if search_params is None:
            continue

        if not search_params.get('filterable'):
            continue

        details = get_filter_info(field, packet)
        if details is None:
            continue

        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, details.get('type'))
        if component is None:
            continue
        details.update({ 'component': component })
        
        filters.append({
            'details': details,
            'options': try_get_template_statistics(field, brand=current_brand)
        })
    
    return filters

def get_metadata_filters(request):
    """
        Gets all filterable fields of the top-level metadata
    """
    current_brand = request.CURRENT_BRAND or 'ALL'

    filters = [ ]
    for field, packet in constants.metadata.items():
        if not packet.get('active'):
            continue

        validation = template_utils.try_get_content(packet, 'validation')
        if validation is None:
            continue
        
        search_params = template_utils.try_get_content(packet, 'search')
        if search_params is None:
            continue
        
        if not search_params.get('filterable') or search_params.get('single_search_only'):
            continue
        
        details = get_filter_info(field, packet)
        if details is None:
            continue

        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, details.get('type'))
        if component is None:
            continue
        details.update({ 'component': component })
        
        options = None
        if 'compute_statistics' in packet:
            options = get_metadata_stats_by_field(field, brand=current_brand)

        if options is None and 'source' in validation:
            options = get_source_references(packet, default=[])
        
        filters.append({
            'details': details,
            'options': options
        })
    
    return filters

def try_derive_entity_type(entity_type):
    """
        Attempts to derive the entity type passed as a kwarg to the search view

        Args:
            entity_type (string): the entity_type parameter
        
        Returns:
            (list) containing the EntityClass ID if successful, otherwise returns None
    """
    if gen_utils.is_empty_string(entity_type):
        return None
    
    # If we've passed an ID, return it without checking
    entity_id = gen_utils.parse_int(entity_type, default=None)
    if entity_id is not None:
        return [entity_id]

    # Try to match by name (need to replace URI encoding to spaces)
    entity_type = entity_type.replace('-', ' ')
    entity_cls = EntityClass.objects.annotate(name_lower=Lower('name')).filter(name_lower=entity_type)
    if entity_cls.exists():
        return [entity_cls.first().id]
    return None

def perform_vector_search(queryset, search_query, min_rank=0.05,
                          order_by_relevance=True, reverse_order=False):
    """
        Performs a search on generic entities' indexed search_vector field
    """
    query = SearchQuery(search_query)
    if order_by_relevance:
        vector = SearchVector('search_vector')
        rank = SearchRank(vector, query)
        clause = '-rank' if not reverse_order else 'rank'

        return queryset.annotate(
            search=vector,
            rank=rank
        ) \
        .filter(Q(rank__gte=min_rank) & Q(search=query)) \
        .order_by(clause)

    return queryset.filter(Q(name__search=query) | Q(author__search=query) | Q(definition__search=query))

def perform_trigram_search(queryset, search_query, min_similarity=0.2,
                           order_by_relevance=True, reverse_order=False):
    """
        Performs trigram fuzzy search on generic entities
    """
    if order_by_relevance:
        clause = '-similarity' if not reverse_order else 'similarity'
        return queryset.filter(search_vector__icontains=search_query) \
            .annotate(
                similarity=(
                    TrigramSimilarity('id', search_query) + \
                    TrigramSimilarity('name', search_query)
                )
            ) \
            .filter(Q(similarity__gte=min_similarity)) \
            .order_by(clause)
    
    return queryset.filter(search_vector__icontains=search_query)

def search_entities(queryset, search_query,
                    min_threshold=0.05, fuzzy=True,
                    order_by_relevance=True, reverse_order=False):
    """
        Utility method to perform either trigram or vector search
    """
    if fuzzy:
        return perform_trigram_search(queryset, search_query, min_threshold, order_by_relevance, reverse_order)

    return perform_vector_search(queryset, search_query, min_threshold, order_by_relevance, reverse_order)

def search_entity_fields(queryset, search_query, fields=[],
                         min_threshold=0.05, fuzzy=True,
                         order_by_relevance=True, reverse_order=False):
    """
        Utility method to search one or more fields of a generic entity based on the parameters of this method
    """

    if not isinstance(fields, list) or len(fields) < 1:
        return queryset.none()

    if fuzzy:
        if order_by_relevance:
            query = None
            for field in fields:
                if query is None:
                    query = TrigramSimilarity(field, search_query)
                else:
                    query = query + TrigramSimilarity(field, search_query)

            clause = '-similarity' if not reverse_order else 'similarity'
            return queryset.annotate(
                similarity=query
            ) \
            .filter(Q(similarity__gte=min_threshold)) \
            .order_by(clause)
        else:
            query = { }
            for field in fields:
                query[f'{field}__trigram_similar'] = search_query
            
            return queryset.filter(**query)
    
    vector = SearchVector(*fields)
    query = SearchQuery(search_query)
    if order_by_relevance:
        rank = SearchRank(vector, query)
        clause = '-rank' if not reverse_order else 'rank'

        return queryset.annotate(
            search=vector,
            rank=rank
        ) \
        .filter(Q(rank__gte=min_threshold) & Q(search=query)) \
        .order_by(clause)

    return queryset.annotate(search=vector).filter(search=query)

def validate_query_param(param, template, data, default=None, request=None):
    """
        Validates the query param based on its field type as defined by the template or metadata by examining its source
    """
    validation = template_utils.try_get_content(template, 'validation')
    if validation:
        if 'source' in validation:
            try:
                source_info = validation.get('source')
                model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
                query = {
                    'pk__in': data
                }

                if 'filter' in source_info:
                    filter_query = template_utils.try_get_filter_query(param, source_info.get('filter'), request=request)
                    query = {**query, **filter_query}
                
                queryset = model.objects.filter(Q(**query))
                queryset = list(queryset.values_list('id', flat=True))
            except:
                return default
            else:
                return queryset if len(queryset) > 0 else default
        elif 'options' in validation:
            options = validation['options']
            cleaned = [ ]
            for item in data:
                value = str(item)
                if value in options:
                    cleaned.append(value)
            return cleaned if len(cleaned) > 0 else default
    
    return default

def apply_param_to_query(query, where, params, template, param, data,
                         is_dynamic=False, force_term=False,
                         is_api=False, request=None):
    """
        Tries to apply a URL param to a query if its able to resolve and validate the param data
    """
    template_data = template_utils.try_get_content(template, param)
    search = template_utils.try_get_content(template_data, 'search')
    if search is None or (not 'filterable' in search and not is_api):
        return False
    
    validation = template_utils.try_get_content(template_data, 'validation')
    if validation is None:
        return False
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return False
    
    if field_type == 'int' or field_type == 'enum':
        if 'options' in validation or 'source' in validation:
            data = [int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None)]
            clean = validate_query_param(param, template_data, data, default=None, request=request)
            if clean is None and force_term:
                clean = data
            
            if clean is not None:
                if is_dynamic:
                    query[f'template_data__{param}__in'] = clean
                else:
                    query[f'{param}__in'] = clean
                return True
        else:
            clean = data.split(',')
            if is_dynamic:
                query[f'template_data__{param}__in'] = clean
            else:
                query[f'{param}__in'] = clean
            return True
    elif field_type == 'int_array':
        data = [int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None)]
        clean = validate_query_param(param, template_data, data, default=None, request=request)
        if clean is None and force_term:
            clean = data

        if clean is not None:
            if is_dynamic:
                q = [str(x) for x in clean]
                where.append('''
                exists(
                  select 1
                    from jsonb_array_elements(
                           case jsonb_typeof(template_data->%s)
                           when 'array'
                             then template_data->%s
                             else '[]'
                           end
                    ) as val
                    where val::text = ANY(%s)
                )
                ''')
                params += [param, param, q]
            else:
                query[f'{param}__overlap'] = clean
            return True
    elif field_type == 'datetime':
        data = [gen_utils.parse_date(x) for x in data.split(',') if gen_utils.parse_date(x)]
        if len(data) > 1 and not is_dynamic:
            data = gen_utils.get_start_and_end_dates(data[:2])
            query[f'{param}__range'] = data
            return True
    elif field_type == 'string':
        if is_dynamic:
            query[f'template_data__{param}'] = data
        else:
            query[f'{param}'] = data
        return True

    return False

def try_get_template_children(entity, default=None):
    """
        Used to retrieve entities assoc. with this parent entity per
        the template specification
    """
    children = [ ]
    if not template_utils.is_data_safe(entity):
        return default

    template = entity.template
    template_version = entity.template_version
    if template is None:
        return default

    template = template.history.filter(template_version=template_version)
    if not template.exists():
        return default
    
    template = template.latest()
    template_fields = template_utils.get_layout_fields(template)
    for field, packet in entity.template_data.items():
        template_field = template_utils.try_get_content(template_fields, field)
        if template_field is None:
            continue

        validation = template_utils.try_get_content(template_field, 'validation')
        if validation is None:
            continue

        child_data = None
        field_type = template_utils.try_get_content(validation, 'type')
        if field_type == 'concept':
            child_data = concept_utils.get_concept_dataset(packet, field_name=field, default=None)

        if child_data is None:
            continue
        children = children + child_data
    return children

def exclude_childless_entities(entities, template_fields, child_fields):
    """
        Method to exclude entities from a HistoricalGenericEntity QuerySet
        where rows do not contain valid children, e.g. in the case of a 
        Phenotype that lacks any associated Concepts and any child codes

        Args:
            entities {QuerySet<HistoricalGenericEntity>}: a HistoricalGenericEntity QuerySet

            template_fields {dict}: the template layout

            child_fields {str[]}: a list of field names that are considered
                                  to contain children

        Returns:
            QuerySet<HistoricalGenericEntity> containing the results
            of the exlusion

    """
    entity_ids = list(entities.values_list('id', flat=True))
    if len(entity_ids) < 1:
        return entities

    history_ids = list(entities.values_list('history_id', flat=True))
    with connection.cursor() as cursor:
        base = '''
        with entities as (
            select *
              from public.clinicalcode_historicalgenericentity
             where id = ANY(%(entity_ids)s)
               and history_id = ANY(%(history_ids)s)
        )
        '''

        for field in child_fields:
            template_field = template_utils.try_get_content(template_fields, field)
            if template_field is None:
                continue

            validation = template_utils.try_get_content(template_field, 'validation')
            if validation is None:
                continue

            field_type = template_utils.try_get_content(validation, 'type')
            if field_type == 'concept':
                sql = base + '''
                select entity.id,
                       entity.history_id
                  from entities as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                  join public.clinicalcode_historicalconcept as concept
                    on concept.id = cast(concepts->>'concept_id' as integer)
                   and concept.history_id = cast(concepts->>'concept_version_id' as integer)
                  join public.clinicalcode_codingsystem as codingsystem
                    on codingsystem.id = concept.coding_system_id
                  join public.clinicalcode_historicalcomponent as component
                    on component.concept_id = concept.id
                   and component.history_date <= concept.history_date
                   and component.logical_type = 1
                   and component.history_type != '-'
                  join public.clinicalcode_historicalcodelist as codelist
                    on codelist.component_id = component.id
                   and codelist.history_date <= concept.history_date
                   and codelist.history_type != '-'
                  join public.clinicalcode_historicalcode as code
                    on code.code_list_id = codelist.id
                   and code.history_date <= concept.history_date
                   and code.history_type != '-'
                 group by entity.id,
                          entity.history_id
                '''

                cursor.execute(
                    sql,
                    params={ 'entity_ids': entity_ids, 'history_ids': history_ids }
                )

                results = cursor.fetchall()
                rowcount = len(results)
                if rowcount < 1:
                    entity_ids = []
                    history_ids = []
                    break

                entity_ids = [None]*rowcount
                history_ids = [None]*rowcount
                for index, row in enumerate(results):
                    entity_ids[index] = row[0]
                    history_ids[index] = row[1]

    if len(entity_ids) > 0:
        return entities.filter(
            id__in=entity_ids,
            history_id__in=history_ids
        )

    return GenericEntity.history.none()

def try_search_child_concepts(entities, search=None, order_clause=None):
    """
        Method to collect concept children of a HistoricalGenericEntity QuerySet

        [!] NOTE:
            1. `order_clause` is unsafe:
                Do not allow unknown inputs, only allow those defined
                within *entity_utils/constants.py*
            
            2. This method ignores permissions:
                It should only be called from a method that
                has previously considered accessibility

        Args:
            entities {QuerySet<HistoricalGenericEntity>}: a HistoricalGenericEntity QuerySet

            search {str | None}: an optional search parameter

            order_clause {str | None}: an optional order clause

        Returns:
            Either (a) dict[] array containing the results;
            or (b) a null value

    """
    results = None
    with connection.cursor() as cursor:
        sql = ''
        if not gen_utils.is_empty_string(search):
            sql = '''
            with
                entities as (
                    select *,
                        cast(regexp_replace(id, '[a-zA-Z]+', '') as integer) as true_id,
                        ts_rank_cd(
                            hge.search_vector,
                            websearch_to_tsquery('pg_catalog.english', %(searchterm)s)
                        ) as score
                      from public.clinicalcode_historicalgenericentity as hge
                     where id = ANY(%(entity_ids)s)
                       and history_id = ANY(%(history_ids)s)
                       and hge.search_vector @@ to_tsquery(
                            'pg_catalog.english',
                            replace(
                                websearch_to_tsquery('pg_catalog.english', %(searchterm)s)::text || ':*',
                                '<->', '|'
                            )
                       )
                     {0}
                ),
            '''
        else:
            sql = '''
            with
                entities as (
                    select *,
                           cast(regexp_replace(id, '[a-zA-Z]+', '') as integer) as true_id
                      from public.clinicalcode_historicalgenericentity
                     where id = ANY(%(entity_ids)s)
                       and history_id = ANY(%(history_ids)s)
                     {0}
                ),
            '''
        sql = sql.format(order_clause)

        sql = sql + '''
            children as (
                select entity.id as parent_id,
                       entity.history_id as parent_history_id,
                       concept.id as id,
                       concept.history_id as history_id,
                       concept.name as name,
                       codingsystem.id as coding_system,
                       codingsystem.name as coding_system_name,
                       'C' as prefix,
                       'concept' as type,
                       'concept_information' as field
                  from entities as entity,
                       json_array_elements(entity.template_data::json->'concept_information') as concepts
                  join public.clinicalcode_historicalconcept as concept
                    on concept.id = cast(concepts->>'concept_id' as integer)
                   and concept.history_id = cast(concepts->>'concept_version_id' as integer)
                  join public.clinicalcode_codingsystem as codingsystem
                    on codingsystem.id = concept.coding_system_id
            )

        select
            json_agg(
                json_build_object(
                    'id', entity.id,
                    'history_id', entity.history_id,
                    'name', entity.name,
                    'author', entity.author,
                    'children', child.children_data
                )
            )
          from entities as entity
          left join (
            select elem.parent_id,
                   elem.parent_history_id,
                   json_agg(
                        json_build_object(
                            'id', elem.id,
                            'history_id', elem.history_id,
                            'name', elem.name,
                            'prefix', elem.prefix,
                            'type', elem.type,
                            'field', elem.field,
                            'coding_system', elem.coding_system,
                            'coding_system_name', elem.coding_system_name
                        )
                   ) as children_data
              from children as elem
             group by elem.parent_id, elem.parent_history_id
          ) as child
            on entity.id = child.parent_id
           and entity.history_id = child.parent_history_id;
        '''
        
        entity_ids = list(entities.values_list('id', flat=True))
        history_ids = list(entities.values_list('history_id', flat=True))
        cursor.execute(
            sql,
            params={
                'entity_ids': entity_ids,
                'history_ids': history_ids,
                'searchterm': search,
            }
        )

        (results, ) = cursor.fetchone()
    
    return results

def try_search_template_descendants(entities, field_type, search=None, order_clause=None):
    """
        Method to search and collect descendants associated with Phenotypes
        from a HistoricalGenericEntity QuerySet

        [!] NOTE:
            1. `order_clause` is unsafe:
                Do not allow unknown inputs, only allow those defined
                within *entity_utils/constants.py*

            2. This method ignores permissions:
                It should only be called from a method that
                has previously considered accessibility

        Args:
            entities {QuerySet<HistoricalGenericEntity>}: a HistoricalGenericEntity QuerySet

            field_type {str}: describes the `field_type` within a template `field`'s `validation`

            search {str | None}: an optional search parameter

            order_clause {str | None}: an optional order clause

        Returns:
            Either (a) dict[] array containing the results;
            or (b) a null value

    """
    search = search if isinstance(search, str) else None
    order_clause = order_clause if isinstance(order_clause, str) else ''

    results = None
    if field_type == 'concept':
        results = try_search_child_concepts(entities, search=search, order_clause=order_clause)

    return results

@gen_utils.measure_perf
def get_template_entities(request, template_id, method='GET', force_term=True, field_type='concept'):
    """
        Method to get a Template's entities that:
            1. Are accessible to the RequestContext's user
            2. Match the query parameters

        Args:
            request {RequestContext}: the HTTP Request Context
            template_id {int | None}: optional template_id
            method {str}: the HTTP request method
            force_term {boolean}: whether to ensure validity and cleanliness of query parameters
            child_field {str}: the entity & template's field to consider when computing descendants

        Returns:
            A page of the results as defined by the query param
                - Contains the entities and their related children
                - Contains the pagination details

    """
    url_parameters = getattr(request, method, None)
    if not isinstance(url_parameters, dict):
        return None

    template = model_utils.try_get_instance(Template, pk=template_id)
    if template is None:
        return None
    
    if not template_utils.is_layout_safe(template):
        return None
    
    template_fields = template_utils.get_layout_fields(template)
    if template_fields is None:
        return None

    child_fields = template_utils.try_get_children_field_details(fields=template_fields)
    has_children = isinstance(child_fields, list) and len(child_fields) > 0
    valid_relation = next((x for x in child_fields if x.get('type') == field_type), None) if has_children else None
    if valid_relation is None:
        return {
            'results': [ ],
            'details': {
                'page': 1,
                'total': 1,
                'max_results': 0,
                'start_index': 0,
                'end_index': 0,
                'has_previous': False,
                'has_next': False,
            },
        }

    entities = permission_utils.get_accessible_entities(
        request,
        status=[constants.APPROVAL_STATUS.ANY]
    )

    metadata_filters = [key for key, value in constants.metadata.items() if 'search' in value and 'filterable' in value.get('search')]
    template_filters = [ ]

    for key, value in template_fields.items():
        if 'search' not in value or 'filterable' not in value.get('search'):
            continue
        template_filters.append(key)

    query = { }
    where = [ ]
    params = [ ]
    for param, data in url_parameters.items():
        if param in metadata_filters:
            apply_param_to_query(query, where, params, constants.metadata, param, data, force_term=force_term)
        elif param in template_filters:
            if template_fields is None:
                continue
            apply_param_to_query(query, where, params, template_fields, param, data, is_dynamic=True, force_term=force_term)

    entities = entities \
            .filter(Q(template__id=template_id) & Q(**query)) \
            .extra(where=where, params=params)

    parent_id = url_parameters.get('parent_id', None)
    parent_id = parent_id if not gen_utils.is_empty_string(parent_id) else None
    parent_history_id = gen_utils.parse_int(url_parameters.get('parent_history_id', None)) if parent_id is not None else None
    if parent_id and parent_history_id:
        entities = entities.exclude(id=parent_id, history_id=parent_history_id)

    search = gen_utils.try_get_param(request, 'search', None)
    search_order = gen_utils.try_get_param(request, 'order_by', '1', method)
    search_order = template_utils.try_get_content(constants.ORDER_BY, search_order)
    if search_order is None:
        search_order = constants.ORDER_BY['1']

    order_clause = 'order by true_id asc'
    if search_order == constants.ORDER_BY.get('1') and not gen_utils.is_empty_string(search):
        order_clause = 'order by score desc'
    elif search_order != constants.ORDER_BY.get('1'):
        order_clause = 'order by %s %s' % (search_order.get('property'), search_order.get('order'))

    results = try_search_template_descendants(entities, field_type=field_type, search=search, order_clause=order_clause)
    results = results or [ ]

    page_obj = try_get_paginated_results(request, results, page_size=10)
    obj_list = page_obj.object_list
    return {
        'results': obj_list,
        'details': {
            'page': page_obj.number,
            'total': page_obj.paginator.num_pages,
            'max_results': page_obj.paginator.count,
            'start_index': page_obj.start_index() if len(results) > 0 else 0,
            'end_index': page_obj.end_index() - (len(obj_list) - len(results)),
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
        },
    }

def reorder_search_results(search_results, order=None, searchterm=''):
    """
        Method to reorder a QuerySet after a group or distinct
        operation has been used during a previous filter

        Args:
            search_results (QuerySet): The current search result query set

            order (dict(constants.ORDER_BY)): The order by clause information

            searchterm (string): Any active searchterms - used to stop reorder
                                 when rank is being used
        
        Returns:
            A queryset containing all related codes of that particular coding system
    """
    if not isinstance(search_results, QuerySet):
        return QuerySet()

    order = order or constants.ORDER_BY.get('1')
    if order == constants.ORDER_BY.get('1') and not gen_utils.is_empty_string(searchterm):
        return search_results.order_by('-score')

    result_ids = None
    result_vds = None
    try:
        result_ids = list(search_results.values_list('id', flat=True))
        result_vds = list(search_results.values_list('history_id', flat=True))
    except:
        return search_results

    results = GenericEntity.history.filter(
        id__in=result_ids,
        history_id__in=result_vds
    )

    if order != constants.ORDER_BY['1']:
        return results.order_by(order.get('clause'))
    
    results = results.all().extra(
        select={'true_id': """CAST(REGEXP_REPLACE(id, '[a-zA-Z]+', '') AS INTEGER)"""}
    ) \
    .order_by('true_id')
    
    return results

def get_renderable_entities(request, entity_types=None, method='GET', force_term=True):
    """
        Method gets searchable, published entities and applies filters retrieved from the request param(s)

        Returns:
            1. The entities and their data
            2. The template associated with each of the entities
    """
    # Get entities relating to the user
    entities = permission_utils.get_accessible_entities(
        request,
        status=[constants.APPROVAL_STATUS.ANY]
    )

    if isinstance(entity_types, list) and len(entity_types) > 0:
        entities = entities.filter(template__entity_class__id__in=entity_types)

    # Get templates for each entity
    templates = Template.history.filter(
        id__in=entities.values_list('template', flat=True),
        template_version__in=entities.values_list('template_version', flat=True)
    ) \
    .order_by('id', 'template_version', '-history_id') \
    .distinct('id', 'template_version')

    is_single_search = templates.count() > constants.MIN_SINGLE_SEARCH
    
    # Gather request params for the filters across template when not single search
    template_filters = [ ]
    if not is_single_search:
        template_filters = set(template_filters)
        for template in templates:
            if not template_utils.is_layout_safe(template):
                continue
            
            field_items = template.definition.get('fields')
            if field_items is None:
                continue
            
            filters = [ ]
            for key, value in field_items.items():
                if 'search' not in value or 'filterable' not in value.get('search'):
                    continue
                filters.append(key)
            
            template_filters = template_filters | set(filters)
        
        template_filters = list(template_filters)
        template_fields = template_utils.get_layout_fields(templates.first())

    # Gather metadata filter params
    metadata_filters = [key for key, value in constants.metadata.items() if 'search' in value and 'filterable' in value.get('search')]
    
    # Build query from filters
    query = { }
    where = [ ]
    params = [ ]
    for param, data in getattr(request, method).items():
        if param in metadata_filters:
            if template_utils.is_single_search_only(constants.metadata, param) and not is_single_search:
                continue
            apply_param_to_query(query, where, params, constants.metadata, param, data, force_term=force_term, request=request)
        elif param in template_filters and not is_single_search:
            if template_fields is None:
                continue
            apply_param_to_query(query, where, params, template_fields, param, data, is_dynamic=True, force_term=force_term, request=request)
    
    # Collect all entities that are (1) published and (2) match request parameters
    entities = entities.filter(Q(**query))
    entities = entities.extra(where=where)

    # Prepare order clause
    search_order = gen_utils.try_get_param(request, 'order_by', '1', method)
    search_order = template_utils.try_get_content(constants.ORDER_BY, search_order)

    if search_order is None:
        search_order = constants.ORDER_BY['1']
    
    # Apply any search param if present
    search = gen_utils.try_get_param(request, 'search', None)
    if not gen_utils.is_empty_string(search):
        entity_ids = list(entities.values_list('id', flat=True))
        history_ids = list(entities.values_list('history_id', flat=True))

        entities = GenericEntity.history.extra(
            select={ 'score': '''ts_rank_cd("clinicalcode_historicalgenericentity"."search_vector", websearch_to_tsquery('pg_catalog.english', %s))'''},
            select_params=[search],
            where=[
                '''"clinicalcode_historicalgenericentity"."id" = ANY(%s)''',
                '''"clinicalcode_historicalgenericentity"."history_id" = ANY(%s)''',
                '''"clinicalcode_historicalgenericentity"."search_vector" @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', %s)::text || ':*', '<->', '|'))'''
            ],
            params=[entity_ids, history_ids, search]
        )

    # Reorder by user selection
    entities = reorder_search_results(entities, order=search_order, searchterm=search)

    # Generate layouts for use in templates
    layouts = { }
    for template in templates:
        layouts[f'{template.id}/{template.template_version}'] = {
            'id': template.id,
            'version': template.template_version,
            'name': template.name,
            'definition': template.definition,
            'order': template_utils.try_get_content(template.definition, 'layout_order', []),
        }

    return entities, layouts

def try_get_paginated_results(request, entities, page=None, page_size=None):
    """
        Gets the paginated results based on request params and the given renderable entities
    """
    if not page:
        page = gen_utils.try_get_param(request, 'page', 1)
        page = max(page, 1)

    if not page_size:
        page_size = gen_utils.try_get_param(request, 'page_size', '1')

        if page_size not in constants.PAGE_RESULTS_SIZE:
            page_size = constants.PAGE_RESULTS_SIZE.get('1')
        else:
            page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

    pagination = Paginator(entities, page_size, allow_empty_first_page=True)
    try:
        page_obj = pagination.page(page)
    except EmptyPage:
        page_obj = pagination.page(pagination.num_pages)
    return page_obj

def get_source_references(struct, default=None, modifier=None):
    """
        Retrieves the refence values from source fields e.g. tags, collections, entity type
    """
    validation = template_utils.try_get_content(struct, 'validation')
    if not validation:
        return default
    
    source_info = template_utils.try_get_content(validation, 'source')
    if not source_info:
        return default
    
    source = template_utils.try_get_content(source_info, 'table')
    relative = template_utils.try_get_content(source_info, 'relative')
    query = template_utils.try_get_content(source_info, 'query', 'pk')
    if not relative:
        return default
    
    try:
        model = apps.get_model(app_label='clinicalcode', model_name=source)
        objs = model.objects.all()

        if isinstance(modifier, dict):
            objs = objs.filter(**modifier)

        ref = []
        for obj in objs:
            pk = template_utils.try_get_instance_field(obj, query)
            data = template_utils.try_get_instance_field(obj, relative)
            if pk is not None and data is not None:
                ref.append({
                    'pk': pk,
                    'value': data
                })
        
        return ref
    except:
        return default

def get_filter_info(field, structure, default=None):
    """
        Compiles the filter_info for a given field
    """
    validation = template_utils.try_get_content(structure, 'validation')
    if validation is None:
        return default
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default
    
    return {
        'field': field,
        'type': field_type,
        'title': structure.get('title', field),
    }

def get_metadata_stats_by_field(field, published=False, brand='ALL'):
    """
        Retrieves the global statistics from metadata fields
    """
    instance = model_utils.try_get_instance(Statistics, type='GenericEntity', org=brand)
    if instance is not None:
        stats = instance.stat
        if published:
            stats = stats.get('published', dict)
        else:
            stats = stats.get('all', dict)
        
        return template_utils.try_get_content(stats, field)

def try_get_template_statistics(field, brand='ALL', published=False, entity_type='GenericEntity', default=None):
    """
        Attempts to retrieve the the field's statistics by brand, its publication status, and entity type
    """
    obj = model_utils.try_get_instance(Statistics, org=brand, type=entity_type)
    if obj is None:
        return default

    stats = template_utils.try_get_content(obj.stat, 'published' if published else 'all')
    if stats is None:
        return default

    return template_utils.try_get_content(stats, field)

def search_codelist_by_pattern(coding_system, pattern, use_desc=False, case_sensitive=True):
    """
        Tries to match a coding system's codes by a valid regex pattern

        Args:
            coding_system (obj): The coding system of interest
            pattern (str): The regex pattern
            use_desc (boolean): Whether to search via desc instead of code
            case_sensitive (boolean): Whether we use __regex or __iregex
        
        Returns:
            A queryset containing all related codes of that particular coding system
    """
    if not isinstance(coding_system, CodingSystem) or not isinstance(pattern, str):
        return None
    
    # Validate the pattern before allowing it to be used in search
    valid_pattern = False
    try:
        re.compile(pattern)
    except re.error:
        valid_pattern = False
    else:
        valid_pattern = True
    
    if not valid_pattern:
        return None

    # Match codes to pattern of that coding system
    table = coding_system.table_name.replace('clinicalcode_', '')
    codelist = apps.get_model(app_label='clinicalcode', model_name=table)

    codes = codelist.objects
    code_column = coding_system.code_column_name.lower()
    desc_column = coding_system.desc_column_name.lower()

    # Filter by filter clause held in coding system
    select_filter = coding_system.filter if coding_system.filter is not None else None
    if select_filter:
        codes = codes.extra(where=[select_filter])

    # Match by code/desc
    query_type = 'regex' if case_sensitive else 'iregex'

    if use_desc:
        codes = codes.filter(**{
            f'{desc_column}__{query_type}': pattern
        })
    else:
        codes = codes.filter(**{
            f'{code_column}__{query_type}': pattern
        })
    
    """
        Required because:
            1. Annotation needed to make naming structure consistent since the code tables aren't consistently named...
            2. Distinct required because there are duplicate entires...
    """
    codes = codes.extra(
        select={
            'code': code_column,
            'description': desc_column,
        }
    )
    
    codes = codes.order_by(code_column).distinct(code_column)
    return codes

def search_codelist_by_term(coding_system, search_term, use_desc=True):
    """
        Fuzzy match codes in a coding system by a search term

        Args:
            coding_system (obj): The coding system of interest
            search_term (str): The search term of interest
            use_desc (boolean): Whether to search via desc instead of code
        
        Returns:
            A queryset containing all related codes of that particular coding system
    """
    if not isinstance(coding_system, CodingSystem) or not isinstance(search_term, str):
        return None

    # Collect table info
    table = coding_system.table_name.replace('clinicalcode_', '')
    codelist = apps.get_model(app_label='clinicalcode', model_name=table)

    codes = codelist.objects
    code_column = coding_system.code_column_name.lower()
    desc_column = coding_system.desc_column_name.lower()

    # Filter by filter clause held in coding system
    select_filter = coding_system.filter if coding_system.filter is not None else None
    if select_filter:
        codes = codes.extra(where=[select_filter])

    # Search by code/desc
    if use_desc:
        codes = codes.filter(**{
            f'{desc_column}__icontains': search_term
        }) \
        .annotate(
            similarity=TrigramSimilarity(f'{desc_column}', search_term)
        )
    else:
        codes = codes.filter(**{
            f'{code_column}__icontains': search_term 
        }) \
        .annotate(
            similarity=TrigramSimilarity(f'{desc_column}', search_term)
        )

    """
        Required because:
            1. Annotation needed to make naming structure consistent since the code tables aren't consistently named...
            2. Distinct required because there are duplicate entires...
    """
    codes = codes.extra(
        select={
            'code': code_column,
            'description': desc_column,
        }
    )
    
    codes = codes.order_by(code_column, '-similarity').distinct(code_column)
    return codes

def search_codelist(coding_system, search_term, use_desc=False,
                    use_wildcard=False, case_sensitive=True, allow_wildcard=True):
    """
        Attempts to search a codelist by a search term, given its coding system

        Args:
            coding_system (obj): The assoc. coding system that is to be searched

            search_term (str): The search term used to query the table
            
            use_desc (boolean): Whether to search by description instead of code

            use_wildcard (boolean): Whether to search by wildcard

            case_sensitive (boolean): Whether we use __regex or __iregex - only applies to pattern search

            allow_wildcard (boolean): Whether to check for, and apply, regex patterns
                                    through the 'wildcard:' prefix
        
        Returns:
            The QuerySet of codes (assoc. with the given codingsystem) that match the
            search term
        
    """
    if not isinstance(coding_system, CodingSystem) or not isinstance(search_term, str):
        return None
    
    has_wildcard_prefix = search_term.lower().startswith('wildcard:')
    is_wildcard = use_wildcard or has_wildcard_prefix
    if allow_wildcard and is_wildcard:
        matches = search_term
        if has_wildcard_prefix:
            matches = re.search('^wildcard:(.*)', matches)
            matches = matches.group(1).lstrip()
        return search_codelist_by_pattern(coding_system, matches, use_desc, case_sensitive)
    
    return search_codelist_by_term(coding_system, search_term, use_desc)
