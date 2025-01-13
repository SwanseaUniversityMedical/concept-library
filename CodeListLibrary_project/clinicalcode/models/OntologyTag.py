from django.apps import apps
from django.db import models, transaction, connection
from django.db.models import F, Count, Max, Case, When, Exists, OuterRef
from django.db.models.query import QuerySet
from django.db.models.functions import JSONObject
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.aggregates.general import ArrayAgg
from django_postgresql_dag.models import node_factory, edge_factory

import logging

from ..entity_utils import gen_utils
from ..entity_utils import constants

from .CodingSystem import CodingSystem

logger = logging.getLogger(__name__)

class OntologyTagEdge(edge_factory('OntologyTag', concrete=False)):
	"""
		OntologyTagEdge

			This class describes the parent-child relationship
			between two nodes - as defined by its `parent_id`
			and its `child_id`

	"""

	# Hidden fields
	# id = models.BigAutoField(primary_key=True)
	# child_id = models.ForeignKey(OntologyTag, on_delete=models.CASCADE, null=False)
	# parent_id = models.ForeignKey(OntologyTag, on_delete=models.CASCADE, null=False)

	class Meta:
		unique_together = ('child_id', 'parent_id',)
		indexes = [
			models.Index(fields=['child_id']),
			models.Index(fields=['parent_id']),
			models.Index(fields=['child_id', 'parent_id']),
		]



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
	## Hidden fields
	# id = models.BigAutoField(primary_key=True)

	## Top-level fields
	name = models.CharField(max_length=256, unique=False)
	type_id = models.IntegerField(choices=[(e.name, e.value) for e in constants.ONTOLOGY_TYPES])
	properties = models.JSONField(blank=True, null=True)

	## Reference to external data source(s)
	reference_id = models.IntegerField(blank=True, null=True, unique=False)

	## FTS
	search_vector = SearchVectorField(null=True)   # Weighted name / description / synonyms / relations
	synonyms_vector = SearchVectorField(null=True) # Related descriptor terms, e.g. snomed synonyms
	relation_vector = SearchVectorField(null=True) # Related object descriptors, e.g. mapped codes


	# Metadata
	class Meta:
		ordering = ('type_id', 'id', )
		indexes = [
			models.Index(fields=['id']),
			models.Index(fields=['type_id']),
			models.Index(fields=['reference_id']),
			models.Index(fields=['id', 'type_id']),
			models.Index(fields=['id', 'reference_id']),
			models.Index(fields=['id', 'type_id', 'reference_id']),
			GinIndex(name='ot_name_gin_idx', fields=['name'], opclasses=['gin_trgm_ops']),
			GinIndex(fields=['search_vector']),
			GinIndex(fields=['synonyms_vector']),
			GinIndex(fields=['relation_vector']),
			GinIndex(fields=['properties'])
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

			IMPORTANT:
			  - This interpolates values without considering sanitsation;
				  as such, this method should not be used for unsanitised
					client input

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


	# Instance methods
	def get_term(self):
		"""
			Derives the label to be presented to user(s) dependent
			on the instance type and its content _e.g._

				1. `CLINICAL_DISEASE` -> `format('%s (%s)', inst.name, inst.code)` (defaults to `name` if not present)
				2. `CLINICAL_DOMAIN` / `CLINICAL_FUNCTIONAL_ANATOMY` -> `name`

		"""
		name = self.name
		internal_type = self.type_id
		if internal_type == constants.ONTOLOGY_TYPES.CLINICAL_DISEASE:
			properties = self.properties
			reference = self.properties.get('code') if isinstance(properties, dict) else None
			if reference is not None:
				return '%(name)s (%(code)s)' % { 'name': name, 'code': reference }

		return name


	def get_reference(self):
		"""
			Derives the reference associated with this
			instance type _e.g._

				1. `CLINICAL_DISEASE` -> `code` (defaults to `reference_id` if not present)
				2. `CLINICAL_DOMAIN` / `CLINICAL_FUNCTIONAL_ANATOMY` -> `reference_id`

		"""
		internal_type = self.type_id
		if internal_type == constants.ONTOLOGY_TYPES.CLINICAL_DISEASE:
			properties = self.properties
			reference = self.properties.get('code') if isinstance(properties, dict) else None
			if reference is not None:
				return reference

		return self.reference_id


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


	# Class methods
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
		source_ids = []
		label_field = []

		if not isinstance(ontology_ids, list):
			for ont_type in constants.ONTOLOGY_TYPES:
				model_label = constants.ONTOLOGY_LABELS.get(ont_type)
				if gen_utils.is_empty_string(model_label):
					model_label = ont_type.name

				source_ids.append(ont_type.value)
				label_field.append('''when node.type_id = %s then \'%s\'''' % (ont_type.value, model_label))
		else:
			for ont_type in ontology_ids:
				model_source = None
				if isinstance(ont_type, constants.ONTOLOGY_TYPES):
					model_source = ont_type
				elif isinstance(ont_type, int) and ont_type in constants.ONTOLOGY_TYPES:
					model_source = constants.ONTOLOGY_TYPES(ont_type)

				if model_source is None or not isinstance(model_source.value, int):
					continue

				model_label = constants.ONTOLOGY_LABELS.get(model_source)
				if gen_utils.is_empty_string(model_label):
					model_label = model_source.name

				source_ids.append(model_source.value)
				label_field.append('''when node.type_id = %s then \'%s\'''' % (model_source.value, model_label))

		if len(source_ids) < 1:
			return default

		label_field = '\n'.join(label_field)
		try:
			with connection.cursor() as cursor:
				sql = f"""
				with
				  roots as (
				    select node.*
					    from public.clinicalcode_ontologytag as node
					    full outer join public.clinicalcode_ontologytagedge as edge
						    on node.id = edge.child_id
				     where edge.id is null
						   and node.type_id = any(%(source_ids)s)
				  ),
					tree as (
						select
						    node.id,
								count(case when edge.id is not null then 1 else 0 end) as child_count
						  from roots as node
						  left join public.clinicalcode_ontologytagedge as edge
							  on node.id = edge.parent_id
						 group by node.id
					)
				select
				    case
							{label_field}
					    else 'Unknown'
					  end as label,
						node.type_id as source,
				    json_agg(
					    json_build_object(
                'id', node.id,
								'label', node.name,
								'properties', node.properties,
								'isLeaf', false,
								'isRoot', true,
								'type_id', node.type_id,
								'reference_id', node.reference_id,
								'child_count', coalesce(children.child_count, 0)
					    )
				    ) as nodes
					from roots as node
					left join tree as children
					  using (id)
					where node.type_id = any(%(source_ids)s)
          group by node.type_id
				"""
				cursor.execute(
					sql,
					params={ 'source_ids': source_ids }
				)

				results = [
					{ 'model': { 'label': row[0], 'source': row[1] }, 'nodes': list(row[2]) if not isinstance(row[2], list) else row[2] }
					for row in cursor.fetchall()
				]
		except Exception as e:
			logger.error('Failed to get ontology groups of \'%s\' with err: \n\t%s' % (source_ids, str(e)))
			return default
		else:
			return results


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

		model_label = model_label if isinstance(model_label, str) and not gen_utils.is_empty_string(model_label) else None

		label_field = []
		for ont_type in constants.ONTOLOGY_TYPES:
			if ont_type.value == model_source and model_label is not None:
				label = model_label
			else:
				label = constants.ONTOLOGY_LABELS.get(ont_type, None)
				if gen_utils.is_empty_string(label):
					label = ont_type.name

			label_field.append('''when node.type_id = %s then \'%s\'''' % (ont_type.value, label))

		label_field = '\n'.join(label_field)
		try:
			with connection.cursor() as cursor:
				sql = f"""
				with
				  roots as (
				    select node.*
					    from public.clinicalcode_ontologytag as node
					    full outer join public.clinicalcode_ontologytagedge as edge
						    on node.id = edge.child_id
				     where edge.id is null
						   and node.type_id = %(source)s
				  ),
					tree as (
						select
						    node.id,
								count(case when edge.id is not null then 1 else 0 end) as child_count
						  from roots as node
						  left join public.clinicalcode_ontologytagedge as edge
							  on node.id = edge.parent_id
						 group by node.id
					)
				select
				    case
							{label_field}
					    else 'Unknown'
					  end as label,
						node.type_id as source,
				    json_agg(
					    json_build_object(
                'id', node.id,
								'label', node.name,
								'properties', node.properties,
								'isLeaf', false,
								'isRoot', true,
								'type_id', node.type_id,
								'reference_id', node.reference_id,
								'child_count', coalesce(children.child_count, 0)
					    )
				    ) as nodes
					from roots as node
					left join tree as children
					  using (id)
					where node.type_id = %(source)s
          group by node.type_id
				"""
				cursor.execute(
					sql,
					params={ 'source': model_source }
				)

				results = cursor.fetchone()
				results = { 'model': { 'label': results[0], 'source': results[1] }, 'nodes': results[2] } if results else default
		except Exception as e:
			logger.error('Failed to get ontology group data of \'%s\' with err: \n\t%s' % (model_label, str(e)))
			return default
		else:
			return results


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
							reference_id=F('reference_id'),
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
							reference_id=F('reference_id'),
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
				'reference_id': node.reference_id,
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
									'reference_id', nodes.reference_id,
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
