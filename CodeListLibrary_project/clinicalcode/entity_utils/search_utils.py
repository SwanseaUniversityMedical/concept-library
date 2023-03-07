from django.apps import apps
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator
from django.contrib.postgres.search import TrigramSimilarity, SearchQuery, SearchRank, SearchVector
import json

from ..models import PublishedGenericEntity, GenericEntity, Template, Statistics
from . import model_utils, permission_utils, template_utils, constants, gen_utils

def get_request_body(body):
    '''
        Decodes the body of a request and attempts to load it as JSON
    '''
    try:
        body = body.decode('utf-8');
        body = json.loads(body)
        return body
    except:
        return None

def try_get_param(request, key, default=None, method='GET'):
    '''
        Attempts to get a param from a request by key
            - If a default is passed and the key isn't present, the default is returned
            - If the key is present, and the default is non-null, it tries to parse the value as the default's type
    '''
    try:
        req = getattr(request, method)
        param = req.get(key, default)
    except:
        return default
    else:
        if default is not None:
            if type(key) is not type(default):
                if isinstance(default, int):
                    return gen_utils.parse_int(param)
                # Add other types when necessary

    return param

def perform_vector_search(queryset, search_query, min_rank=0.05, order_by_relevance=True, reverse_order=False):
    '''
        Performs a search on generic entities' indexed search_vector field, includes the following fields:
            1. Name
            2. Definition
            3. Author
    '''
    query = SearchQuery(search_query)
    if order_by_relevance:
        vector = SearchVector('name', 'author', 'definition')
        rank = SearchRank(vector, query)
        clause = '-rank' if not reverse_order else 'rank'

        return queryset.annotate(
            search=vector,
            rank=rank
        ) \
        .filter(Q(rank__gte=min_rank) & Q(search=query)) \
        .order_by(clause)

    return queryset.filter(Q(name__search=query) | Q(author__search=query) | Q(definition__search=query))

def perform_trigram_search(queryset, search_query, min_similarity=0.2, order_by_relevance=True, reverse_order=False):
    '''
        Performs trigram fuzzy search on generic entities, includes the following indexed fields:
            1. Name
            2. Definition
            3. Author
    '''
    if order_by_relevance:
        clause = '-similarity' if not reverse_order else 'similarity'
        return queryset.annotate(
            similarity=(
                TrigramSimilarity('name', search_query) + \
                TrigramSimilarity('definition', search_query) + \
                TrigramSimilarity('author', search_query)
            )
        ) \
        .filter(Q(similarity__gte=min_similarity)) \
        .order_by(clause)
    
    return queryset.filter(
        Q(name__trigram_similar=search_query) | \
        Q(definition__trigram_similar=search_query) | \
        Q(author__trigram_similar=search_query)
    )

def search_entities(queryset, search_query, min_threshold=0.05, fuzzy=True, order_by_relevance=True, reverse_order=False):
    '''
        Utility method to perform either trigram or vector search
    '''
    if fuzzy:
        return perform_trigram_search(queryset, search_query, min_threshold, order_by_relevance, reverse_order)

    return perform_vector_search(queryset, search_query, min_threshold, order_by_relevance, reverse_order)

def search_entity_fields(queryset, search_query, fields=[], min_threshold=0.05, fuzzy=True, order_by_relevance=True, reverse_order=False):
    '''
        Utility method to search one or more fields of a generic entity based on the parameters of this method
    '''

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

def validate_query_param(template, data, default=None):
    '''
        Validates the query param based on its field type as defined by the template or metadata by examining its source
    '''
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
                    query = query | source_info['filter']
                
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

def apply_param_to_query(query, template, param, data, is_dynamic=False, force_term=False):
    '''
        Tries to apply a URL param to a query if its able to resolve and validate the param data
    '''
    template_data = template_utils.try_get_content(template, param)
    search = template_utils.try_get_content(template_data, 'search')
    if search is None or not 'filterable' in search:
        return False

    validation = template_utils.try_get_content(template_data, 'validation')
    if validation is None:
        return False
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return False
    
    if field_type == 'int' or field_type == 'enum':
        data = [int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None)]
        if not force_term:
            data = validate_query_param(template_data, data)

        if data is not None:
            if is_dynamic:
                query[f'template_data__{param}__in'] = data
            else:
                query[f'{param}__in'] = data
            return True
    elif field_type == 'int_array':
        data = [int(x) for x in data.split(',') if gen_utils.parse_int(x, default=None)]
        if not force_term:
            data = validate_query_param(template_data, data)

        if data is not None:
            if is_dynamic:
                query[f'template_data__{param}__contains'] = data
            else:
                query[f'{param}__overlap'] = data
            return True
    
    return False

