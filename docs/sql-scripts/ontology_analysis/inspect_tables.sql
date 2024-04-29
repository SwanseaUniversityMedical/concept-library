with
  entities as (
    select entity.id as id,
           entity.history_id as version_id,
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where json_array_length(entity.template_data::json->'concept_information') > 0
       and entity.template_id = 1
       and (entity.is_deleted is null or entity.is_deleted = false)
	     and not (
        array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[]
        && array[4, 17, 18, 5, 6, 9, 13]
       )
  ),
  latest_entities as (
    select id,
           max(version_id) as version_id,
           concept_id,
           concept_version_id
      from entities
     group by id, concept_id, concept_version_id
  ),
  latest_codelists as (
    select entity.id as phenotype_id,
           entity.version_id as phenotype_version_id,
           ge.name as phenotype_name,
	         au.username as phenotype_owner,
           concept.id as concept_id,
           max(concept.history_id) as concept_version_id,
           concept.coding_system_id as coding_system_id,
           concept.history_date as concept_history_date,
           component.id as component_id,
           max(component.history_id) as component_history_id,
           component.logical_type as logical_type,
           codelist.id as codelist_id,
           max(codelist.history_id) as codelist_history_id,
           codes.id as code_id,
           codes.code,
           codes.description
      from latest_entities as entity
	    join public.clinicalcode_genericentity as ge
	      on ge.id = entity.id
	    join public.auth_user as au
	      on au.id = ge.created_by_id
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
       and (codes.code != '' and codes.code !~ '^\s*$')
     group by entity.id,
              entity.version_id,
              ge.name,
	            au.username,
              concept.id,
              concept.history_id,
              concept.history_date, 
              concept.coding_system_id,
              component.id, 
              component.logical_type, 
              codelist.id,
              codes.id,
              codes.code,
              codes.description
  ),
  computed_codelists as (
    select included_codes.*
      from latest_codelists as included_codes
      left join latest_codelists as excluded_codes
        on excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
  ),
  codelists as (
    select
          codelist.phenotype_id,
          codelist.phenotype_name,
          codelist.phenotype_version_id,
	        codelist.phenotype_owner,
          'C' || codelist.concept_id::text as concept_id,
          codelist.concept_version_id,
          codelist.component_id,
          codelist.component_history_id,
          codelist.codelist_id,
          codelist.codelist_history_id,
          codelist.coding_system_id,
          (
            case
              when coding_system_id =  4 then 'ICD10'
              when coding_system_id =  5 then 'ReadCodesV2'
              when coding_system_id =  6 then 'ReadCodesV3'
              when coding_system_id =  7 then 'OPCS4'
              when coding_system_id =  8 then 'CPRD MedCodes'
              when coding_system_id =  9 then 'SNOMED CT'
              when coding_system_id = 10 then 'PROD Codes'
              when coding_system_id = 11 then 'BNF Codes'
              when coding_system_id = 12 then 'UKBioBank'
              when coding_system_id = 14 then 'GPRD Product Code'
              when coding_system_id = 15 then 'OXMIS'
              when coding_system_id = 16 then 'Multilex'
              when coding_system_id = 17 then 'ICD9'
              when coding_system_id = 18 then 'ICD11'
              when coding_system_id = 19 then 'CTV3'
              when coding_system_id = 20 then 'ICPC-2'
              when coding_system_id = 21 then 'EMIS'
              when coding_system_id = 22 then 'Vision Codes'
              when coding_system_id = 23 then 'DM+D Codes'
              else null
            end
          ) as coding_system_name,
          codelist.code_id,
          codelist.code,
          codelist.description
      from computed_codelists as codelist
  ),
  sizes as (
    select phenotype_id,
           phenotype_version_id,
           count(distinct concept_id) as concept_len,
           count(code) as code_len
      from codelists
     group by phenotype_id,
              phenotype_version_id
     order by count(code) desc
  ),
  systems as (
    select entity.id,
           coding::text::int as coding_system
    from public.clinicalcode_genericentity as entity,
         json_array_elements(entity.template_data::json->'coding_system') as coding
    where entity.template_id = 1
      and (entity.is_deleted is null or entity.is_deleted = false)
  ),
  agg_systems as (
    select entity.id,
           array_agg(coding::text::int) as coding_system
    from public.clinicalcode_genericentity as entity,
         json_array_elements(entity.template_data::json->'coding_system') as coding
    where entity.template_id = 1
      and (entity.is_deleted is null or entity.is_deleted = false)
    group by entity.id
  )



