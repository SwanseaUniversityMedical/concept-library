from django.db import connection
from django.db.models import F, Count, Max, Case, When, Exists, OuterRef
from django.db.models.query import QuerySet
from django.db.models.functions import JSONObject
from django.contrib.postgres.aggregates.general import ArrayAgg

from . import constants
from . import gen_utils

from ..models.OntologyTag import OntologyTag

def try_get_ontology_data(model_source, model_label=None, default=None):
    """
        Derives the tree model data given the model source name

        Args:
            model_source (int|enum): the ontology id

            model_label (str|None): the associated model label

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a dict containing the associated tree model data
    """
    if isinstance(model_source, constants.ONTOLOGY_TYPES):
        model_source = model_source.value
    elif not isinstance(model_source, int) or model_source not in constants.ONTOLOGY_TYPES:
        return default

    try:
        model_roots = OntologyTag.objects.roots().filter(type_id=model_source)
        model_roots_len = model_roots.count() if isinstance(model_roots, QuerySet) else 0
        if model_roots_len < 1:
            return default

        model_roots = model_roots.values('id', 'name') \
            .annotate(
                child_count=Count(F('children')),
                max_parent_id=Max(F('parents'))
            ) \
            .annotate(
                tree_dataset=JSONObject(
                    id=F('id'),
                    label=F('name'),
                    isLeaf=Case(
                        When(child_count__lt=1, then=True),
                        default=False
                    ),
                    isRoot=Case(
                        When(max_parent_id__isnull=True, then=True),
                        default=False
                    ),
                    type_id=F('type_id'),
                    atlas_id=F('atlas_id'),
                    child_count=F('child_count')
                )
            ) \
            .values_list('tree_dataset', flat=True)
    except:
        pass
    else:
        model_label = model_label or constants.ONTOLOGY_LABELS[constants.ONTOLOGY_TYPES(model_source)]
        return {
            'model': { 'source': model_source, 'label': model_label },
            'nodes': list(model_roots),
        }

    return default

def try_get_ontology_model_data(ontology_ids, default=None):
    """
        Derives the tree model data given a list containing the model source and its associated label

        Args:
            ontology_ids (int[]|enum[]): a list of ontology model ids

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a list of dicts containing the associated tree model data

    """
    if not isinstance(ontology_ids, list):
        return default

    output = None
    for ontology_id in ontology_ids:
        model_source = None
        if isinstance(ontology_id, constants.ONTOLOGY_TYPES):
            model_source = ontology_id.value
        elif isinstance(ontology_id, int) and ontology_id in constants.ONTOLOGY_TYPES:
            model_source = ontology_id

        if not isinstance(model_source, int):
            continue

        model_label = constants.ONTOLOGY_LABELS[constants.ONTOLOGY_TYPES(ontology_id)]
        data = try_get_ontology_data(model_source, model_label, default=default)
        if not isinstance(data, dict):
            continue

        if output is None:
            output = []
        
        output.append(data)

    return output

def try_get_ontology_node_data(node_id, model_label=None, default=None):
    """
        Derives the ontology node data given the node id

        Args:
            node_id (int): the node id

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a dict containing the associated node's data
    """

    try:
        node = OntologyTag.objects.filter(id=node_id)
        node = node.first() if node.exists() else None
        if node is None:
            return default

        model_source = node.type_id
        parents = node.parents.all()
        if parents.count() > 0:
            parents = parents.annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        isRoot=Case(
                            When(
                                Exists(OntologyTag.parents.through.objects.filter(
                                    child_id=OuterRef('pk'),
                                )),
                                then=False
                            ),
                            default=True
                        ),
                        isLeaf=False,
                        type_id=F('type_id'),
                        atlas_id=F('atlas_id'),
                        child_count=Count(F('children')),
                        parents=ArrayAgg('parents', distinct=True)
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            parents = []

        children = node.children.all()
        if children.count() > 0:
            children = OntologyTag.objects.filter(id__in=children) \
                .annotate(
                    child_count=Count(F('children'))
                ) \
                .annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        isRoot=False,
                        isLeaf=Case(
                            When(child_count__lt=1, then=True),
                            default=False
                        ),
                        type_id=F('type_id'),
                        atlas_id=F('atlas_id'),
                        child_count=F('child_count'),
                        parents=ArrayAgg('parents', distinct=True)
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            children = []

        is_root = node.is_root() or node.is_island()
        is_leaf = node.is_leaf()

        model_label = model_label or constants.ONTOLOGY_LABELS[constants.ONTOLOGY_TYPES(model_source)]

        result = {
            'id': node_id,
            'label': node.name,
            'model': { 'source': model_source, 'label': model_label },
            'isRoot': is_root,
            'isLeaf': is_leaf,
            'type_id': node.type_id,
            'atlas_id': node.atlas_id,
            'child_count': len(children),
            'parents': list(parents) if not isinstance(parents, list) else parents,
            'children': list(children) if not isinstance(children, list) else children,
        }

        if not is_root:
            roots = [ { 'id': x.id, 'label': x.name } for x in node.roots() ]
            result.update({ 'roots': roots })

        return result
    except:
        pass

    return default

