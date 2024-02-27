from django.apps import apps
from django.db.models import F, Count, Max, Case, When
from django.db.models.query import QuerySet
from django.db.models.functions import JSONObject

from . import gen_utils

def try_get_tree_data(model_source, model_label=None, default=None):
    """
        Derives the tree model data given the model source name

        Args:
            model_source (str): the tree model name

            model_label (str|None): the associated model label

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a dict containing the associated tree model data
    """
    if not isinstance(model_source, str) or gen_utils.is_empty_string(model_source):
        return default

    try:
        model = apps.get_model(app_label='clinicalcode', model_name=model_source)
        model_roots = model.objects.roots() if model is not None else None
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
                    child_count=F('child_count')
                )
            ) \
            .values_list('tree_dataset', flat=True)
    except:
        pass
    else:
        return {
            'nodes': list(model_roots),
            'model': { 'source': model_source, 'label': model_label or model_source },
        }
    
    return default

def try_get_tree_models_data(desired_models, default=None):
    """
        Derives the tree model data given a list containing the model source and its associated label

        Args:
            desired_models (dict{label: str|None, source: str}[]):
                a list of dicts {label: str|None, source: str} describing the ontologies

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a list of dicts containing the associated tree model data

    """
    if not isinstance(desired_models, list):
        return default

    output = None
    for model_data in desired_models:
        if not isinstance(model_data, dict):
            continue

        model_label = model_data.get('label')
        model_source = model_data.get('source')

        data = try_get_tree_data(model_source, model_label, default=default)
        if not isinstance(data, dict):
            continue

        if output is None:
            output = []
        
        output.append(data)

    return output

def try_get_tree_node_data(model_source, node_id, model_label=None, default=None):
    """
        Derives the node data given the model source name and the node id

        Args:
            model_source (str): the tree model name

            node_id (int): the node id

            default (any|None): the default return value

        Returns:
            Either (a) the default value if none are found,
                or (b) a dict containing the associated node's data
    """

    if not isinstance(model_source, str) or gen_utils.is_empty_string(model_source):
        return default

    if not isinstance(node_id, int):
        return default

    try:
        model = apps.get_model(app_label='clinicalcode', model_name=model_source)

        node = model.objects.filter(id=node_id)
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
                        )
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
                        child_count=F('child_count')
                    )
                ) \
                .values_list('tree_dataset', flat=True)
        else:
            children = []

        is_root = node.is_root()
        is_leaf = node.is_leaf()

        result = {
            'id': node_id,
            'label': node.name,
            'model': { 'source': model_source, 'label': model_label or model_source },
            'parents': parents,
            'children': children,
            'isRoot': is_root,
            'isLeaf': is_leaf,
        }

        if not is_root:
            roots = [ { 'id': x.id, 'label': x.name } for x in node.roots() ]
            result.update({ 'roots': roots })

        return result
    except:
        pass

    return default