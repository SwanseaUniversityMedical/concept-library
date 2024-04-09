/**********************************
 *                                *
 *       Labeling Assessment      *
 *                                *
 **********************************/

with
  -- select all concept information related with each historical version of a phenotype
  entities as (
    select entity.id as phenotype_id,
           entity.history_id as phenotype_version_id,
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where json_array_length(entity.template_data::json->'concept_information') > 0
       and entity.template_id = 1
       and (entity.is_deleted is null or entity.is_deleted = false)
  ),
  -- select all codes associated with each each historical version of a phenotype
  codelists as (
    select entity.phenotype_id as phenotype_id,
           entity.phenotype_version_id as phenotype_version_id,
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
     group by entity.phenotype_id,
              entity.phenotype_version_id,
              concept.id,
              concept.history_id,
              concept.coding_system_id,
              concept.history_date, 
              component.id, 
              component.logical_type, 
              codelist.id,
              codes.id,
              codes.code,
              codes.description
  ),
  -- select each concepts associated with each historical phenotype
  concepts as (
     select entity.phenotype_id as phenotype_id,
            entity.phenotype_version_id as phenotype_version_id,
            concept.id as concept_id,
            concept.history_id as concept_version_id,
            concept.coding_system_id
       from public.clinicalcode_historicalconcept as concept
       join entities as entity
         on entity.concept_id = concept.id
        and entity.concept_version_id = concept.history_id
  ),
  -- select all distinct & latest concept_ids associated with each historical phenotype
  distinct_cids as (
    select entity.concept_id,
           max(entity.concept_version_id) as concept_version_id,
           count(entity.concept_id)
      from entities as entity
      group by entity.concept_id
  ),
  -- select & match distinct concepts across all phenotypes
  distinct_concepts as (
    select phenotype_id,
           phenotype_version_id,
           concept_id,
           concept_version_id,
           coding_system_id
      from (
        select *,
               rank() over (
                 partition by concept_id
                     order by phenotype_id asc,
                              concept_version_id desc,
                              phenotype_version_id asc
               ) as rank
          from concepts
      ) as c
     where rank = 1
  ),
  -- select & count the different coding systems present across all phenotypes
  distinct_systems as (
    select counts.ref_count,
           coding.*
      from public.clinicalcode_codingsystem as coding
      join (
        select concept.coding_system_id as cid,
               count(concept.coding_system_id) as ref_count
          from distinct_concepts as concept
         group by concept.coding_system_id
      ) as counts
        on counts.cid = coding.id
  )


-------------------------------------------------------------

/**********************************
 *                                *
 *         View concept(s)        *
 *                                *
 **********************************/

/*
   Measure ...
     1. Total number of distinct concepts across phenotypes
     2. Concept reference count(s)

*/

-- select count(*),
--        json_agg(to_json(t))
-- from (
--   select counted.*,
--          concept.coding_system_id
--     from (
--       select concept_id,
--              count(*) as count
--         from distinct_concepts
--        group by concept_id
--       ) as counted
--     join distinct_concepts as concept
--       on concept.concept_id = counted.concept_id
--    order by counted.count desc
-- ) as t;


-------------------------------------------------------------

/**********************************
 *                                *
 *        View codelist(s)        *
 *                                *
 **********************************/

/* Count codelist sizes across all historical phenotypes */

-- select phenotype_id,
--        phenotype_version_id,
--        count(distinct concept_id) as concept_len,
--        count(code) as code_len
--   from codelists
--  group by phenotype_id,
--           phenotype_version_id
--  order by count(code) desc, count(distinct concept_id) desc;



/* Count codelist sizes across all unique concepts */

-- select concept_id,
--        count(distinct code) as code_len
--   from (
--     select *,
--            rank() over (
--              partition by concept_id
--                  order by phenotype_id desc,
--                           concept_version_id desc,
--                           phenotype_version_id desc
--            ) as rank
--       from codelists
--   ) as c
--  group by 1
--  order by 2 desc



-------------------------------------------------------------

/**********************************
 *                                *
 *          View system(s)        *
 *                                *
 **********************************/

/* View coding system counts across all historical phenotypes */

-- select *
--   from distinct_systems
--  order by ref_count desc;



/* Det. remaining after mapping ICD-10 codes */

-- select count(codingsystem_id) as num_coding_systems,
--        sum(ref_count) as total_concept_count,
--        (
--            select ref_count
--              from distinct_systems
--            where codingsystem_id = 4
--        ) as icd10_concept_count,
--        (
--          sum(ref_count) - (
--            select ref_count
--              from distinct_systems
--            where codingsystem_id = 4
--          )
--        ) as remaining_concepts
--   from distinct_systems;



/* View code frequency across coding systems */

-- select c.code,
--        s.name,
--        c.coding_system_id,
--        c.count_code
--   from (
--     select code,
--            coding_system_id,
--            count(code) as count_code
--       from codelists
--      group by 1, 2
--   ) as c
--   join public.clinicalcode_codingsystem as s
--     on s.codingsystem_id = c.coding_system_id
--   order by 4 desc;



/* View coding system frequency across codes */

-- select c.coding_system_id,
--        s.name,
--        c.count_coding_system
--   from (
--     select c.coding_system_id,
--            count(c.coding_system_id) as count_coding_system
--       from (
--         select *,
--                rank() over (
--                   partition by code
--                       order by codelist_history_id asc
--                ) as rank
--           from codelists
--       ) as c
--      where c.rank = 1
--      group by 1
--   ) as c
--   join public.clinicalcode_codingsystem as s
--     on s.codingsystem_id = c.coding_system_id
--   order by 3 desc;

/* View erroneous codes */

select *
  from codelists
 where code ~ '^\s*$';

-------------------------------------------------------------
