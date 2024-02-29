from django.db.models import F, Count, Max, Case, When
from django.db.models.query import QuerySet
from django.db.models.functions import JSONObject

from . import gen_utils, constants
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
    except Exception as e:
        print(e)
        pass
    else:
        model_label = model_label or constants.ONTOLOGY_LABELS[constants.ONTOLOGY_TYPES(model_source)]
        return {
            'nodes': list(model_roots),
            'model': { 'source': model_source, 'label': model_label },
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

def try_get_ontology_node_data(ontology_id, node_id, model_label=None, default=None):
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
            parents = parents.values('id', 'name') \
                .annotate(
                    max_parent_id=Max(F('parents'))
                ) \
                .annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        isRoot=Case(
                            When(max_parent_id__isnull=True, then=True),
                            default=False
                        ),
                        type_id=F('type_id'),
                        atlas_id=F('atlas_id')
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            parents = []

        children = node.children.all()
        if children.count() > 0:
            children = children.values('id', 'name') \
                .annotate(
                    max_parent_id=Max(F('parents')),
                    child_count=Count(F('children'))
                ) \
                .annotate(
                    tree_dataset=JSONObject(
                        id=F('id'),
                        label=F('name'),
                        isRoot=Case(
                            When(max_parent_id__isnull=True, then=True),
                            default=False
                        ),
                        isLeaf=Case(
                            When(child_count__lt=1, then=True),
                            default=False
                        ),
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
            'parents': parents,
            'children': children,
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