def get_renderable_entities(request, entity_type=None, method='GET'):
    '''
        Method gets searchable, published entities and applies filters retrieved from the request param(s)

        Returns:
            1. The entities and their data
            2. The template associated with each of the entities
    '''
    if entity_type is None:
        templates = Template.objects.filter(entity_class__entity_count__gt=0)
    else:
        if isinstance(entity_type, list):
            templates = Template.objects.filter(id__in=entity_type)
        else:
            templates = Template.objects.filter(id=entity_type)
    
    # Collect the relevant template(s)
    layouts = { }
    templates = templates.order_by('id')
    for template in templates:
        layouts[template.entity_class.entity_prefix] = {
            'id': template.id,
            'name': template.name,
            'definition': template.definition,
            'order': template.entity_order,
            'statistics': template.entity_statistics,
        }

    is_single_search = Template.objects.count() > constants.MIN_SINGLE_SEARCH
    template_ids = list(templates.values_list('id', flat=True))

    # Get all entities assoc. with the template(s) requested
    entities = GenericEntity.objects.filter(template__in=template_ids).all()
    entities = PublishedGenericEntity.objects.filter(entity__in=entities).order_by('-created').distinct()
    
    # Gather request params for the filters across template when not single search
    template_filters = [ ]
    if not is_single_search:
        filters = set([])
        for items in templates.values_list('entity_filters', flat=True).distinct():
            filters = filters | set(items)
        template_filters = list(filters)

        template_fields = list(layouts.values())
        if len(template_fields) > 0:
            template_fields = template_utils.get_layout_fields(template_fields[0])

    # Gather metadata filter params
    metadata_filters = [key for key, value in constants.metadata.items() if 'search' in value and 'filterable' in value.get('search')]
    
    # Build query from filters
    query = { }
    for param, data in getattr(request, method).items():
        if param in metadata_filters:
            if template_utils.is_single_search_only(constants.metadata, param) and not is_single_search:
                continue
            apply_param_to_query(query, constants.metadata, param, data)
        elif param in template_filters and not is_single_search:
            if template_fields is None:
                continue
            apply_param_to_query(query, template_fields, param, data, is_dynamic=True)
    
    # Collect all entities that are (1) published and (2) match request parameters
    entities = GenericEntity.history.filter(
        Q(**query) \
        & \
        Q(
            history_id__in=list(entities.values_list('entity_history_id', flat=True)),
            id__in=list(entities.values_list('entity_id', flat=True))
        )
    )

    # Prepare order clause
    search_order = try_get_param(request, 'order_by', '1', method)
    should_order_search = search_order == '1'
    search_order = template_utils.try_get_content(constants.ORDER_BY, search_order)
    if search_order is None:
        search_order = constants.ORDER_BY['1']
    
    # Apply any search param if present
    search = try_get_param(request, 'search', None)
    if search is not None:
        entities = search_entities(queryset=entities, search_query=search, order_by_relevance=should_order_search, fuzzy=True, min_threshold=0.1)

    # Reorder by user selection
    if search_order != constants.ORDER_BY['1'] or search is None:
        entities = entities.order_by(search_order.get('clause'))

    return entities, layouts

def try_get_paginated_results(request, entities, page=None, page_size=None):
    '''
        Gets the paginated results based on request params and the given renderable entities
    '''
    if not page:
        page = try_get_param(request, 'page', 1)

    if not page_size:
        page_size = try_get_param(request, 'page_size', '1')

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

def get_metadata_stats_by_field(field):
    '''
        Retrieves the global statistics from metadata fields
    '''
    instance = model_utils.try_get_instance(Statistics, type='metadata')
    if instance is not None:
        stats = instance.stat
        return template_utils.try_get_content(stats, field)

def get_source_references(struct, default=[]):
    '''
        Retrieves the refence values from source fields e.g. tags, collections, entity type
    '''
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
    '''
        Compiles the filter_info for a given field
    '''
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

def try_get_template_statistics(struct, field, default=None):
    '''
        Attempts to retrieve the statistics for a templated field from its parent template
    '''
    if not template_utils.is_layout_safe(struct):
        return default

    stats = template_utils.try_get_content(struct, 'statistics') if isinstance(struct, dict) else getattr(struct, 'entity_statistics')
    if stats is None:
        return default
    
    stats = template_utils.try_get_content(stats, field)
    if stats is None:
        return default
    
    return stats
