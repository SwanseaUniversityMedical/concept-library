from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

import re
import math

from ...entity_utils import gen_utils
from ...entity_utils import constants
from ...models.OntologyTag import OntologyTag

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontologies(request):
    """
        Get all ontology groups and their root
        nodes, _incl._ associated data such as the rood nodes, children _etc_

    """
    result = OntologyTag.get_groups([x.value for x in constants.ONTOLOGY_TYPES], default=[])
    return Response(
        data=list(result),
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_detail(request, ontology_id):
    """
        Get specified ontology group type detail by the given `ontology_id`
        type, including associated data _e.g._ root nodes, children _etc_

    """
    ontology_id = gen_utils.parse_int(ontology_id, default=None)
    if not isinstance(ontology_id, int):
        return Response(
            data={
                'message': 'Invalid ontology id, expected valid integer'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    result = OntologyTag.get_group_data(ontology_id, default=None)
    if not isinstance(result, dict):
        return Response(
            data={
                'message': f'Ontology of id {ontology_id} does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_node(request, node_id):
    """
        Gets an Ontology node by the given request
        by a given `node_id`

    """
    node_id = gen_utils.parse_int(node_id, default=None)
    if not isinstance(node_id, int):
        return Response(
            data={
                'message': 'Invalid node id, expected valid integer'
            },
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )

    result = OntologyTag.get_node_data(node_id, default=None)
    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_ontology_nodes(request):
    """
        Queries Ontology nodes by the given request
        parameters, returning a `QuerySet` of all
        matched node(s)

        | Param         | Type     | Default            | Desc                                                       |
        |---------------|----------|--------------------|------------------------------------------------------------|
        | search        | `string` | `NULL`             | Full-text search                                           |
        | codes         | `list`   | `NULL`             | Either (a) ICD-10 code; or (b) Code ID                     |
        | exact_codes   | `empty`  | `NULL`             | apply this parameter if you would like to search for exact codes instead of fuzzy matching the given `codes` across all related mappings (ICD-9/10, MeSH, OPSC4, ReadCodes etc) |
        | type_ids      | `list`   | `NULL`             | Filter ontology type by ID                                 |
        | reference_ids | `list`   | `NULL`             | Filter ontology by Atlas reference                         |
        | page          | `number` | `1`                | Page cursor                                                |
        | page_size     | `enum`   | `1` (_20_ results) | Page size enum, where: `1` = 20, `2` = 50 & `3` = 100 rows |
    """

    response = { }
    params = { key: value for key, value in request.query_params.items() }

    clauses = []
    row_clause = '''row_number() over (order by node.id asc) as rn,'''
    order_clause = '''order by node.rn asc'''
    count_clause = '''select reltuples as row_count from pg_class where relname = \'clinicalcode_ontologytag\''''

    page = params.pop('page', None)
    page = gen_utils.try_value_as_type(page, 'int')
    page = max(page, 1) if isinstance(page, int) else 1

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

    type_ids = params.pop('type_ids', None)
    type_ids = type_ids.split(',') if type_ids is not None else None
    type_ids = gen_utils.try_value_as_type(type_ids, 'int_array')
    if isinstance(type_ids, list):
        clauses.append('''node.type_id = any(%(type_ids)s)''')

    reference_ids = params.pop('reference_ids', None)
    reference_ids = reference_ids.split(',') if reference_ids is not None else None
    reference_ids = gen_utils.try_value_as_type(reference_ids, 'int_array')
    if isinstance(reference_ids, list):
        clauses.append('''node.reference_id = any(%(reference_ids)s)''')

    codes = params.pop('codes', None)
    codes = codes.split(',') if codes is not None else None
    codes = gen_utils.try_value_as_type(codes, 'string_array')

    alt_codes = None
    if isinstance(codes, list) and len(codes) > 0:
        codes = [ code.lower() for code in codes ]
        alt_codes = [ re.sub('[^0-9a-zA-Z]', '', code) for code in codes ]

        # Future Opt?
        #  -> Direct search for other coding systems?

        if 'exact_codes' not in request.query_params.keys():
            # Fuzzy across every code mapping
            clauses.append('''(
                (relation_vector @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', array_to_string(%(codes)s, '|'))::text || ':*', '<->', '|')))
                or (relation_vector @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', array_to_string(%(alt_codes)s, '|'))::text || ':*', '<->', '|')))
            )''')
        else:
            # Direct search for snomed
            clauses.append('''node.properties::json->>'code' is not null and (
                lower(node.properties::json->>'code'::text) = any(%(codes)s)
                or regexp_replace(lower(node.properties::json->>'code'::text), '[^aA-zZ0-9\-]', '', 'g') = any(%(alt_codes)s)
            )''')

    search = params.pop('search', None)
    search_rank = ''
    if isinstance(search, str) and not gen_utils.is_empty_string(search):
        # Future Opt?
        #  -> Change search params, i.e. across syn, rel or desc?

        # Fuzzy across code / desc / synonyms / relation
        clauses.append('''(
            node.search_vector
            @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', %(search)s)::text || ':*', '<->', '|'))
        )''')

        search_rank = '''ts_rank_cd(node.search_vector, websearch_to_tsquery('pg_catalog.english', %(search)s))'''
        row_clause = '''row_number() over (order by %s) as rn,''' % search_rank

        search_rank = search_rank + ' as score,'
        order_clause = '''order by node.score desc'''

    page_details = {
        'offset_start': (page - 1)*page_size,
        'offset_end': page*page_size,
        'page_size': page_size,
    }

    if len(clauses) > 0:
        node_limit = ''

        clauses = 'where (%s)' % (' and '.join(clauses), )
        count_clause = '''select max(rn) as row_count from records'''

        query_limit = '''
            where node.rn >= %(offset_start)s and node.rn < %(offset_end)s
            limit %(page_size)s
        ''' % page_details
    else:
        clauses = ''
        query_limit = ''

        node_limit = '''where node.id >= %(offset_start)s and node.id < %(offset_end)s
            group by match_id
            limit %(page_size)s
        ''' % page_details

    with connection.cursor() as cursor:
        sql = '''
        with
            matches as (
                select %(search_rank)s
                       %(row_clause)s
                       node.id as match_id
                  from public.clinicalcode_ontologytag as node
                 %(where)s
                 %(node_limit)s
            ),
            records as (
                select t0.*, t1.*
                  from matches as t0
                  join public.clinicalcode_ontologytag as t1
                    on t0.match_id = t1.id
            ),
            total_count as (
                %(count_clause)s
            ),
            results as (
                select
                    json_agg(jsonb_build_object(
                        'id', node.id,
                        'label', node.name,
                        'properties', node.properties,
                        'isLeaf', case when tree.child_count < 1 then True else False end,
                        'isRoot', case when tree.max_parents is NULL then True else False end,
                        'type_id', node.type_id,
                        'reference_id', node.reference_id,
                        'child_count', tree.child_count
                    ) %(order)s) as items
                from records as node
                join (
                    select rec.id, count(edges1.child_id) as child_count, max(edges0.parent_id) as max_parents
                      from records as rec
                      left outer join public.clinicalcode_ontologytagedge as edges0
                        on rec.id = edges0.child_id
                      left outer join public.clinicalcode_ontologytagedge as edges1
                        on rec.id = edges1.parent_id
                     group by rec.id
                ) as tree
                  on node.id = tree.id
               %(query_limit)s
            )
        select
            (select t.row_count from total_count as t) as total_rows,
            t0.items as items
          from results as t0;

        ''' % {
            'search_rank': search_rank,
            'row_clause': row_clause,
            'where': clauses,
            'order': order_clause,
            'count_clause': count_clause,
            'node_limit': node_limit,
            'query_limit': query_limit,
            'score_field': 'node.score,' if len(search_rank) > 0 else '',
        }
        
        cursor.execute(sql, params={
            'codes': codes,
            'alt_codes': alt_codes,
            'search': search,
            'type_ids': type_ids,
            'reference_ids': reference_ids,
        })

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        results = results[0] if len(results) > 0 else {}

        rows = results.get('items', None) or list()
        total_rows = gen_utils.parse_int(results.get('total_rows', 0), default=0)
        total_pages = math.ceil(total_rows / page_size)

        response = {
            'page': min(page, total_pages),
            'total_pages': total_pages,
            'page_size': page_size,
            'results': rows
        }

    return Response(
        data=response,
        status=status.HTTP_200_OK
    )

