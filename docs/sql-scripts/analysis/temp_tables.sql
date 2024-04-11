/*markdown
### Drop if required
*/
 

drop table if exists temp_entities;
drop table if exists temp_all_codes;
drop table if exists temp_codelists;
drop table if exists temp_ontology_tags;
drop table if exists temp_matches;

 
/*markdown
### ICD-10 map temp tables
*/
 

create temporary table if not exists temp_entities
  on commit preserve rows
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
  on commit preserve rows
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
  on commit preserve rows
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
  on commit preserve rows
  as (
    select
          node.id as ontology_id,
          node.name as ontology_descriptor,
          edge.child_id as ontology_child,
          edge.parent_id as ontology_parent,
          node.type_id as ontology_type,
          icd10.id as ontology_coding_id,
          lower(icd10.code) as ontology_dot_code,
          lower(icd10.alt_code) as ontology_alt_code,
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
  on commit preserve rows
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
        or ontology.ontology_alt_code = codelist.code)
  );


/*markdown
### Det. matched count(s) 
*/
 

select
      t0.phenotype_id,
      (
        select count(distinct t1.ontology_id)
          from temp_matches t1
         where t1.phenotype_id = t0.phenotype_id
      ) as count_total_matches,
      (
        select string_agg(distinct t1.code, ', ')
          from temp_matches t1
         where t1.phenotype_id = t0.phenotype_id
      ) as all_matches
  from temp_codelists as t0
 group by phenotype_id
 order by count_total_matches desc;


/*markdown
### Det. total matched
*/
 

select
      count(t0.phenotype_id) as total_count,
      sum(
        case
          when exists(select 1 from temp_matches t1 where t1.phenotype_id = t0.phenotype_id) then 1
          else 0
        end
      ) as total_matched
 from (
   select distinct phenotype_id
	   from temp_codelists
 ) as t0;


/*markdown
### Reduce parents ...
*/
 

select ont_matches.*
  from (
    select
          phenotype_id,
          ontology_parent::int as ontology_parent,
          array_agg(ontology_id::int) as ontology_ids
      from temp_matches
    group by phenotype_id, ontology_parent
  ) as ont_matches
  join (
    select edge.parent_id,
           array_agg(edge.child_id::int) as children
      from public.clinicalcode_ontologytagedge as edge
     group by parent_id
  ) as ontology
    on ontology.parent_id = ont_matches.ontology_parent
 where ontology.children <@ ont_matches.ontology_ids;


/*markdown
### Try collect ontology after reduction ...
*/
 

with
  reduced_ontology as (
    select ont_matches.*
      from (
        select
              phenotype_id,
              ontology_parent::int as ontology_id,
              array_agg(ontology_id::int) as ontology_ids
          from temp_matches
         group by phenotype_id, ontology_parent
      ) as ont_matches
      join (
        select edge.parent_id,
              array_agg(edge.child_id::int) as children
          from public.clinicalcode_ontologytagedge as edge
         group by parent_id
      ) as ontology
        on ontology.parent_id = ont_matches.ontology_id
     where ontology.children <@ ont_matches.ontology_ids
  )

select
      phenotype_id,
      array_length(array_agg(
		distinct
	  	case
		  when exists(select 1 from reduced_ontology where ontology_parent::int = t0.ontology_parent::int and t0.phenotype_id = phenotype_id) then ontology_parent::int
		  else ontology_id::int
		end
	  ), 1) as ontology_count,
	  array_length(array_agg(distinct t0.ontology_id::int), 1) as ontology_prev,
	  array_agg(
		distinct
	  	case
		  when exists(select 1 from reduced_ontology where ontology_parent::int = t0.ontology_parent::int and t0.phenotype_id = phenotype_id) then ontology_parent::int
		  else ontology_id::int
		end
	  ) as ontol_ids,
	  array_agg(distinct t0.ontology_id::int) as prev_ontol_ids
  from temp_matches t0
 group by phenotype_id
 order by 2 desc
