from django.db import models, connection
from django.db.models import F, Count, Case, When, Exists, OuterRef
from django.db.models.functions import JSONObject
from django.contrib.postgres import indexes as Indexes
from django.contrib.postgres.search import SearchVectorField
from django_postgresql_dag.models import node_factory, edge_factory

import logging
import psycopg2

from ..entity_utils import gen_utils
from ..entity_utils import constants

logger = logging.getLogger(__name__)

"""
	Default const. value specifying the minimum amount of characters required before a typeahead request will be queried
"""
TYPEAHEAD_MIN_CHARS = 3

"""
	Default const. value specifying the maximum number of results to return in a typeahead query
"""
TYPEAHEAD_MAX_RESULTS = 20

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
			# Hash indices
			Indexes.HashIndex(fields=['id'], name='oe_hh_id_idx'),
			Indexes.HashIndex(fields=['child_id'], name='oe_hh_chid_idx'),
			Indexes.HashIndex(fields=['parent_id'], name='oe_hh_prid_idx'),
			# Composite indices
			Indexes.BTreeIndex(fields=['child_id', 'parent_id'], name='oe_cpbt_chpr_idx'),
			# Covering indices
			models.Index(fields=['child_id'], include=['id', 'parent_id'], name='oe_cv_ch_idx'),
			models.Index(fields=['parent_id'], include=['id', 'child_id'], name='oe_cv_pr_idx'),
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
	reference_id = models.CharField(max_length=64, unique=False, default='')
	properties = models.JSONField(blank=True, null=True)

	## FTS
	search_vector = SearchVectorField(null=True)   # Weighted name / description / synonyms / relations
	synonyms_vector = SearchVectorField(null=True) # Related descriptor terms, e.g. snomed synonyms
	relation_vector = SearchVectorField(null=True) # Related object descriptors, e.g. mapped codes


	# Metadata
	class Meta:
		ordering = ('type_id', 'id',)
		unique_together = ('type_id', 'reference_id',)
		indexes = [
			# Hash & BTree indices
			Indexes.HashIndex(fields=['id'], name='ot_hh_id_idx'),
			Indexes.HashIndex(fields=['type_id'], name='ot_bt_tp_idx'),
			Indexes.BTreeIndex(fields=['reference_id'], name='ot_bt_ref_idx'),
			# jsonb indices
			Indexes.GinIndex(
				Indexes.OpClass(F('properties__xrefs'), name='jsonb_path_ops'),
				name='ot_gin_jref_idx'
			),
			Indexes.GinIndex(
				Indexes.OpClass(F('properties__synonyms'), name='jsonb_path_ops'),
				name='ot_gin_jsyn_idx'
			),
			Indexes.GinIndex(
				Indexes.OpClass(F('properties__categories'), name='jsonb_path_ops'),
				name='ot_gin_jcat_idx'
			),
			Indexes.GinIndex(
				Indexes.OpClass(F('properties__definition'), name='jsonb_path_ops'),
				name='ot_gin_jdef_idx'
			),
			# tsvector indices
			Indexes.GinIndex(fields=['search_vector'], name='ot_gin_srch_idx'),
			Indexes.GinIndex(fields=['synonyms_vector'], name='ot_gin_syns_idx'),
			Indexes.GinIndex(fields=['relation_vector'], name='ot_gin_rels_idx'),
			# Composite indices
			Indexes.BTreeIndex(fields=['type_id', 'reference_id'], name='ot_cpbt_tr_idx'),
			# Covering indices
			models.Index(
				fields=['id'],
				include=['name', 'type_id', 'reference_id'],
				name='ot_cv_id_idx'
			),
			models.Index(
				fields=['type_id'],
				include=['id', 'name', 'reference_id'],
				name='ot_cv_tid_idx'
			),
			models.Index(
				fields=['reference_id'],
				include=['id', 'name', 'type_id'],
				name='ot_cv_ref_idx'
			),
			models.Index(
				fields=['type_id', 'reference_id'],
				include=['id', 'name'],
				name='ot_cv_tr_idx'
			),
		]


	# Dunder methods
	def __str__(self):
		return self.name


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
			for ont_type in constants.ONTOLOGY_ACTIVE:
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

				if model_source.value not in constants.ONTOLOGY_ACTIVE:
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
								'type_id', node.type_id,
								'reference_id', node.reference_id,
								'properties', node.properties,
								'isLeaf', false,
								'isRoot', true,
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
	def get_group_data(cls, ont_type, model_label=None, default=None):
		"""
			Derives the tree model data given the model source name

			Args:
				ont_type    (int|enum): the ontology id

				model_label (str|None): the associated model label

				default     (any|None): the default return value

			Returns:
				Either (a) the default value if none are found,
					or (b) a dict containing the associated tree model data
		"""
		model_source = None
		if isinstance(ont_type, constants.ONTOLOGY_TYPES):
			model_source = ont_type
		elif isinstance(ont_type, int) and ont_type in constants.ONTOLOGY_TYPES:
			model_source = constants.ONTOLOGY_TYPES(ont_type)

		if model_source is None or not isinstance(model_source.value, int) or model_source.value not in constants.ONTOLOGY_ACTIVE:
			return default

		model_label = model_label if isinstance(model_label, str) and not gen_utils.is_empty_string(model_label) else None
		model_source = model_source.value

		label_field = []
		for ont in constants.ONTOLOGY_TYPES:
			if ont.value == model_source and model_label is not None:
				label = model_label
			else:
				label = constants.ONTOLOGY_LABELS.get(ont, None)
				if gen_utils.is_empty_string(label):
					label = ont.name

			label_field.append('''when node.type_id = %s then \'%s\'''' % (ont.value, label))

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
								'type_id', node.type_id,
								'reference_id', node.reference_id,
								'properties', node.properties,
								'isLeaf', false,
								'isRoot', true,
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
		if not isinstance(node_id, int):
			return default

		if isinstance(ontology_id, constants.ONTOLOGY_TYPES):
			model_source = ontology_id
		elif isinstance(ontology_id, int) and ontology_id in constants.ONTOLOGY_TYPES:
			model_source = constants.ONTOLOGY_TYPES(ontology_id)
		else:
			model_source = None

		with connection.cursor() as cursor:
			try:
				label_cases = None
				if not isinstance(model_source, constants.ONTOLOGY_TYPES):
					model_id = -1
					model_label = 'Unknown'

					label_cases = psycopg2.sql.SQL('case')
					for x in constants.ONTOLOGY_LABELS:
						label_cases += psycopg2.sql.SQL('''\nwhen sel.type_id = {value} then {label}''') \
								.format(
									value=psycopg2.sql.Literal(x.value),
									label=psycopg2.sql.Literal(constants.ONTOLOGY_LABELS[x] if x in constants.ONTOLOGY_LABELS else x.name),
								)

					label_cases += psycopg2.sql.SQL('''\nelse 'Unknown'\n end\n''')
				else:
					model_id = model_source.value

					if not isinstance(model_label, str) or gen_utils.is_empty_string(model_label):
						model_label = constants.ONTOLOGY_LABELS.get(model_source, None)
						if model_label is None:
							model_label = model_source.name

					label_cases = psycopg2.sql.Literal(model_label)

				sql = psycopg2.sql.SQL('''
				with
					recursive ancestry(parent_id, child_id, trg, depth, path) as (
						select
									n0.parent_id,
									n0.child_id,
									n0.child_id as trg,
									1 as depth,
									array[n0.parent_id, n0.child_id] as path
							from public.clinicalcode_ontologytagedge as n0
							left outer join public.clinicalcode_ontologytagedge as n1
								on n0.parent_id = n1.child_id
						 where n0.child_id = %(node_id)s
						union
						select
									n2.parent_id,
									ancestry.child_id,
									ancestry.trg,
									ancestry.depth + 1 as depth,
									n2.parent_id || ancestry.path
							from ancestry
							join public.clinicalcode_ontologytagedge as n2
								on n2.child_id = ancestry.parent_id
					),
					selected as (
						select *
							from public.clinicalcode_ontologytag as node
						 where node.id = %(node_id)s
						 limit 1
					),
					root_path as (
						select path.*
							from ancestry as path
							join (
								select
											trg,
											min(depth) as depth
									from ancestry
								 group by trg
							) as roots
								on (roots.depth = path.depth and roots.trg = path.trg)
					),
					root_nodes as (
						select
									sel.id,
									json_agg(
										jsonb_build_object(
											'id', node.id,
											'label', node.name
										)
										order by node.id asc
									) as tree
							from selected as sel
							join root_path as path
								on path.trg = sel.id
							join public.clinicalcode_ontologytag as node
								on node.id = path.parent_id
						 group by sel.id
					),
					child_nodes as (
						select
									c0.id,
									count(*) as cnt,
									json_agg(c0.tree) as tree
							from (
								select
											obj.id as id,
											jsonb_build_object(
												'id', n0.id,
												'label', n0.name,
												'type_id', n0.type_id,
												'reference_id', n0.reference_id,
												'properties', n0.properties,
												'isRoot', false,
												'isLeaf', case when count(t1.child_id) < 1 then true else false end,
												'child_count', count(t1.child_id),
												'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
											) as tree
									from selected as obj
									join public.clinicalcode_ontologytagedge as e0
										on obj.id = e0.parent_id
									join public.clinicalcode_ontologytag as n0
										on e0.child_id = n0.id
									left outer join public.clinicalcode_ontologytagedge as t0
										on n0.id = t0.child_id
									left outer join public.clinicalcode_ontologytagedge as t1
										on n0.id = t1.parent_id
								 group by obj.id, n0.id
							) as c0
						 group by c0.id
					),
					parent_nodes as (
						select
									c0.id,
									count(*) as cnt,
									json_agg(c0.tree) as tree
							from (
								select
										obj.id as id,
										jsonb_build_object(
											'id', n0.id,
											'label', n0.name,
											'type_id', n0.type_id,
											'reference_id', n0.reference_id,
											'properties', n0.properties,
											'isRoot', case when count(t0.parent_id) < 1 then true else false end,
											'isLeaf', case when count(t1.child_id) < 1 then true else false end,
											'child_count', count(t1.child_id),
											'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
										) as tree
								from selected as obj
								join public.clinicalcode_ontologytagedge as e0
									on obj.id = e0.child_id
								join public.clinicalcode_ontologytag as n0
									on e0.parent_id = n0.id
								left outer join public.clinicalcode_ontologytagedge t0
									on n0.id = t0.child_id
								left outer join public.clinicalcode_ontologytagedge t1
									on n0.id = t1.parent_id
							 group by obj.id, n0.id
							) as c0
						 group by c0.id
					)
				select
							json_build_object(
								'id', sel.id,
								'label', sel.name,
								'model', (
									case
										when sel.type_id = {model_source} then
											json_build_object(
												'label', {model_label},
												'source', {model_source}
											)
										else
											json_build_object(
												'label', ({label_cases}),
												'source', sel.type_id
											)
									end
								),
								'type_id', sel.type_id,
								'reference_id', sel.reference_id,
								'properties', sel.properties,
								'isLeaf', case when coalesce(children.cnt, 0) < 1 then True else False end,
								'isRoot', case when parents.id is NULL then True else False end,
								'child_count', coalesce(children.cnt, 0),
								'parents', coalesce(parents.tree, '[]'::json),
								'children', coalesce(children.tree, '[]'::json),
								'roots', coalesce(roots.tree, '[]'::json)
							) as tree
					from selected as sel
					left outer join parent_nodes as parents
						using (id)
					left outer join child_nodes as children
						using (id)
					left outer join root_nodes as roots
						using (id)
				''') \
					.format(
						model_label=psycopg2.sql.Literal(model_label),
						model_source=psycopg2.sql.Literal(model_id),
						label_cases=label_cases
					)

				cursor.execute(sql, params={ 'node_id': node_id })

				columns = [col[0] for col in cursor.description]
				results = [dict(zip(columns, row)) for row in cursor.fetchall()]
				return results[0].get('tree') if len(results) > 0 and results[0].get('tree') is not None else default
			except:
				return default


	@classmethod
	def get_node_resultset(cls, node_ids, default=None):
		"""
			Computes an array of objects describing the nodes matched by the specified node_ids

			Args:
				node_ids (int|str|list): the node id(s); this could be one or more node ids

				default (any|None): the default return value

			Returns:
				Either (a) the default value if none are found,
					  or (b) a list of objects containing the node data
		"""
		node_ids = gen_utils.try_value_as_type(node_ids, 'int_array', loose_coercion=True, strict_elements=False, default=None)
		if not isinstance(node_ids, list) or len(node_ids) < 1:
			return default

		with connection.cursor() as cursor:
			try:
				label_cases = psycopg2.sql.SQL('case')
				for x in constants.ONTOLOGY_LABELS:
					label_cases += psycopg2.sql.SQL('''\nwhen sel.type_id = {value} then {label}''') \
							.format(
								value=psycopg2.sql.Literal(x.value),
								label=psycopg2.sql.Literal(constants.ONTOLOGY_LABELS[x] if x in constants.ONTOLOGY_LABELS else x.name),
							)

				label_cases += psycopg2.sql.SQL('''\nelse 'Unknown'\n end\n''')

				sql = psycopg2.sql.SQL('''
				with
					recursive ancestry(parent_id, child_id, trg, depth, path) as (
						select
									n0.parent_id,
									n0.child_id,
									n0.child_id as trg,
									1 as depth,
									array[n0.parent_id, n0.child_id] as path
							from public.clinicalcode_ontologytagedge as n0
							left outer join public.clinicalcode_ontologytagedge as n1
								on n0.parent_id = n1.child_id
						 where n0.child_id = any(%(node_ids)s)
						union
						select
									n2.parent_id,
									ancestry.child_id,
									ancestry.trg,
									ancestry.depth + 1 as depth,
									n2.parent_id || ancestry.path
							from ancestry
							join public.clinicalcode_ontologytagedge as n2
								on n2.child_id = ancestry.parent_id
					),
					selected as (
						select *
							from public.clinicalcode_ontologytag as node
						 where node.id = any(%(node_ids)s)
					),
					root_path as (
						select path.*
							from ancestry as path
							join (
								select
											trg,
											min(depth) as depth
									from ancestry
								 group by trg
							) as roots
								on (roots.depth = path.depth and roots.trg = path.trg)
					),
					root_nodes as (
						select
									sel.id,
									json_agg(
										jsonb_build_object(
											'id', node.id,
											'label', node.name
										)
										order by node.id asc
									) as tree
							from selected as sel
							join root_path as path
								on path.trg = sel.id
							join public.clinicalcode_ontologytag as node
								on node.id = path.parent_id
						 group by sel.id
					),
					child_nodes as (
						select
									c0.id,
									count(*) as cnt,
									json_agg(c0.tree) as tree
							from (
								select
											obj.id as id,
											jsonb_build_object(
												'id', n0.id,
												'label', n0.name,
												'type_id', n0.type_id,
												'reference_id', n0.reference_id,
												'properties', n0.properties,
												'isRoot', false,
												'isLeaf', case when count(t1.child_id) < 1 then true else false end,
												'child_count', count(t1.child_id),
												'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
											) as tree
									from selected as obj
									join public.clinicalcode_ontologytagedge as e0
										on obj.id = e0.parent_id
									join public.clinicalcode_ontologytag as n0
										on e0.child_id = n0.id
									left outer join public.clinicalcode_ontologytagedge as t0
										on n0.id = t0.child_id
									left outer join public.clinicalcode_ontologytagedge as t1
										on n0.id = t1.parent_id
								 group by obj.id, n0.id
							) as c0
						 group by c0.id
					),
					parent_nodes as (
						select
									c0.id,
									count(*) as cnt,
									json_agg(c0.tree) as tree
							from (
								select
										obj.id as id,
										jsonb_build_object(
											'id', n0.id,
											'label', n0.name,
											'type_id', n0.type_id,
											'reference_id', n0.reference_id,
											'properties', n0.properties,
											'isRoot', case when count(t0.parent_id) < 1 then true else false end,
											'isLeaf', case when count(t1.child_id) < 1 then true else false end,
											'child_count', count(t1.child_id),
											'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
										) as tree
								from selected as obj
								join public.clinicalcode_ontologytagedge as e0
									on obj.id = e0.child_id
								join public.clinicalcode_ontologytag as n0
									on e0.parent_id = n0.id
								left outer join public.clinicalcode_ontologytagedge t0
									on n0.id = t0.child_id
								left outer join public.clinicalcode_ontologytagedge t1
									on n0.id = t1.parent_id
							 group by obj.id, n0.id
							) as c0
						 group by c0.id
					)
				select
							json_build_object(
								'id', sel.id,
								'label', sel.name,
								'model', json_build_object(
									'label', ({label_cases}),
									'source', sel.type_id
								),
								'type_id', sel.type_id,
								'reference_id', sel.reference_id,
								'properties', sel.properties,
								'isLeaf', case when coalesce(children.cnt, 0) < 1 then True else False end,
								'isRoot', case when parents.id is NULL then True else False end,
								'child_count', coalesce(children.cnt, 0),
								'parents', coalesce(parents.tree, '[]'::json),
								'children', coalesce(children.tree, '[]'::json),
								'roots', coalesce(roots.tree, '[]'::json)
							) as tree
					from selected as sel
					left outer join parent_nodes as parents
						using (id)
					left outer join child_nodes as children
						using (id)
					left outer join root_nodes as roots
						using (id)
				''') \
					.format(
						label_cases=label_cases
					)

				cursor.execute(sql, params={ 'node_ids': node_ids })

				results = cursor.fetchall()
				results = [row[0] for row in results if isinstance(row, (list, tuple,)) and len(row) > 0]
				return results
			except Exception as e:
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
				Either:
					1. On failure: the default value if we're unable to resolve the data,
					2. On success: a list of dicts containing the associated node's data and its ancestry data

		"""
		descendant_ids = gen_utils.try_value_as_type(
			descendant_ids,
			'int_array',
			loose_coercion=True,
			strict_elements=False,
			default=None
		)

		if descendant_ids is None:
			return default

		ancestry = default
		try:
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
						 where n0.child_id = any(%(node_ids)s)
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
					objects as (
						select
									selected.child_id,
									nodes.id as nodes_id,
									jsonb_build_object(
										'id', nodes.id,
										'idx', selected.idx,
										'label', nodes.name,
										'type_id', nodes.type_id,
										'reference_id', nodes.reference_id,
										'properties', nodes.properties,
										'isLeaf', case when count(edges1.child_id) < 1 then True else False end,
										'isRoot', case when max(edges0.parent_id) is NULL then True else False end,
										'child_count', count(edges1.child_id)
									) as tree
						  from (
								select
										id,
										child_id,
										idx
									from
											ancestors,
											unnest(path) with ordinality as ids(id, idx)
								 group by id, child_id, idx
							) as selected
						  join public.clinicalcode_ontologytag as nodes
							  on nodes.id = selected.id
						  left outer join public.clinicalcode_ontologytagedge as edges0
							  on nodes.id = edges0.child_id
						  left outer join public.clinicalcode_ontologytagedge as edges1
							  on nodes.id = edges1.parent_id
						 group by selected.child_id, nodes.id, selected.idx
					),
					recur as (
						select
									obj.child_id,
									obj.tree || jsonb_build_object(
										'children', coalesce(children.tree, '[]'::json),
										'parents', coalesce(parents.tree, '[]'::json)
									) as tree
							from objects as obj
						  left outer join (
								select c0.id, json_agg(c0.tree) as tree
								  from (
										select
													sel.nodes_id as id,
													jsonb_build_object(
														'id', n0.id,
														'label', n0.name,
														'type_id', n0.type_id,
														'reference_id', n0.reference_id,
														'properties', n0.properties,
														'isRoot', false,
														'isLeaf', case when count(t1.child_id) < 1 then true else false end,
														'child_count', count(t1.child_id),
														'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
													) as tree
										from objects as sel
										join public.clinicalcode_ontologytagedge as e0
											on sel.nodes_id = e0.parent_id
										join public.clinicalcode_ontologytag as n0
											on e0.child_id = n0.id
										left outer join public.clinicalcode_ontologytagedge as t0
											on n0.id = t0.child_id
										left outer join public.clinicalcode_ontologytagedge as t1
											on n0.id = t1.parent_id
										group by sel.nodes_id, n0.id
								  ) as c0
								 group by c0.id
							) as children
							  on children.id = obj.nodes_id
						  left outer join (
								select c0.id, json_agg(c0.tree) as tree
								  from (
										select
													sel.nodes_id as id,
													jsonb_build_object(
														'id', n0.id,
														'label', n0.name,
														'type_id', n0.type_id,
														'reference_id', n0.reference_id,
														'properties', n0.properties,
														'isRoot', case when count(t0.parent_id) < 1 then true else false end,
														'isLeaf', case when count(t1.child_id) < 1 then true else false end,
														'child_count', count(t1.child_id),
														'parents', coalesce(array_agg(distinct t0.parent_id) filter (where t0.parent_id is not null), array[]::bigint[])
													) as tree
										from objects as sel
										join public.clinicalcode_ontologytagedge as e0
											on sel.nodes_id = e0.child_id
										join public.clinicalcode_ontologytag as n0
											on e0.parent_id = n0.id
										left outer join public.clinicalcode_ontologytagedge as t0
											on n0.id = t0.child_id
										left outer join public.clinicalcode_ontologytagedge as t1
											on n0.id = t1.parent_id
										group by sel.nodes_id, n0.id
								  ) as c0
								 group by c0.id
							) as parents
							  on parents.id = obj.nodes_id
					)
				select
							ancestor.child_id,
							ancestor.path,
							json_agg(obj.tree order by obj.tree->>'idx') as dataset
				  from ancestors as ancestor
				  join recur as obj
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
					type_id=F('type_id'),
					reference_id=F('reference_id'),
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
					isLeaf=Case(
						When(child_count__lt=1, then=True),
						default=False
					),
				)
			) \
			.values_list('tree_dataset', flat=True)

		return [
			node | { 'full_names': roots.get(node.get('id')) }
			if not node.get('isRoot') and roots.get(node.get('id')) else node
			for node in nodes
		]


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
		node_ids = gen_utils.try_value_as_type(node_ids, 'int_array', loose_coercion=True, strict_elements=False, default=None)
		type_ids = gen_utils.try_value_as_type(type_ids, 'int_array', loose_coercion=True, strict_elements=False, default=None)

		if (node_ids is None or len(node_ids) < 1) or (type_ids and len(type_ids) < 1):
			return default

		nodes = OntologyTag.get_node_resultset(node_ids, default=[])
		ancestors = []

		tree = cls.build_tree(node_ids, default=None)
		if tree:
			for node in nodes:
				if len(node.get('children', [])) + len(node.get('parents', [])) < 1:
					continue

				obj = next((x for x in tree if x.get('child_id') == node.get('id')), None)
				if obj is not None and isinstance(obj.get('dataset'), list):
					ancestors.append(obj.get('dataset'))

		return {
			'ancestors': ancestors,
			'value': nodes,
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
		node_ids = gen_utils.try_value_as_type(node_ids, 'int_array', loose_coercion=True, strict_elements=False, default=None)
		type_ids = gen_utils.try_value_as_type(type_ids, 'int_array', loose_coercion=True, strict_elements=False, default=None)

		if (node_ids is None or len(node_ids) < 1) or (type_ids is None or len(type_ids) < 1):
			return default

		nodes = OntologyTag.objects.filter(id__in=node_ids, type_id__in=type_ids)
		if nodes.count() < 1:
			return default

		return list(nodes.annotate(value=F('id')).values('name', 'value', 'reference_id'))


	@classmethod
	def query_typeahead(cls, searchterm = '', type_ids=None, result_limit = TYPEAHEAD_MAX_RESULTS):
		"""
			Autocomplete, typeahead-like web search for Ontology search components

			Note:
				The searchterm must satisfy the `TYPEAHEAD_MIN_CHARS` size (gte 3) to return results

			Args:
				searchterm (str): some web query search term; defaults to an empty `str`

				type_ids (int|str|int[]): optionally narrow the resultset by specifying the ontology type ids; defaults to `None`

				result_limit (int): maximum number of results to return per request; defaults to `TYPEAHEAD_MAX_RESULTS`

			Returns:
				An array, ordered by search rank, listing each of the matching ontological terms

		"""
		if not isinstance(searchterm, str) or gen_utils.is_empty_string(searchterm) or len(searchterm) < TYPEAHEAD_MIN_CHARS:
			return []

		type_ids = gen_utils.try_value_as_type(type_ids, 'int_array', loose_coercion=True, strict_elements=False, default=[])
		with connection.cursor() as cursor:
			sql = psycopg2.sql.SQL('''
			with
				matches as (
					select
								node.id,
								node.name,
								node.type_id,
								node.reference_id,
								node.properties,
								ts_rank_cd(node.search_vector, plainto_tsquery('public.ontology_en', trim(%(searchterm)s)) as score
						from public.clinicalcode_ontologytag as node
					 where ((
								search_vector
								@@ plainto_tsquery('public.ontology_en', trim(%(searchterm)s))
						  )
							 or (
								(relation_vector @@ plainto_tsquery('public.ontology_en', trim(%(searchterm)s)))
								or (synonyms_vector @@ plainto_tsquery('public.ontology_en', trim(%(searchterm)s)))
						  )
					   )
			''')

			if len(type_ids) > 0:
				sql = sql + psycopg2.sql.SQL('''and node.type_id = any(%(type_ids)s::int[])''')

			sql = sql + psycopg2.sql.SQL('''		
					 group by node.id
					 limit {lim_size}
				)
			select json_agg(
							jsonb_build_object(
								'id', node.id,
								'label', node.name,
								'type_id', node.type_id,
								'reference_id', node.reference_id,
								'properties', coalesce(node.properties, jsonb_build_object())
							)
							order by node.score desc
						) as agg
				from matches as node
			''') \
				.format(
					lim_size=psycopg2.sql.Literal(result_limit)
				)

			cursor.execute(sql, params={
				'type_ids': type_ids,
				'searchterm': searchterm,
			})

			columns = [col[0] for col in cursor.description]
			results = [dict(zip(columns, row)) for row in cursor.fetchall()]
			return results[0].get('agg') if len(results) > 0 and isinstance(results[0].get('agg'), list) else []
