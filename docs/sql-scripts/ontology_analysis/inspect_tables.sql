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


select
	 phenotype_id,
     phenotype_name,
	 string_agg(distinct coding_system_name, ', ') as coding_systems,
     string_agg(distinct code, ', ') as codes,
	 array_agg(array(select value::text::int from json_array_elements(entity.ontologies))) as ontology
  from codelists as codelist
  join entities as entity
    on entity.id = phenotype_id
   and entity.version_id = phenotype_version_id
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


