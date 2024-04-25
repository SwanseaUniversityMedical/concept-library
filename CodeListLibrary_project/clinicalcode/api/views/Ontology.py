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
        Get all ontology categories and their root
        nodes, _incl._ associated data

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
@gen_utils.measure_perf
def get_ontology_nodes(request):
    """
        Queries Ontology nodes by the given request
        parameters, returning a `QuerySet` of all
        matched node(s)

        Query Params:
            - `page` - the page number cursor (defaults to 1)
            - `page_size` - denotes page size enum, where `1` = 20 rows, `2` = 50 rows and `3` = 100 rows
            - `codes` - one or more code(s) to filter on the related ontology code string
            - `search` - full-text search on ontology name(s)
            - `type_ids` - one or more id(s) to filter on ontology type
            - `atlas_ids` - one or more id(s) to filter on atlas reference id

    """
    response = { }
    params = { key: value for key, value in request.query_params.items() }

    clauses = []
    row_clause = '''row_number() over (order by node.id asc) as rn,'''
    order_clause = '''order by t.rn asc'''

    page = params.pop('page', None)
    page = gen_utils.try_value_as_type(page, 'int')
    page = max(page, 1) if isinstance(page, int) else 1

    page_size = params.pop('page_size', None)
    page_size = gen_utils.try_value_as_type(page_size, 'int')
    page_size = str(page_size) if isinstance(page_size, int) else '2'

    if page_size is None or page_size not in constants.PAGE_RESULTS_SIZE:
        page_size = constants.PAGE_RESULTS_SIZE.get('2')
    else:
        page_size = constants.PAGE_RESULTS_SIZE.get(str(page_size))

    type_ids = params.pop('type_ids', None)
    type_ids = type_ids.split(',') if type_ids is not None else None
    type_ids = gen_utils.try_value_as_type(type_ids, 'int_array')
    if isinstance(type_ids, list):
        clauses.append('''node.type_id = any(%(type_ids)s)''')

    atlas_ids = params.pop('atlas_ids', None)
    atlas_ids = atlas_ids.split(',') if atlas_ids is not None else None
    atlas_ids = gen_utils.try_value_as_type(atlas_ids, 'int_array')
    if isinstance(atlas_ids, list):
        clauses.append('''node.atlas_id = any(%(atlas_ids)s)''')

    codes = params.pop('codes', None)
    codes = codes.split(',') if codes is not None else None
    codes = gen_utils.try_value_as_type(codes, 'string_array')
    alt_codes = None
    if isinstance(codes, list):
        alt_cleaner = re.compile('[^0-9a-zA-Z]')

        codes = [ code.lower() for code in codes ]
        alt_codes = [ alt_cleaner.sub('', code) for code in codes ]
        clauses.append('''node.properties::json->>'code' is not null and (
            lower(node.properties::json->>'code'::text) = any(%(codes)s)
            or regexp_replace(lower(node.properties::json->>'code'::text), '[^aA-zZ0-9\-]', '', 'g') = any(%(alt_codes)s)
        )''')

    search = params.pop('search', None)
    search_rank = ''
    if isinstance(search, str):
        clauses.append('''(
            node.search_vector
            @@ to_tsquery('pg_catalog.english', replace(websearch_to_tsquery('pg_catalog.english', %(search)s)::text || ':*', '<->', '|'))
        )''')

        search_rank = '''ts_rank_cd(node.search_vector, websearch_to_tsquery('pg_catalog.english', %(search)s))'''
        row_clause = '''row_number() over (order by %s) as rn,''' % search_rank

        search_rank = search_rank + ' as score,'
        order_clause = '''order by t.score desc'''

    if len(clauses) > 0:
        clauses = 'where %s' % (' and '.join(clauses), )
    else:
        clauses = ''

    with connection.cursor() as cursor:
        sql = '''
        with
            recursive ancestry(parent_id, child_id, depth, path) as (
                select
                        n0.parent_id,
                        n0.child_id,
                        1 as depth,
                        array[n0.parent_id, n0.child_id] as path
                  from public.clinicalcode_ontologytagedge as n0
                  left outer join public.clinicalcode_ontologytagedge as n1
                    on n0.parent_id = n1.child_id
                union
                select
                        n2.parent_id,
                        ancestry.child_id,
                        ancestry.depth + 1 as depth,
                        n2.parent_id || ancestry.path
                  from ancestry
                  join public.clinicalcode_ontologytagedge as n2
                    on n2.child_id = ancestry.parent_id
            ),
            ancestors as (
                select
                        p0.child_id,
                        p0.path
                  from ancestry as p0
                  join (
                    select
                            child_id,
                            max(depth) as max_depth
                      from ancestry
                     group by child_id
                  ) as lim
                    on lim.child_id = p0.child_id
                   and lim.max_depth = p0.depth
            ),
            results as (
                select
                        %(search_rank)s
                        %(row_clause)s
                        jsonb_build_object(
                            'id', node.id,
                            'label', node.name,
                            'properties', node.properties,
                            'isLeaf', case when count(edges1.child_id) < 1 then True else False end,
                            'isRoot', case when max(edges0.parent_id) is NULL then True else False end,
                            'type_id', node.type_id,
                            'atlas_id', node.atlas_id,
                            'child_count', count(edges1.child_id)
                        ) as res
                  from public.clinicalcode_ontologytag as node
                  left outer join public.clinicalcode_ontologytagedge as edges0
                    on node.id = edges0.child_id
                  left outer join public.clinicalcode_ontologytagedge as edges1
                    on node.id = edges1.parent_id
                 %(where)s
                 group by node.id
            )

        select
            json_agg(t.res %(order)s) filter (where t.rn > %(offset_start)s and t.rn <= %(offset_end)s) items,
            count(*) as total_rows
          from results as t
         limit %(page_size)s;

        ''' % {
            'offset_start': (page - 1)*page_size,
            'offset_end': page*page_size,
            'page_size': page_size,
            'search_rank': search_rank,
            'row_clause': row_clause,
            'where': clauses,
            'order': order_clause
        }
        
        cursor.execute(sql, params={
            'codes': codes,
            'alt_codes': alt_codes,
            'search': search,
            'type_ids': type_ids,
            'atlas_ids': atlas_ids,
        })

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        results = results[0] if len(results) > 0 else []

        rows = results.get('items', None) or list()
        total_rows = results.get('total_rows', 0)

        response = {
            'page': page,
            'total_pages': math.ceil(total_rows / page_size),
            'page_size': page_size,
            'results': rows
        }

    return Response(
        data=response,
        status=status.HTTP_200_OK
    )