-------------------------------------------------------------

-- File-related

select
        phenotype_id,
        phenotype_name,
        concept_id,
        code_id,
        coding_system_id,
        coding_system_name,
        code,
        description
  from codelists as codelist
 order by
          cast(regexp_replace(phenotype_id, '[a-zA-Z]+', '') as integer) asc,
          concept_id asc,
          coding_system_id asc


select
	   phenotype_id,
     phenotype_name,
	   string_agg(distinct coding_system_name, ', ') as coding_systems,
     string_agg(distinct code, ', ') as codes
  from codelists as codelist
 group by phenotype_id, phenotype_name
 order by cast(regexp_replace(phenotype_id, '[a-zA-Z]+', '') as integer) asc

-------------------------------------------------------------

-- Det. average codelist size

-- select 
--        to_char(sum(code_len)::int, 'fm999G999') as total_used_codes,
--        to_char(avg(code_len)::int, 'fm999G999') as avg_codelist_size,
--        to_char(sum(concept_len)::int, 'fm999G999') as total_used_concepts,
--        to_char(avg(concept_len)::int, 'fm999G999') as avg_concept_length
--   from sizes;



-------------------------------------------------------------

-- Det. type across phenotypes

-- select type_id,
--        (
--          case
--            when type_id = 1 then 'Biomarker'
--            when type_id = 2 then 'Disease Or Syndrome'
--            when type_id = 3 then 'Drug'
--            when type_id = 4 then 'Lifestyle Risk Factor'
--            when type_id = 5 then 'Musculoskeletal'
--            when type_id = 6 then 'Surgical Procedure'
--            else 'Other'
--          end
--        ) as type_name,
--        count(type_id) as count_phenotype_types
--   from (
--     select cast(entity.template_data::json->>'type' as integer) as type_id
--       from public.clinicalcode_genericentity as entity
--      where entity.template_data::json->'type' is not null
--        and entity.template_id = 1
--   ) as entity
--  group by type_id
--  order by count_phenotype_types desc;



-------------------------------------------------------------

-- Det. codelist size(s)

-- select phenotype_id,
--        phenotype_version_id,
--        count(distinct concept_id) as concept_len,
--        count(code) as code_len
--   from codelists
--  group by phenotype_id,
--           phenotype_version_id
--  order by count(code) desc, count(distinct concept_id) desc;

-------------------------------------------------------------

-- System counting via Phenotypes

-- select count(distinct entity.id) as total_phenotypes,
--        count(entity.coding_system) as total_coding_references,
--   from systems as entity
--   join public.clinicalcode_codingsystem as coding
--     on coding.codingsystem_id = entity.coding_system

-- select
--       (
--         select count(distinct id)
--           from systems
--          where systems.coding_system = coding.codingsystem_id
--       ) as "count",
--       coding.codingsystem_id as coding_id,
--       coding.name as coding_system_name
--   from public.clinicalcode_codingsystem as coding
--  where (
--         select count(distinct id)
--           from systems
--          where systems.coding_system = coding.codingsystem_id
--       ) > 0
--  order by "count" desc

-- System counting via Concepts

-- select
--       count(distinct id) as total_phenotypes,
--       (
--         select count(distinct id)
--           from systems as s
--          where coding_system = ANY(array[4, 5, 6, 9, 17, 18])
--       ) as total_mappable,
--       sum(
--         case
--           when (coding_system = ANY(ARRAY[17, 4, 18]) and coding_system != ANY(ARRAY[9, 5, 6])) then 1
--           else 0
--         end
--       ) as icd_mappable,
--       sum(
--         case
--           when (coding_system = ANY(ARRAY[9]) and coding_system != ANY(ARRAY[17, 4, 18, 5, 6])) then 1
--           else 0
--         end
--       ) as snomed_mappable,
--       sum(
--         case
--           when (coding_system = ANY(ARRAY[5, 6]) and coding_system != ANY(ARRAY[17, 4, 18, 9])) then 1
--           else 0
--         end
--       ) as read_mappable
--   from systems as entity



-------------------------------------------------------------

-- Misc.

