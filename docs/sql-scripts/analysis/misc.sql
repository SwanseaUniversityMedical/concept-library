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
  ),
  max_entities as (
    select id,
           max(version_id) as version_id,
           concept_id,
           concept_version_id
      from entities
     group by id, concept_id, concept_version_id
  ),
  codelists as (
    select entity.id as phenotype_id,
           entity.version_id as phenotype_version_id,
           concept.id as concept_id,
           max(concept.history_id) as concept_version_id,
           concept.history_date as concept_history_date,
           component.id as component_id,
           max(component.history_id) as component_history_id,
           component.logical_type as logical_type,
           codelist.id as codelist_id,
           max(codelist.history_id) as codelist_history_id,
           codes.id as code_id,
           codes.code,
           codes.description
      from max_entities as entity
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
     group by entity.id,
              entity.version_id,
              concept.id,
              concept.history_id,
              concept.history_date, 
              component.id, 
              component.logical_type, 
              codelist.id,
              codes.id,
              codes.code,
              codes.description
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
  
