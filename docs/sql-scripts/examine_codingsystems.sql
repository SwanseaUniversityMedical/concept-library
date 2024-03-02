/*

  Data structures....

    1. Clinical GenericEntity model template structure:

      HistoricalGenericEntity::model {
        template_data::jsonb {
          'concept_information'::jsonb<Array[]> [
            { 'concept_id': number, 'concept_version_id': number, 'attributes': array[] },
            { 'concept_id': number, 'concept_version_id': number, 'attributes': array[] },
          ],

          'coding_system'::jsonb<Array[]> [
            coding_system_id,
            coding_system_id
          ],
        }
      }

    2. Need to:
      - Find all coding systems associated with a phenotype and aggregate them
      - Update each HistoricalGenericEntity model with the updated coding system field

      e.g.

        GenericEntity<PH1584/2909>::model {
          template_data::jsonb {
            'concept_information'::jsonb<Array[]> [
              { concept_id: 3405, concept_version_id: 10431 },
              { concept_id: 3407, concept_version_id: 10433 },
              { concept_id: 716, concept_version_id: 2571 },
            ],

            'coding_system'::jsonb<Array[]> [
              4, 5, 3
            ],
          }
        }

*/

/**********************************
 *                                *
 *      Det. array aggregates     *
 *                                *
 **********************************/

--  select entity.phenotype_id,
--         entity.phenotype_version_id,
--         array_agg(distinct concept.coding_system_id::integer) as coding_system
--    from public.clinicalcode_historicalconcept as concept
--    join entities as entity
--      on entity.concept_id = concept.id and entity.concept_version_id = concept.history_id
--   group by entity.phenotype_id, entity.phenotype_version_id


/**********************************
 *                                *
 *     Det. array comparisons     *
 *                                *
 **********************************/

-- select id as phenotype_id,
--        history_id as phenotype_version_id,
--        array(
--          select jsonb_array_elements_text(entity.template_data->'coding_system')
--        )::int[]
--   from public.clinicalcode_historicalgenericentity as entity
--  where json_array_length(entity.template_data::json->'coding_system') > 0


/**********************************
 *                                *
 *       Update all entities      *
 *                                *
 **********************************/

update public.clinicalcode_historicalgenericentity as trg
   set template_data['coding_system'] = to_jsonb(src.coding_system)
  from (
     select entity.phenotype_id,
            entity.phenotype_version_id,
            array_agg(distinct concept.coding_system_id::integer) as coding_system
       from public.clinicalcode_historicalconcept as concept
       join (
        select id as phenotype_id,
               history_id as phenotype_version_id,
               cast(concepts->>'concept_id' as integer) as concept_id,
               cast(concepts->>'concept_version_id' as integer) as concept_version_id
          from (
            select id,
                   history_id,
                   concepts
              from public.clinicalcode_historicalgenericentity as entity,
                   json_array_elements(entity.template_data::json->'concept_information') as concepts
             where json_array_length(entity.template_data::json->'concept_information') > 0
        ) results
       ) as entity
    on entity.concept_id = concept.id and entity.concept_version_id = concept.history_id
    group by entity.phenotype_id, entity.phenotype_version_id
  ) src
 where trg.id = src.phenotype_id
   and trg.history_id = src.phenotype_version_id
   and array(
        select jsonb_array_elements_text(trg.template_data->'coding_system')
      )::int[] <> src.coding_system;
