"""Defines a model used to assoc. failed DOI registration tasks with entities"""
from operator import itemgetter
from functools import cached_property
from django.db import models, connection
from django.db.models import Q
from django.forms.models import model_to_dict
from django.db.models.query import RawQuerySet
from django.db.models.manager import BaseManager

import math
import json
import inspect

from clinicalcode.entity_utils import gen_utils
from clinicalcode.models.GenericEntity import GenericEntity

HistoricalGenericEntity = GenericEntity.history.model

def queryset_to_array(self):
	"""Used to convert a `RawQuerySet` to a `list[Dict[Str,Any]]`"""
	return [model_to_dict(x) for x in self]

class QueuedDOI(models.Model):
	"""
	Acts as persistent storage for failed DOI registration tasks
	"""
	id = models.BigAutoField(primary_key=True)
	trg_id = models.CharField(null=False, max_length=50)
	trg_ver = models.IntegerField(null=False)
	created = models.DateTimeField(auto_now_add=True, editable=True)
	modified = models.DateTimeField(auto_now_add=True, editable=True)

	@classmethod
	def is_valid_target(cls, entity):
		"""
		Validates the given `entity` arg as a valid :model:`HistoricalGenericEntity`

		Args:
			entity (Any): some value to inspect

		Returns:
			(bool): describing whether the provided `entity` is a valid :model:`HistoricalGenericEntity`
		"""
		if entity is None or (not isinstance(entity, HistoricalGenericEntity) and not (inspect.isclass(entity) and issubclass(entity, HistoricalGenericEntity))):
			return False
		return isinstance(getattr(entity, 'id', None), str) and isinstance(getattr(entity, 'history_id', None), int)

	@classmethod
	def get_queued(cls):
		"""
		Retrieves a `List[Dict[Str, Any]]` of queued :model:`QueuedDOI` records.

		Returns:
			(List[Dict[Str,Any]]): a `list` of `dicts` describing the actively queued :model:`QueuedDOI` records
		"""
		with connection.cursor() as cursor:
			cursor.execute(
				'''
				select id, trg_id, trg_ver, created, modified
				  from public.clinicalcode_queueddoi
				 order by modified desc;
				'''
			)

			columns = [col[0] for col in cursor.description]
			return [dict(zip(columns, row)) for row in cursor.fetchall()]

	@classmethod
	def get_record(cls, entity):
		"""
		Retrieves the record assoc. with some entity

		Args:
			entity (models.Model|Dict): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]` describing the entity of interest

		Returns:
			(Model|None): the associated :model:`QueuedDOI` if found, otherwise returns a `NoneType` value
		"""
		entity = cls.resolve_entity(entity)
		if entity is None:
			return None

		entity = cls.objects.filter(Q(id=entity.get('id')) & Q(history_id=entity.get('history_id')))
		return entity.first() if entity.exists() else None

	@classmethod
	def get_records(cls, *args):
		"""
		Retrieves a `RawQuerySet` of :model:`QueuedDOI` records _assoc._ with the provided entities

		Note:
			- An additional method has been appended to the `RawQuerySet` to enable serialisation, call `.to_array()` to convert the RawQuerySet to a list of dictified model(s)

		Args:
			*args: Variadic args describing either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]`

		Returns:
			(RawQuerySet): a `RawQuerySet` of :model:`QueuedDOI`s
		"""
		targets, _ = cls.resolve_targets(*args)
		if len(targets) < 1:
			query = BaseManager(cls).from_queryset(RawQuerySet).none()
		else:
			query = QueuedDOI.objects.raw(
				'''
				select qdoi.*
					from public.clinicalcode_queueddoi as qdoi
					join (
						select *
							from jsonb_to_recordset(%(targets)s::jsonb) as t(
								id           varchar(256),
								history_id   integer
							)
					) as trg
						on qdoi.trg_id = trg.id and qdoi.trg_ver = trg.history_id
				''',
				params={ 'targets': json.dumps(targets) }
			)

		query.to_array = queryset_to_array.__get__(query)
		return query

	@classmethod
	def register(cls, *args, **kwargs):
		"""
		Inserts or updates records of one or more entities to register the failure to create its respective DOI

		Args:
			*args: Variadic args describing either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]`

		Kwargs:
			bubble_errors (bool): defaults to `False`, optionally specify whether to bubble errors after attempting to record the failures of the successfully resolved entities

		Returns:
			(Dict):
				- "rows": An (int) describing the number of affected rows;
				- "errors": Either (a) a `NoneType` value if no errors were captured or (b) `Dict[int,Error]` describing errors assoc. with each arg index.

		Raises:
			ValueError: If `bubble_errors` is not specified then if one or more invalid entities were passed or if no entity could be derived from the provided arguments.
		"""
		targets, errors = cls.resolve_targets(*args)

		trg_len = len(targets)
		bubble_errors = kwargs.get('bubble_errors', False)

		if isinstance(errors, dict) and not bubble_errors:
			raise ValueError(
				'Errors encountered when registering DOI failures:\n' + '\n'.join(['  - ' + x for x in errors.values()])
			)

		if trg_len < 1:
			if not bubble_errors:
				raise ValueError('Invalid args, expected at least one valid reference to a HistoricalGenericEntity')
			return { 'rows': 0, 'errors': errors }

		with connection.cursor() as cursor:
			cursor.execute(
				'''
				insert into public.clinicalcode_queueddoi(
					trg_id,
					trg_ver,
					created,
					modified
				)
				select
						id as trg_id,
						history_id as trg_ver,
						now() as created,
						now() as modified
					from jsonb_to_recordset(%(targets)s::jsonb) as t(
						id           varchar(256),
						history_id   integer
					)
				on conflict(trg_id, trg_ver)
				  do update
				        set modified = now();
				''',
				params={ 'targets': json.dumps(targets) }
			)

			return { 'rows': cursor.rowcount, 'errors': errors }

	@classmethod
	def unregister(cls, *args, **kwargs):
		"""
		Deletes the records associated with one or more entities registered as having previously failed to create its respective DOI

		Args:
			*args: Variadic args describing either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]`

		Kwargs:
			bubble_errors (bool): defaults to `False`, optionally specify whether to bubble errors after attempting to record the failures of the successfully resolved entities

		Returns:
			(Dict):
				- "rows": An (int) describing the number of affected rows;
				- "errors": Either (a) a `NoneType` value if no errors were captured or (b) `Dict[int,Error]` describing errors assoc. with each arg index.

		Raises:
			ValueError: If `bubble_errors` is not specified then if one or more invalid entities were passed or if no entity could be derived from the provided arguments.
		"""
		targets, errors = cls.resolve_targets(*args)

		trg_len = len(targets)
		bubble_errors = kwargs.get('bubble_errors', False)

		if isinstance(errors, dict) and not bubble_errors:
			raise ValueError(
				'Errors encountered when unregistering DOI failure records:\n' + '\n'.join(['- ' + x for x in errors.values()])
			)

		if trg_len < 1:
			if not bubble_errors:
				raise ValueError('Invalid args, expected at least one valid reference to a HistoricalGenericEntity')
			return { 'rows': 0, 'errors': errors }

		with connection.cursor() as cursor:
			cursor.execute(
				'''
				with
					targets as (
						select *
							from jsonb_to_recordset(%(targets)s::jsonb) as t(
								id           varchar(256),
								history_id   integer
							)
					)
				delete from public.clinicalcode_queueddoi as qdoi
				 where exists (
				   select 1
					   from targets as trg
					  where qdoi.trg_id = trg.id and qdoi.trg_ver = trg.history_id
				 );
				''',
				params={ 'targets': json.dumps(targets) }
			)

			return { 'rows': cursor.rowcount, 'errors': errors }

	@classmethod
	def resolve_entity(cls, entity):
		"""
		Retrieves the :model:`HistoricalGenericEntity` assoc. with the given args if applicable

		Args:
			entity (Any): either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]`

		Returns:
			(HistoricalGenericEntity|None): a :model:`HistoricalGenericEntity` if a target entity can be resolved from the provided args; otherwise returns (None)
		"""
		if isinstance(entity, dict):
			ent_id = entity.get('id', None)
			ent_ver = entity.get('history_id', None)

			ent_id = ent_id if isinstance(ent_id, str) and not gen_utils.is_empty_string(ent_id) else None
			ent_ver = gen_utils.parse_int(ent_ver)
			ent_ver = ent_ver if isinstance(ent_ver, int) and math.isfinite(ent_ver) and not math.isnan(ent_ver) else None

			if ent_id is not None and ent_ver is not None:
				entity = GenericEntity.history.filter(id=ent_id, history_id=ent_ver).latest_of_each()
				entity = entity.first() if entity.exists() else None

		return entity if cls.is_valid_target(entity) else None

	@classmethod
	def resolve_targets(cls, *args):
		"""
		Validates and resolves a set of targets assoc. with one or more :model:`HistoricalGenericEntity` args

		Args:
			*args: Variadic args describing either (a) a :model:`HistoricalGenericEntity` or (b) a `Dict[{'id': str, 'history_id': int}]`

		Returns:
			(tuple):
				1. A `list` of `Dict[{'id': str, 'history_id': int}]`s describing the resolved entities;
				2. Either (a) a `NoneType` value if no errors were captured or (b) `Dict[int,Error]` describing errors assoc. with each arg index.
		"""
		seen = set()
		resolved = []

		errors = None
		queryable = None
		for i, entity in enumerate(args):
			if cls.is_valid_target(entity):
				ref = '%s/%d' % (entity.id, entity.history_id,)
				if ref in seen:
					continue

				seen.add(ref)
				resolved.append({
					'id': entity.id,
					'history_id': entity.history_id,
				})
			elif isinstance(entity, dict):
				ent_id = entity.get('id', None)
				ent_ver = entity.get('history_id', None)

				entity_id = ent_id if isinstance(ent_id, str) and not gen_utils.is_empty_string(ent_id) else None
				entity_ver = gen_utils.parse_int(ent_ver)
				entity_ver = ent_ver if isinstance(entity_ver, int) and math.isfinite(entity_ver) and not math.isnan(entity_ver) else None

				if entity_id is None or entity_ver is None:
					if not isinstance(errors, dict):
						errors = {}

					errors.update({
						i: (
							'TypeError: Arg<index: %d> of type `%s` is invalid, expected `id`:`str` and `history_id`:`int` but got [%s,%s]' % (
								i,
								type(entity).__name__,
								str(ent_id),
								str(ent_ver),
							)
						)
					})
					continue

				ref = '%s/%d' % (entity_id, entity_ver,)
				if ref in seen:
					continue

				if not isinstance(queryable, list):
					queryable = []

				seen.add(ref)
				queryable.append({
					'id': entity_id,
					'history_id': entity_ver,
					'queryable_id': i,
				})
			else:
				if not isinstance(errors, dict):
					errors = {}

				errors.update({
					i: (
						'TypeError: Arg<index: %d> is invalid, expected `HistoricalGenericEntity` or `Dict[{\'id\': str, \'history_id\': int}]` but got type `%s`' % (
							i,
							type(entity).__name__
						)
					)
				})

		if isinstance(queryable, list):
			with connection.cursor() as cursor:
				cursor.execute(
					'''
				  select trg.queryable_id, hge.id, hge.history_id
				    from public.clinicalcode_historicalgenericentity as hge
				    join (
				      select *
				        from jsonb_to_recordset(%(query)s::jsonb) as t (
				          id           varchar(256),
				          history_id   integer,
								  queryable_id integer
				        )
				    ) as trg
						  on trg.id = hge.id and trg.history_id = hge.history_id;
					''',
					params={ 'query': json.dumps(queryable) }
				)

				columns = [col[0] for col in cursor.description]
				results = [dict(zip(columns, row)) for row in cursor.fetchall()]
				nresult = len(results)
				if nresult != len(queryable):
					diff = {x.get('queryable_id') for x in results}.symmetric_difference(map(itemgetter('queryable_id'), queryable))
					diff = {
						qid: (
							'LookupError: Arg<index: %d> of type `%s`, failed to resolve HistoricEntity<id: %s, history_id: %s>' % (
								qid,
								type(args[qid]).__name__,
								str(args[qid].get('id')),
								str(args[qid].get('history_id')),
							)
						)
						for qid in diff
					}

					errors = diff if not isinstance(errors, dict) else (errors | diff)

				if nresult > 0:
					resolved += [{ 'id': x.get('id'), 'history_id': x.get('history_id') } for x in results]

		return resolved, errors

	@cached_property
	def entity(self):
		"""Retrieves the :model:`GenericEntity` associated with this instance's record"""
		obj = GenericEntity.objects.filter(id=self.trg_id)
		return obj.first() if obj.exists() else None

	@cached_property
	def historical_entity(self):
		"""Retrieves the :model:`HistoricalGenericEntity` associated with this instance's record"""
		obj = GenericEntity.history.filter(id=self.trg_id, history_id=self.trg_ver)
		return obj.first() if obj.exists() else None

	class Meta:
		ordering = ('-created',)
		unique_together = ('trg_id', 'trg_ver',)
		indexes = [
			models.Index(fields=['id']),
			models.Index(fields=['trg_id']),
			models.Index(fields=['trg_ver']),
			models.Index(fields=['modified']),
			models.Index(fields=['trg_id', 'trg_ver']),
			models.Index(fields=['trg_id', 'trg_ver', 'modified']),
		]

	def __str__(self):
		"""Debug str"""
		return 'QueuedDOI<trg: %s/%d>' % (self.trg_id, self.trg_ver)