def try_get_ontology_group_node_data(ontology_id, node_id, model_label=None, default=None):
    """
        Derives the ontology node data given the model id name and the node id

        Args:
            ontology_id (int|enum): the ontology model id

            node_id (int): the node id

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a dict containing the associated node's data
    """

    model_source = None
    if isinstance(ontology_id, constants.ONTOLOGY_TYPES):
        model_source = ontology_id.value
    elif isinstance(ontology_id, int) and ontology_id in constants.ONTOLOGY_TYPES:
        model_source = ontology_id

    if not isinstance(node_id, int) or not isinstance(model_source, int):
        return default

    try:
        node = OntologyTag.objects.filter(id=node_id, type_id=model_source)
        node = node.first() if node.exists() else None
        if node is None:
            return default

        parents = node.parents.all()
        if parents.count() > 0:
            parents = parents.annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        parents=ArrayAgg('parents', distinct=True),
                        isRoot=Case(
                            When(
                                Exists(OntologyTag.parents.through.objects.filter(
                                    child_id=OuterRef('pk'),
                                )),
                                then=False
                            ),
                            default=True
                        ),
                        isLeaf=False,
                        type_id=F('type_id'),
                        atlas_id=F('atlas_id')
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            parents = []

        children = node.children.all()
        if children.count() > 0:
            children = OntologyTag.objects.filter(id__in=children) \
                .annotate(
                    child_count=Count(F('children'))
                ) \
                .annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        isRoot=False,
                        isLeaf=Case(
                            When(child_count__lt=1, then=True),
                            default=False
                        ),
                        parents=ArrayAgg('parents', distinct=True),
                        type_id=F('type_id'),
                        atlas_id=F('atlas_id'),
                        child_count=F('child_count')
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            children = []

        is_root = node.is_root()
        is_leaf = node.is_leaf()

        model_label = model_label or constants.ONTOLOGY_LABELS[constants.ONTOLOGY_TYPES(model_source)]

        result = {
            'id': node_id,
            'label': node.name,
            'model': { 'source': model_source, 'label': model_label },
            'parents': list(parents) if not isinstance(parents, list) else parents,
            'children': list(children) if not isinstance(children, list) else children,
            'isRoot': is_root,
            'isLeaf': is_leaf,
            'type_id': node.type_id,
            'atlas_id': node.atlas_id,
        }

        if not is_root:
            roots = [ { 'id': x.id, 'label': x.name } for x in node.roots() ]
            result.update({ 'roots': roots })

        return result
    except:
        pass

    return default

