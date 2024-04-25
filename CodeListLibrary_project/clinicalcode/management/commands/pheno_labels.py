from django.core.management.base import BaseCommand
from django.db import transaction, connection

import os
import csv
import json
import time

from .constants import LogType

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

class Command(BaseCommand):
    help = 'Various tasks associated with phenotype labeling'

    def __get_log_style(self, style):
        """
            Returns the BaseCommand's log style

            See ref @ https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/#django.core.management.BaseCommand.style
        """
        if isinstance(style, str):
            style = style.upper()
            if style in LogType.__members__:
                return getattr(self.style, style)
        elif isinstance(style, LogType):
            if style.name in LogType.__members__:
                return getattr(self.style, style.name)
        return self.style.SUCCESS

    def __log(self, message, style=LogType.SUCCESS):
        """
            Logs the incoming to the terminal if
            the verbose argument is present
        """
        if not self._verbose:
            return
        style = self.__get_log_style(style)
        self.stdout.write(style(message))

    def __record_execution_time(self, title=None):
        title = f'[{title}] ' if isinstance(title, str) else ''
        start = time.time()

        def finalise(suffix=None):
            elapsed = (time.time() - start) * 1000
            suffix = f' | {suffix}' if isinstance(suffix, str) else ''
            self.__log(f'{title}Execution Time: {elapsed:.2f} ms{suffix}')
        return finalise

    def __try_label_readcodes(self):
        fp = os.path.join(os.path.abspath(os.path.dirname('manage.py')), 'data/READ_ICD10_MAPPING.csv')
        
        recorder = self.__record_execution_time('MappingReader')
        with open(fp, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            system_mapping = [
                { 'read': row.get('READ_CODE'), 'icd': row.get('ICD10_CODE') }
                for row in reader
            ]
        recorder(f'Read-ICD Mapping Count: {len(system_mapping)}')

        with connection.cursor() as cursor:
            recorder = self.__record_execution_time('QueryBuilder')

            sql = '''
            create temporary table if not exists temp_mapping
              on commit drop
              as (
                select
                      distinct on (t.read)
                      lower(t.read) as read,
                      lower(regexp_replace(t.read, '[^aA-zZ0-9\-]', '', 'g')) as read_alt,
                      lower(t.icd) as icd,
                      lower(regexp_replace(t.icd, '[^aA-zZ0-9\-]', '', 'g')) as icd_alt
                  from jsonb_to_recordset(%(dataset)s::jsonb) as t (
                    read  varchar(256),
                    icd   varchar(256)
                  )
              );

            create temporary table if not exists temp_entities
              on commit drop
              as (
                select
                      entity.id as phenotype_id,
                      entity.name as phenotype_name,
                      cast(concepts->>'concept_id' as integer) as concept_id,
                      cast(concepts->>'concept_version_id' as integer) as concept_version_id,
                      concept.coding_system_id as coding_system_id,
                      coding.name as coding_system_name
                  from
                      public.clinicalcode_genericentity as entity,
                      json_array_elements(entity.template_data::json->'concept_information') as concepts
            	  join public.clinicalcode_historicalconcept as concept
            	    on concept.id = (concepts->>'concept_id'::text)::int
            	   and concept.history_id = (concepts->>'concept_version_id'::text)::int
            	  join public.clinicalcode_codingsystem as coding
            	    on concept.coding_system_id = coding.codingsystem_id
                 where json_array_length(entity.template_data::json->'concept_information') > 0
                   and entity.template_id = 1
                   and (entity.is_deleted is null or entity.is_deleted = false)
                   and 5 = any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
            	     and not (
                      array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[]
                      && array[4, 13]
                   )
              );

            create temporary table if not exists temp_all_codes
              on commit drop
              as (
                select
                      entity.phenotype_id as phenotype_id,
                      entity.phenotype_name as phenotype_name,
                      concept.id as concept_id,
                      max(concept.history_id) as concept_version_id,
                      entity.coding_system_id as coding_system_id,
                      entity.coding_system_name as coding_system_name,
                      concept.history_date as concept_history_date,
                      component.id as component_id,
                      max(component.history_id) as component_history_id,
                      component.logical_type as logical_type,
                      codelist.id as codelist_id,
                      max(codelist.history_id) as codelist_history_id,
                      codes.id as code_id,
                      lower(codes.code) as code,
                      lower(regexp_replace(codes.code, '[^aA-zZ0-9\-]', '', 'g')) as code_alt,
                      codes.description
                  from temp_entities as entity
                  join public.clinicalcode_historicalconcept as concept
                    on concept.id = entity.concept_id
                   and concept.history_id = entity.concept_version_id
                  join public.clinicalcode_historicalcomponent as component
                    on component.concept_id = concept.id
                   and component.history_date <= concept.history_date
                  left join public.clinicalcode_historicalcomponent as deleted_component
                    on deleted_component.concept_id = concept.id
                   and deleted_component.id = component.id
                   and deleted_component.history_date <= concept.history_date
                   and deleted_component.history_type = '-'
                  join public.clinicalcode_historicalcodelist as codelist
                    on codelist.component_id = component.id
                   and codelist.history_date <= concept.history_date
                   and codelist.history_type <> '-'
                  join public.clinicalcode_historicalcode as codes
                    on codes.code_list_id = codelist.id
                   and codes.history_date <= concept.history_date
                  left join public.clinicalcode_historicalcode as deleted_code
                    on deleted_code.id = codes.id
                   and deleted_code.code_list_id = codelist.id
                   and deleted_code.history_date <= concept.history_date
                   and deleted_code.history_type = '-'
                 where deleted_component.id is null
                   and deleted_code.id is null
                   and component.history_type <> '-'
                   and codes.history_type <> '-'
                   and entity.coding_system_id = 5
                   and (codes.code != '' and codes.code !~ '^\s*$')
                 group by
                          entity.phenotype_id,
                          entity.phenotype_name,
                          concept.id,
                          concept.history_id,
                          concept.history_date, 
                          entity.coding_system_id,
                          entity.coding_system_name,
                          component.id, 
                          component.logical_type, 
                          codelist.id,
                          codes.id,
                          codes.code,
                          codes.description
              );

            create temporary table if not exists temp_codelists
              on commit drop
              as (
                select included_codes.*
                  from temp_all_codes as included_codes
                  left join temp_all_codes as excluded_codes
                    on excluded_codes.code = included_codes.code
                   and excluded_codes.logical_type = 2
                 where included_codes.logical_type = 1
                   and excluded_codes.code is null
              );

            create temporary table if not exists temp_ontology_tags
              on commit drop
              as (
                select
                      node.id as ontology_id,
                      node.name as ontology_descriptor,
                      edge.child_id as ontology_child,
                      edge.parent_id as ontology_parent,
                      node.type_id as ontology_type,
                      icd10.id as ontology_coding_id,
                      lower(icd10.code) as ontology_dot_code,
                      lower(regexp_replace(icd10.alt_code, '[^aA-zZ0-9\-]', '', 'g')) as ontology_alt_code,
                      lower(regexp_replace(icd10.code, '-[^-]+$', '', 'g')) as ontology_min_code,
                      node.atlas_id as ontology_atlas,
                      node.properties as ontology_props
                  from public.clinicalcode_ontologytag node
                  join public.clinicalcode_ontologytagedge edge
                    on edge.child_id = node.id
                  join public.clinicalcode_icd10_codes_and_titles_and_metadata as icd10
                    on lower(regexp_replace(icd10.code, '[^aA-zZ0-9\-]', '', 'g')) = lower(regexp_replace(node.properties->>'code'::text, '[^aA-zZ0-9\-]', '', 'g'))
                 where type_id = 0
              );

            create temporary table if not exists temp_matches
              on commit drop
              as (
                select
                      phenotype_id,
                      phenotype_name,
                      coding_system_id,
                      coding_system_name,
                      ontology.*,
                      code
                  from temp_codelists as codelist
                  join temp_mapping as mapping
                    on (mapping.read_alt = codelist.code_alt)
                  join temp_ontology_tags as ontology
                    on (ontology.ontology_alt_code = mapping.icd_alt)
              );

            select
                  t0.phenotype_id,
                  array_agg(distinct t0.ontology_id::int order by t0.ontology_id::int asc) as all_ontology_ids,
                  array_agg(distinct t0.code::text) as all_code_matches
              from temp_matches as t0
             group by phenotype_id;
            '''
            recorder = self.__record_execution_time('QueryBuilder')
            cursor.execute(sql, params={ 'dataset': json.dumps(system_mapping) })

            columns = [col[0] for col in cursor.description] + ['id_set']
            results = [dict(zip(columns, row + (set(row[1]),))) for row in cursor.fetchall()]
            phenotype_match_count = cursor.rowcount

            recorder(f'Result Count: {phenotype_match_count}')

            sql = '''
            select
                 edge.parent_id,
                 array_agg(edge.child_id::int order by edge.child_id::int asc) as children
              from public.clinicalcode_ontologytagedge as edge
             group by parent_id
             order by parent_id asc;
            '''

            recorder = self.__record_execution_time('OntologyBuilder')
            cursor.execute(sql)

            columns = [col[0] for col in cursor.description] + ['id_set']
            reducible = [dict(zip(columns, row + (set(row[1]),))) for row in cursor.fetchall()]
            recorder()

            recorder = self.__record_execution_time('OntologyReducer')

            global max_depth
            max_depth = None

            global max_depth_id
            max_depth_id = None

            def try_reduce(row_set, ident, depth=0):
                global max_depth, max_depth_id
                if not max_depth or depth > max_depth:
                    max_depth = depth
                    max_depth_id = ident

                try:
                    matched = next((item for item in reducible if item.get('id_set') and item.get('id_set').issubset(row_set)), None) if len(row_set) > 0 else None
                except:
                    matched = None

                if matched is not None:
                    row_set = row_set.difference(matched.get('id_set'))
                    row_set.update([matched.get('parent_id')])
                    return try_reduce(row_set, ident, depth + 1)
                return row_set

            initial_size = 0
            reduced_size = 0
            for row in results:
                row_set = row.get('id_set')
                initial_size += len(row_set)

                row_set = try_reduce(row_set, row.get('phenotype_id'), 0)
                reduced_size += len(row_set)

                row.update({ 'reduced_ids': row_set })

            avg = reduced_size / len(results)
            recorder(f'Reduction<size: Reduction<from: {initial_size:,}, to: {reduced_size:,}>, average: {int(avg):,}, depth: Traversal<max_depth: {max_depth:,}, id: {max_depth_id}>>')

            recorder = self.__record_execution_time('OntologyUpdate')
            sql = '''
            update public.clinicalcode_historicalgenericentity as trg
               set template_data['ontology'] = to_jsonb(src.reduced_ids)
              from (
                select *
                  from jsonb_to_recordset(%(dataset)s::jsonb) as t (
                    phenotype_id     varchar(256),
                    all_ontology_ids integer[],
                    all_code_matches text[],
                    id_set           integer[],
                    reduced_ids      integer[]
                  )
              ) as src
             where trg.id = src.phenotype_id
               and trg.template_id = 1
               and src.reduced_ids is not null
               and array_length(src.reduced_ids, 1) > 0;

            update public.clinicalcode_genericentity as trg
               set template_data['ontology'] = to_jsonb(src.reduced_ids)
              from (
                select *
                  from jsonb_to_recordset(%(dataset)s::jsonb) as t (
                    phenotype_id     varchar(256),
                    all_ontology_ids integer[],
                    all_code_matches text[],
                    id_set           integer[],
                    reduced_ids      integer[]
                  )
              ) as src
             where trg.id = src.phenotype_id
               and trg.template_id = 1
               and src.reduced_ids is not null
               and array_length(src.reduced_ids, 1) > 0;
            '''
            cursor.execute(sql, { 'dataset': json.dumps(results, cls=SetEncoder) })

            phenotype_update_count = cursor.rowcount
            recorder(f'Update Count: {phenotype_update_count:,}')

    def __try_label_icd10(self):
        with connection.cursor() as cursor:
            sql = '''
            create temporary table if not exists temp_entities
              on commit drop
              as (
                select
                      entity.id as phenotype_id,
                      entity.name as phenotype_name,
                      cast(concepts->>'concept_id' as integer) as concept_id,
                      cast(concepts->>'concept_version_id' as integer) as concept_version_id,
                      concept.coding_system_id as coding_system_id,
                      coding.name as coding_system_name
                  from
                      public.clinicalcode_genericentity as entity,
                      json_array_elements(entity.template_data::json->'concept_information') as concepts
            	  join public.clinicalcode_historicalconcept as concept
            	    on concept.id = (concepts->>'concept_id'::text)::int
            	   and concept.history_id = (concepts->>'concept_version_id'::text)::int
            	  join public.clinicalcode_codingsystem as coding
            	    on concept.coding_system_id = coding.codingsystem_id
                 where json_array_length(entity.template_data::json->'concept_information') > 0
                   and entity.template_id = 1
                   and (entity.is_deleted is null or entity.is_deleted = false)
                   and 4 = any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
            	     and 13 != any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
              );

            create temporary table if not exists temp_all_codes
              on commit drop
              as (
                select
                      entity.phenotype_id as phenotype_id,
                      entity.phenotype_name as phenotype_name,
                      concept.id as concept_id,
                      max(concept.history_id) as concept_version_id,
                      entity.coding_system_id as coding_system_id,
                      entity.coding_system_name as coding_system_name,
                      concept.history_date as concept_history_date,
                      component.id as component_id,
                      max(component.history_id) as component_history_id,
                      component.logical_type as logical_type,
                      codelist.id as codelist_id,
                      max(codelist.history_id) as codelist_history_id,
                      codes.id as code_id,
                      lower(codes.code) as code,
                      lower(regexp_replace(codes.code, '[^aA-zZ0-9\-]', '', 'g')) as alt_code,
                      lower(regexp_replace(codes.code, '-[^-]+$', '', 'g')) as min_code,
                      codes.description
                  from temp_entities as entity
                  join public.clinicalcode_historicalconcept as concept
                    on concept.id = entity.concept_id
                   and concept.history_id = entity.concept_version_id
                  join public.clinicalcode_historicalcomponent as component
                    on component.concept_id = concept.id
                   and component.history_date <= concept.history_date
                  left join public.clinicalcode_historicalcomponent as deleted_component
                    on deleted_component.concept_id = concept.id
                   and deleted_component.id = component.id
                   and deleted_component.history_date <= concept.history_date
                   and deleted_component.history_type = '-'
                  join public.clinicalcode_historicalcodelist as codelist
                    on codelist.component_id = component.id
                   and codelist.history_date <= concept.history_date
                   and codelist.history_type <> '-'
                  join public.clinicalcode_historicalcode as codes
                    on codes.code_list_id = codelist.id
                   and codes.history_date <= concept.history_date
                  left join public.clinicalcode_historicalcode as deleted_code
                    on deleted_code.id = codes.id
                   and deleted_code.code_list_id = codelist.id
                   and deleted_code.history_date <= concept.history_date
                   and deleted_code.history_type = '-'
                 where deleted_component.id is null
                   and deleted_code.id is null
                   and component.history_type <> '-'
                   and codes.history_type <> '-'
                   and entity.coding_system_id = 4
                   and (codes.code != '' and codes.code !~ '^\s*$')
                 group by
                          entity.phenotype_id,
                          entity.phenotype_name,
                          concept.id,
                          concept.history_id,
                          concept.history_date, 
                          entity.coding_system_id,
                          entity.coding_system_name,
                          component.id, 
                          component.logical_type, 
                          codelist.id,
                          codes.id,
                          codes.code,
                          codes.description
              );

            create temporary table if not exists temp_codelists
              on commit drop
              as (
                select included_codes.*
                  from temp_all_codes as included_codes
                  left join temp_all_codes as excluded_codes
                    on excluded_codes.code = included_codes.code
                   and excluded_codes.logical_type = 2
                 where included_codes.logical_type = 1
                   and excluded_codes.code is null
              );

            create temporary table if not exists temp_ontology_tags
              on commit drop
              as (
                select
                      node.id as ontology_id,
                      node.name as ontology_descriptor,
                      edge.child_id as ontology_child,
                      edge.parent_id as ontology_parent,
                      node.type_id as ontology_type,
                      icd10.id as ontology_coding_id,
                      lower(icd10.code) as ontology_dot_code,
                      lower(regexp_replace(icd10.alt_code, '[^aA-zZ0-9\-]', '', 'g')) as ontology_alt_code,
                      lower(regexp_replace(icd10.code, '-[^-]+$', '', 'g')) as ontology_min_code,
                      node.atlas_id as ontology_atlas,
                      node.properties as ontology_props
                  from public.clinicalcode_ontologytag node
                  join public.clinicalcode_ontologytagedge edge
                    on edge.child_id = node.id
                  join public.clinicalcode_icd10_codes_and_titles_and_metadata as icd10
                    on icd10.code = node.properties->>'code'::text
                 where type_id = 0
              );

            create temporary table if not exists temp_matches
              on commit drop
              as (
                select
                      phenotype_id,
                      phenotype_name,
                      coding_system_id,
                      coding_system_name,
                      ontology.*,
                      code
                  from temp_codelists as codelist
                  join temp_ontology_tags as ontology
                    on (ontology.ontology_dot_code = codelist.code
                    or ontology.ontology_alt_code = codelist.alt_code)
              );

            select
                  t0.phenotype_id,
                  array_agg(distinct t0.ontology_id::int order by t0.ontology_id::int asc) as all_ontology_ids,
                  array_agg(distinct t0.code::text) as all_code_matches
              from temp_matches as t0
             group by phenotype_id;
            '''

            recorder = self.__record_execution_time('QueryBuilder')
            cursor.execute(sql)

            columns = [col[0] for col in cursor.description] + ['id_set']
            results = [dict(zip(columns, row + (set(row[1]),))) for row in cursor.fetchall()]
            phenotype_match_count = cursor.rowcount

            recorder(f'Result Count: {phenotype_match_count}')

            sql = '''
            select
                 edge.parent_id,
                 array_agg(edge.child_id::int order by edge.child_id::int asc) as children
              from public.clinicalcode_ontologytagedge as edge
             group by parent_id
             order by parent_id asc;
            '''

            recorder = self.__record_execution_time('OntologyBuilder')
            cursor.execute(sql)

            columns = [col[0] for col in cursor.description] + ['id_set']
            reducible = [dict(zip(columns, row + (set(row[1]),))) for row in cursor.fetchall()]
            recorder()

            recorder = self.__record_execution_time('OntologyReducer')

            global max_depth
            max_depth = None

            global max_depth_id
            max_depth_id = None

            def try_reduce(row_set, ident, depth=0):
                global max_depth, max_depth_id
                if not max_depth or depth > max_depth:
                    max_depth = depth
                    max_depth_id = ident

                try:
                    matched = next((item for item in reducible if item.get('id_set') and item.get('id_set').issubset(row_set)), None) if len(row_set) > 0 else None
                except:
                    matched = None

                if matched is not None:
                    row_set = row_set.difference(matched.get('id_set'))
                    row_set.update([matched.get('parent_id')])
                    return try_reduce(row_set, ident, depth + 1)
                return row_set

            initial_size = 0
            reduced_size = 0
            for row in results:
                row_set = row.get('id_set')
                initial_size += len(row_set)

                row_set = try_reduce(row_set, row.get('phenotype_id'), 0)
                reduced_size += len(row_set)

                row.update({ 'reduced_ids': row_set })

            avg = reduced_size / len(results)
            recorder(f'Reduction<size: Reduction<from: {initial_size:,}, to: {reduced_size:,}>, average: {int(avg):,}, depth: Traversal<max_depth: {max_depth:,}, id: {max_depth_id}>>')

            recorder = self.__record_execution_time('OntologyUpdate')
            sql = '''
            update public.clinicalcode_historicalgenericentity as trg
               set template_data['ontology'] = to_jsonb(src.reduced_ids)
              from (
                select *
                  from jsonb_to_recordset(%(dataset)s::jsonb) as t (
                    phenotype_id     varchar(256),
                    all_ontology_ids integer[],
                    all_code_matches text[],
                    id_set           integer[],
                    reduced_ids      integer[]
                  )
              ) as src
             where trg.id = src.phenotype_id
               and trg.template_id = 1
               and src.reduced_ids is not null
               and array_length(src.reduced_ids, 1) > 0;

            update public.clinicalcode_genericentity as trg
               set template_data['ontology'] = to_jsonb(src.reduced_ids)
              from (
                select *
                  from jsonb_to_recordset(%(dataset)s::jsonb) as t (
                    phenotype_id     varchar(256),
                    all_ontology_ids integer[],
                    all_code_matches text[],
                    id_set           integer[],
                    reduced_ids      integer[]
                  )
              ) as src
             where trg.id = src.phenotype_id
               and trg.template_id = 1
               and src.reduced_ids is not null
               and array_length(src.reduced_ids, 1) > 0;
            '''
            cursor.execute(sql, { 'dataset': json.dumps(results, cls=SetEncoder) })

            phenotype_update_count = cursor.rowcount
            recorder(f'Update Count: {phenotype_update_count:,}')

    def add_arguments(self, parser):
        """
            Handles arguments given via the CLI

        """
        parser.add_argument('-p', '--print', type=bool, help='Print debug information to the terminal')
        parser.add_argument('-t', '--type', type=int, help='Which coding system type to process (0 = icd, 1 = read)')

    def handle(self, *args, **kwargs):
        """
            Main command handle

        """
        # init parameters
        verbose = kwargs.get('print')
        process = kwargs.get('type')
        self._verbose = not not verbose

        # det handle
        if process == 0:
            self.__try_label_icd10()
        elif process == 1:
            self.__try_label_readcodes()