-- select count(distinct concept_id) as distinct_phenotypes
--   from entities;


-------------------------------------------------------------

-- Chapters post-review with DT

with
  recursive ancestry(parent_id, child_id, depth, path) as (
    select n0.parent_id,
           n0.child_id,
           1 as depth,
           array[n0.parent_id, n0.child_id] as path
      from public.clinicalcode_ontologytagedge as n0
      left outer join public.clinicalcode_ontologytagedge as n1
        on n0.parent_id = n1.child_id
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
  entities as (
    select
          entity.id as phenotype_id,
          (select max(history_id) from public.clinicalcode_historicalgenericentity where id = entity.id) as phenotype_version_id,
          entity.name as phenotype_name,
          cast(concepts->>'concept_id' as integer) as concept_id,
          cast(concepts->>'concept_version_id' as integer) as concept_version_id,
          concept.coding_system_id as coding_system_id,
          coding.name as coding_system_name
      from public.clinicalcode_genericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
      join public.clinicalcode_historicalconcept as concept
        on concept.id = (concepts->>'concept_id'::text)::int
       and concept.history_id = (concepts->>'concept_version_id'::text)::int
      join public.clinicalcode_codingsystem as coding
        on concept.coding_system_id = coding.codingsystem_id
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
       and json_array_length(entity.template_data::json->'concept_information') > 0
       and (entity.is_deleted is null or entity.is_deleted = false)
       and entity.template_data->>'type' = '2'
       and 4 = any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
       and 13 != any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
  ),
  mappings as (
    select
          entity.id as phenotype_id,
          array(
            select distinct ontology::text::integer as ontology_id
              from json_array_elements(entity.template_data::json->'ontology') as ontology
          ) as ontology_ids,
          array(
            select distinct tag.name
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_names,
          array(
            select 
                  distinct coalesce(
                    (
                      select distinct tag.name
                        from ancestors as ancestor
                        join public.clinicalcode_ontologytag as tag
                          on tag.id = ancestor.path[1]
                      where ancestor.child_id = ontology::text::integer
					  limit 1
                    ),
					tag.name
                  )
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_chapters
      from public.clinicalcode_genericentity as entity
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
  ),
  all_codes as (
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
      from entities as entity
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
  ),
  codelists as (
    select included_codes.*
      from all_codes as included_codes
      left join all_codes as excluded_codes
        on excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
  ),
  phenotypes as (
    select
          codelist.phenotype_id,
          string_agg(distinct codelist.coding_system_name, ', ') as coding_systems,
          string_agg(distinct codelist.code, ', ') as codes,
          string_agg(distinct substr(regexp_replace(codelist.code, '\W', '', 'g'), 1, 3), ', ') as codes_3char
      from codelists as codelist
     group by codelist.phenotype_id
  )

select
      pheno.phenotype_id,
      pheno.coding_systems,
      pheno.codes,
      pheno.codes_3char,
      mapped.ontology_names,
      mapped.ontology_chapters,
      mapped.ontology_ids
  from phenotypes as pheno
  join mappings as mapped
    on mapped.phenotype_id = pheno.phenotype_id
 order by cast(regexp_replace(pheno.phenotype_id, '[a-zA-Z]+', '') as integer) asc


-------------------------------------------------------------

-- Post-HH review

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
  entities as (
    select
          entity.id as phenotype_id,
          entity.history_id as phenotype_version_id,
          entity.name as phenotype_name,
          cast(concepts->>'concept_id' as integer) as concept_id,
          cast(concepts->>'concept_version_id' as integer) as concept_version_id,
          concept.coding_system_id as coding_system_id,
          coding.name as coding_system_name
      from (
        select
              entity.*,
              published.entity_history_id as history_id
          from public.clinicalcode_genericentity as entity
          join (
            select
                  published.entity_id,
                  max(published.entity_history_id) as entity_history_id
              from public.clinicalcode_publishedgenericentity as published
             group by published.entity_id
          ) as published
            on entity.id = published.entity_id
      ) as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
      join public.clinicalcode_historicalconcept as concept
        on concept.id = (concepts->>'concept_id'::text)::int
       and concept.history_id = (concepts->>'concept_version_id'::text)::int
      join public.clinicalcode_codingsystem as coding
        on concept.coding_system_id = coding.codingsystem_id
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
       and json_array_length(entity.template_data::json->'concept_information') > 0
       and (entity.is_deleted is null or entity.is_deleted = false)
       and entity.template_data->>'type' = '2'
       and 4 = any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
       and 13 != any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
  ),
  mappings as (
    select
          entity.id as phenotype_id,
          array(
            select distinct ontology::text::integer as ontology_id
              from json_array_elements(entity.template_data::json->'ontology') as ontology
          ) as ontology_ids,
          array(
            select distinct tag.name
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_names,
          array(
            select 
                  distinct coalesce(
                    (
                      select distinct tag.name
                        from ancestors as ancestor
                        join public.clinicalcode_ontologytag as tag
                          on tag.id = ancestor.path[1]
                      where ancestor.child_id = ontology::text::integer
					  limit 1
                    ),
					tag.name
                  )
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_chapters
      from public.clinicalcode_genericentity as entity
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
  ),
  all_codes as (
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
      from entities as entity
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
  ),
  codelists as (
    select
          included_codes.*
      from all_codes as included_codes
      left join all_codes as excluded_codes
        on excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
  ),
  phenotypes as (
    select
          codelist.phenotype_id,
          codelist.phenotype_name,
          string_agg(distinct codelist.coding_system_name, ', ') as coding_systems,
          string_agg(distinct codelist.code, ', ') as codes,
          string_agg(distinct substr(regexp_replace(codelist.code, '\W', '', 'g'), 1, 3), ', ') as codes_3char
      from codelists as codelist
     group by codelist.phenotype_id, codelist.phenotype_name
  )

select
      pheno.phenotype_id,
      pheno.phenotype_name,
      pheno.coding_systems,
      pheno.codes,
      pheno.codes_3char,
      mapped.ontology_names,
      mapped.ontology_chapters,
      mapped.ontology_ids
  from phenotypes as pheno
  join mappings as mapped
    on mapped.phenotype_id = pheno.phenotype_id
 order by cast(regexp_replace(pheno.phenotype_id, '[a-zA-Z]+', '') as integer) asc


-------------------------------------------------------------

-- Comp unmapped

with
  entities as (
    select
          entity.id as phenotype_id,
          entity.history_id as phenotype_version_id,
          entity.name as phenotype_name,
          cast(concepts->>'concept_id' as integer) as concept_id,
          cast(concepts->>'concept_version_id' as integer) as concept_version_id,
          concept.coding_system_id as coding_system_id,
          coding.name as coding_system_name
      from (
        select
              entity.*,
              published.entity_history_id as history_id
          from public.clinicalcode_genericentity as entity
          join (
            select
                  published.entity_id,
                  max(published.entity_history_id) as entity_history_id
              from public.clinicalcode_publishedgenericentity as published
             group by published.entity_id
          ) as published
            on entity.id = published.entity_id
      ) as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
      join public.clinicalcode_historicalconcept as concept
        on concept.id = (concepts->>'concept_id'::text)::int
       and concept.history_id = (concepts->>'concept_version_id'::text)::int
      join public.clinicalcode_codingsystem as coding
        on concept.coding_system_id = coding.codingsystem_id
     where json_array_length(entity.template_data::json->'concept_information') > 0
       and (entity.is_deleted is null or entity.is_deleted = false)
       and entity.template_data->>'type' = '2'
       and not (
          array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[]
          && array[4, 17, 18, 13]
       )
  ),
  all_codes as (
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
      from entities as entity
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
  ),
  codelists as (
    select
          included_codes.*
      from all_codes as included_codes
      left join all_codes as excluded_codes
        on excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
  ),
  phenotypes as (
    select
          codelist.phenotype_id,
          codelist.phenotype_name,
          string_agg(distinct codelist.coding_system_name, ', ') as coding_systems,
          string_agg(distinct codelist.code, ', ') as codes
      from codelists as codelist
     group by codelist.phenotype_id, codelist.phenotype_name
  )

select *
  from phenotypes pheno
 order by cast(regexp_replace(pheno.phenotype_id, '[a-zA-Z]+', '') as integer) asc;

select
        phenotype_id,
        phenotype_name,
        concept_id,
        code_id,
        coding_system_id,
        coding_system_name,
        code,
        description
  from codelists as codelist
 order by
          cast(regexp_replace(phenotype_id, '[a-zA-Z]+', '') as integer) asc,
          concept_id asc,
          coding_system_id asc;


-------------------------------------------------------------

-- Drop temp(s)

drop table if exists temp_ancestors;
drop table if exists temp_mappings;
drop table if exists temp_entities;
drop table if exists temp_all_codes;
drop table if exists temp_codelists;
drop table if exists temp_phenotypes;

-- Draft review ICD + ReadCodes

create temp table if not exists temp_ancestors(child_id bigint, path bigint[])
  on commit preserve rows;

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
  )

insert into temp_ancestors
select * from ancestors;

create temp table if not exists temp_mappings
 on commit preserve rows
 as (
    select
          entity.id as phenotype_id,
          array(
            select distinct ontology::text::integer as ontology_id
              from json_array_elements(entity.template_data::json->'ontology') as ontology
          ) as ontology_ids,
          array(
            select distinct tag.name
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_names,
          array(
            select 
                  distinct coalesce(
                    (
                      select distinct tag.name
                        from temp_ancestors as ancestor
                        join public.clinicalcode_ontologytag as tag
                          on tag.id = ancestor.path[1]
                      where ancestor.child_id = ontology::text::integer
					  limit 1
                    ),
					tag.name
                  )
              from json_array_elements(entity.template_data::json->'ontology') as ontology
              join public.clinicalcode_ontologytag as tag
                on tag.id = ontology::text::integer
          ) as ontology_chapters
      from public.clinicalcode_genericentity as entity
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
 );

create temp table if not exists temp_entities
 on commit preserve rows
 as (
    select
          entity.id as phenotype_id,
          entity.history_id as phenotype_version_id,
          entity.name as phenotype_name,
          cast(concepts->>'concept_id' as integer) as concept_id,
          cast(concepts->>'concept_version_id' as integer) as concept_version_id,
          concept.coding_system_id as coding_system_id,
          coding.name as coding_system_name
      from (
        select
              entity.*,
              published.entity_history_id as history_id
          from public.clinicalcode_genericentity as entity
          join (
            select
                  published.entity_id,
                  max(published.entity_history_id) as entity_history_id
              from public.clinicalcode_publishedgenericentity as published
             group by published.entity_id
          ) as published
            on entity.id = published.entity_id
      ) as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
      join public.clinicalcode_historicalconcept as concept
        on concept.id = (concepts->>'concept_id'::text)::int
       and concept.history_id = (concepts->>'concept_version_id'::text)::int
      join public.clinicalcode_codingsystem as coding
        on concept.coding_system_id = coding.codingsystem_id
     where json_typeof(entity.template_data::json->'ontology') = 'array'
       and json_array_length(entity.template_data::json->'ontology') > 0
       and json_array_length(entity.template_data::json->'concept_information') > 0
       and (entity.is_deleted is null or entity.is_deleted = false)
       and entity.template_data->>'type' = '2'
       and array[4, 5] && array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[]
       and 13 != any(array(select json_array_elements_text(entity.template_data::json->'coding_system'))::int[])
 );

create temp table if not exists temp_all_codes
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
       and entity.coding_system_id = any(array[4, 5])
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

create temp table if not exists temp_codelists
 on commit preserve rows
 as (
    select
          included_codes.*
      from temp_all_codes as included_codes
      left join temp_all_codes as excluded_codes
        on excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
 );

create temp table if not exists temp_phenotypes
 on commit preserve rows
 as (
    select
          codelist.phenotype_id,
          codelist.phenotype_name,
          string_agg(distinct codelist.coding_system_name, ', ') as coding_systems,
          string_agg(distinct codelist.code, ', ') as codes,
          string_agg(distinct substr(regexp_replace(codelist.code, '\W', '', 'g'), 1, 3), ', ') as codes_3char
      from temp_codelists as codelist
     group by codelist.phenotype_id, codelist.phenotype_name
 );

select
      pheno.phenotype_id,
      pheno.phenotype_name,
      pheno.coding_systems,
      pheno.codes,
      pheno.codes_3char,
      mapped.ontology_names,
      mapped.ontology_chapters,
      mapped.ontology_ids
  from temp_phenotypes as pheno
  join temp_mappings as mapped
    on mapped.phenotype_id = pheno.phenotype_id
 order by cast(regexp_replace(pheno.phenotype_id, '[a-zA-Z]+', '') as integer) asc;
