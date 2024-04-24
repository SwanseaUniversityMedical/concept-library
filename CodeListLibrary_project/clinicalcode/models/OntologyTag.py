from django.apps import apps
from django.db import models, transaction, connection
from django.db.models import F, Count, Max, Case, When, Exists, OuterRef
from django.db.models.query import QuerySet
from django.db.models.functions import JSONObject
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.aggregates.general import ArrayAgg
from django_postgresql_dag.models import node_factory, edge_factory

from ..entity_utils import gen_utils
from ..entity_utils import constants

from .CodingSystem import CodingSystem

class OntologyTagEdge(edge_factory('OntologyTag', concrete=False)):
	"""
		OntologyTagEdge

			This class describes the parent-child relationship
			between two nodes - as defined by its `parent_id`
			and its `child_id`

	"""

	# Fields
	name = models.CharField(max_length=2048, unique=False)

	# Dunder methods
	def __str__(self):
		return self.name

	# Public methods
	def save(self, *args, **kwargs):
		"""
			Save override to appropriately style the instance's
			name field
		"""
		self.name = f'{self.parent.name} {self.child.name}'
		super().save(*args, **kwargs)

class OntologyTag(node_factory(OntologyTagEdge)):
	"""
		OntologyTag

			This class describes the fields for each node
			within an ontology group, separated by its `type_id`

			The relationship between nodes are described by
			the associated `OntologyTagEdge` instances, describing
			each node's relationship with another

			Together, these classes allow you to describe a graph
			of nodes that could be described as either a Directed
			Acyclic Graph or a Hierarchical Tree

			Ref:
				- Hierarchical Tree @ https://en.wikipedia.org/wiki/Tree_structure
				- Directed Acyclic Graph @ https://en.wikipedia.org/wiki/Directed_acyclic_graph

	"""

	# Fields
	name = models.CharField(max_length=1024, unique=False)
	type_id = models.IntegerField(choices=[(e.name, e.value) for e in constants.ONTOLOGY_TYPES])
	atlas_id = models.IntegerField(blank=True, null=True, unique=False)
	properties = models.JSONField(blank=True, null=True)

	# Metadata
	class Meta:
		ordering = ('type_id', 'id', )

		indexes = [
			models.Index(fields=['id', 'type_id']),
			GinIndex(
				name='ot_name_gin_idx',
				fields=['name']
			),
		]

	# Dunder methods
	def __str__(self):
		return self.name

	# Private methods
	def __validate_disease_code_id(self, properties, default=None):
		"""
			Attempts to validate the associated code id, should only
			be called for ontology instances that have a type_id
			which associates an instance with a specific code,
			e.g. ICD-10 category codes

			Args:
				self (<OntologyTag<models.Model>>): this instance

				properties (dict): the properties field associated
								   with this instance

				default (any|None): the default return value

			Returns:
				Either (a) the default value if none are found,
					or (b) the pk of the associated code
		"""
		if not isinstance(properties, dict):
			return default

		code = None
		try:
			desired_code = properties.get('code')
			desired_system_id = gen_utils.parse_int(properties.get('coding_system_id'), None)

			if not isinstance(desired_code, str) or not isinstance(desired_system_id, int):
				return default

			desired_system = CodingSystem.objects.filter(pk__eq=desired_system_id)
			desired_system = desired_system.first() if desired_system.exists() else None

			if desired_system is None:
				return default

			comparators = [ desired_code.lower(), desired_code.replace('.', '').lower() ]
			table_name = desired_system.table_name
			model_name = desired_system.table_name.replace('clinicalcode_', '')
			codes_name = desired_system.code_column_name.lower()

			query = """
				select *
				  from public.%(table_name)s
				 where lower(%(column_name)s);

				""" % { 'table_name': table_name, 'column_name': codes_name }

			codes = apps.get_model(app_label='clinicalcode', model_name=model_name)
			code = codes.objects.raw(query + ' = ANY(%(values)s::text[])', { 'values': comparators })
		except:
			code = None
		finally:
			if code is None or not code.exists():
				return default
			return code.first().pk

	# Public methods
	@classmethod
	def get_groups(cls, ontology_ids=None, default=None):
		"""
			Derives the tree model data given a list containing
			the model source and its associated label

			If no ontology_id list is provided we will return
			all root(s) of each type

			Args:
				ontology_ids (int[]|enum[]|none): an optional list of ontology model ids

				default (any|None): the default return value

			Returns:
				Either (a) the default value if none are found,
					or (b) a list of dicts containing the associated
						   tree model data

		"""
		if not isinstance(ontology_ids, list):
			ontology_ids = OntologyTag.objects.all().distinct('type_id').values_list('type_id')
			ontology_ids = list(ontology_ids)

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
			data = OntologyTag.get_group_data(model_source, model_label, default=default)
			if not isinstance(data, dict):
				continue

			if output is None:
				output = []

			output.append(data)

		return output

	@classmethod
	def get_group_data(cls, model_source, model_label=None, default=None):
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
						properties=F('properties'),
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

	@classmethod
	def get_node_data(cls, node_id, ontology_id=None, model_label=None, default=None):
		"""
			Derives the ontology node data given the node id

			Args:
				node_id (int): the node id

				ontology_id (int|enum|none): optional ontology model id

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

		if not isinstance(node_id, int):
			return default

		try:
			node = None
			if isinstance(model_source, int):
				node = OntologyTag.objects.filter(id=node_id, type_id=model_source)
			else:
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
							properties=F('properties'),
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
							properties=F('properties'),
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
				'properties': node.properties,
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

	@classmethod
	def build_tree(cls, descendant_ids, default=None):
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
									'properties', nodes.properties,
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

	@classmethod
	def get_full_names(cls, node, default=None):
		"""
			Derives the full name(s) of the root path
			from a given node

			Args:
				node (OntologyTag<Instance>): the node instance
				default (any): the default return value
			
			Returns:
				Returns either (a) the full name string, if applicable;
									  OR (b) the default return value if no roots available
			
		"""
		roots = [node.name for node in node.roots()]
		if len(roots) > 0:
			roots = '; '.join(roots)
			roots = f'from {roots}'
			return roots

		return default

	@classmethod
	def get_detail_data(cls, node_ids, default=None):
		"""
			Attempts to derive the ontology data associated with a given a list of nodes
			as described by a GenericEntity's template data

			[!] Note: No validation on the type of input is performed here, you are expected
			          to perform this validation prior to calling this method

			Args:
				node_ids (int[]): a list of node ids

				default (any|None): the default return value

			Returns:
				Either (a) the default value if we're unable to resolve the data,
					 OR; (b) a list of dicts containing the associated data

		"""
		nodes = OntologyTag.objects.filter(id__in=node_ids)
		roots = { node.id: OntologyTag.get_full_names(node) for node in nodes if not node.is_root() and not node.is_island() }

		nodes = nodes \
			.annotate(
				child_count=Count(F('children'))
			) \
			.annotate(
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
					isLeaf=Case(
						When(child_count__lt=1, then=True),
						default=False
					),
					type_id=F('type_id')
				)
			) \
			.values_list('tree_dataset', flat=True)

		nodes = [
			node | { 'full_names': roots.get(node.get('id')) }
			if not node.get('isRoot') and roots.get(node.get('id')) else node
			for node in nodes
		]
	
		return nodes

	@classmethod
	def get_creation_data(cls, node_ids, type_ids, default=None):
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
				OntologyTag.get_node_data(ancestor.id, default=None)
				for ancestor in node.ancestors()
			]
			for node in nodes
			if not node.is_root() and not node.is_island()
		]

		return {
			'ancestors': ancestors,
			'value': [OntologyTag.get_node_data(node_id) for node_id in node_ids],
		}

	@classmethod
	def get_detailed_source_value(cls, node_ids, type_ids, default=None):
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

	@transaction.atomic
	def save(self, *args, **kwargs):
		"""
			Save override to apply validation or
			modification methods dependent on the
			associated `type_id`
		"""
		internal_type = self.type_id
		if internal_type == constants.ONTOLOGY_TYPES.CLINICAL_DISEASE:
			code_id = self.__validate_disease_code_id(self.properties)
			if isinstance(code_id, int):
				self.properties.update({ 'code_id': code_id })

		super().save(*args, **kwargs)