def try_build_ontology_tree(descendant_ids, default=None):
    """
        Attempts to derive the ontology tree data associated given a list of node
        descendant ids

        Note: This is used to fill in the tree before sending it to the create page,
              which allows for the selection(s) to be correctly displayed without
              querying the entire tree

        Args:
            descendant_ids (int[]): a list of node descendant ids

            default (any|None): the default return value

        Returns:
            Either (a) the default value if we're unable to resolve the data,
                or (b) a list of dicts containing the associated node's data
                       and its ancestry data

    """
    if not isinstance(descendant_ids, list):
        return default

    ancestry = default
    try:
        with connection.cursor() as cursor:
            sql = '''
            with
                recursive ancestry(parent_id, child_id, depth, path) as (
                    select n0.parent_id,
                           n0.child_id,
                           1 as depth,
                           array[n0.parent_id, n0.child_id] as path
                      from public.clinicalcode_ontologytagedge as n0
                      left outer join public.clinicalcode_ontologytagedge as n1
                        on n0.parent_id = n1.child_id
                     where n0.child_id = any(%(node_ids)s)
                     union
                    select n2.parent_id,
                           ancestry.child_id,
                           ancestry.depth + 1 as depth,
                           n2.parent_id || ancestry.path
                      from ancestry
                      join public.clinicalcode_ontologytagedge as n2
                        on n2.child_id = ancestry.parent_id
                ),
                ancestors as (
                    select p0.child_id,
                           p0.path
                      from ancestry as p0
                      join (
                                select child_id,
                                       max(depth) as max_depth
                                  from ancestry
                                 group by child_id
                           ) as lim
                        on lim.child_id = p0.child_id
                       and lim.max_depth = p0.depth
                ),
                objects as (
                    select selected.child_id,
                           jsonb_build_object(
                                'id', nodes.id,
                                'label', nodes.name,
                                'isLeaf', case when count(edges1.child_id) < 1 then True else False end,
                                'isRoot', case when max(edges0.parent_id) is NULL then True else False end,
                                'type_id', nodes.type_id,
                                'atlas_id', nodes.atlas_id,
                                'child_count', count(edges1.child_id)
                           ) as tree
                      from (
                                select id,
                                       child_id
                                  from ancestors,
                                       unnest(path) as id
                                 group by id, child_id
                            ) as selected
                      join public.clinicalcode_ontologytag as nodes
                        on nodes.id = selected.id
                      left outer join public.clinicalcode_ontologytagedge as edges0
                        on nodes.id = edges0.child_id
                      left outer join public.clinicalcode_ontologytagedge as edges1
                        on nodes.id = edges1.parent_id
                     group by selected.child_id, nodes.id
                )

            select ancestor.child_id,
                   ancestor.path,
                   json_agg(obj.tree) as dataset
              from ancestors as ancestor
              join objects as obj
                on obj.child_id = ancestor.child_id
             group by ancestor.child_id, ancestor.path;
            '''

            cursor.execute(
                sql,
                params={ 'node_ids': descendant_ids }
            )

            columns = [col[0] for col in cursor.description]
            ancestry = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except:
        pass

    return ancestry

def try_get_ontology_creation_data(node_ids, type_ids, default=None):
    """
        Attempts to derive the ontology data associated given a list of nodes
        and their type_ids - will return the default value if it fails.

        This is a required step in preparing the creation data, since we
        need to derive the path of each node so that we can merge it into the given
        root node data.

        Args:
            node_ids (int[]): a list of node ids

            type_ids (int): the ontology type ids

            default (any|None): the default return value

        Returns:
            Either (a) the default value if we're unable to resolve the data,
                or (b) a dict containing the value id(s) and any pre-fetched ancestor-related data 

    """
    if not isinstance(node_ids, list) or not isinstance(type_ids, list):
        return default

    node_ids = [int(node_id) for node_id in node_ids if gen_utils.parse_int(node_id, default=None) is not None]
    type_ids = [int(type_id) for type_id in type_ids if gen_utils.parse_int(type_id, default=None) is not None]

    if len(node_ids) < 1 or len(type_ids) < 1:
        return default

    nodes = OntologyTag.objects.filter(id__in=node_ids, type_id__in=type_ids)
    ancestors = [
        [
            try_get_ontology_node_data(ancestor.id, default=None)
            for ancestor in node.ancestors()
        ]
        for node in nodes
        if not node.is_root() and not node.is_island()
    ]

    return {
        'ancestors': ancestors,
        'value': [try_get_ontology_node_data(node_id) for node_id in node_ids],
    }

def get_detailed_sourced_ontology_value(node_ids, type_ids, default=None):
    """
        Attempts to format the ontology data in a similar to manner
        that's composed via `template_utils.get_detailed_sourced_value()`

        Args:
            node_ids (int[]): a list of node ids

            type_ids (int): the ontology type ids

            default (any|None): the default return value

        Returns:
            Either (a) the default value if we're unable to resolve the data,
                or (b) a list of objects containing the sourced value data

    """
    if not isinstance(node_ids, list) or not isinstance(type_ids, list):
        return default

    node_ids = [int(node_id) for node_id in node_ids if gen_utils.parse_int(node_id, default=None) is not None]
    type_ids = [int(type_id) for type_id in type_ids if gen_utils.parse_int(type_id, default=None) is not None]

    if len(node_ids) < 1 or len(type_ids) < 1:
        return default

    nodes = OntologyTag.objects.filter(id__in=node_ids, type_id__in=type_ids)
    if nodes.count() < 1:
        return default

    return list(nodes.annotate(value=F('id')).values('name', 'value'))
