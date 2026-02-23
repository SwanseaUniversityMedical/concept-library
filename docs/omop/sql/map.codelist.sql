do $tx$
declare
  _cursor constant refcursor := '_cursor';
begin
  --[!] Create coding system map lookup
  drop table if exists coding_lookup cascade;

  create temp table coding_lookup as
  select *
    from (
      values
        (     'dm+d'::text,      '{23}'::int[],   '{23}'::int[]),
        (     'MeSH'::text,      '{26}'::int[],   '{26}'::int[]),
        (     'ICD9'::text,      '{17}'::int[],   '{17}'::int[]),
        (    'ICD10'::text, '{4,24,25}'::int[],   '{25}'::int[]),
        (    'OPCS4'::text,       '{7}'::int[],    '{7}'::int[]),
        (    'OXMIS'::text,      '{15}'::int[], '{5,15}'::int[]),
        (   'READV2'::text,       '{5}'::int[],    '{5}'::int[]),
        (   'SNOMED'::text,       '{9}'::int[],    '{9}'::int[]),
        ('UKBioBank'::text,      '{12}'::int[],   '{12}'::int[])
    ) as t(name, in_coding, out_coding);

  --[!] Create intermediate tables
  drop table if exists omop_init_match cascade;
  drop table if exists omop_best_match cascade;

  create temp table omop_init_match(
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    concept_id           int          not null,
    concept_version_id   bigint       not null,
    omop_id              varchar(64)  not null,
    omop_name            varchar(256) not null,
    omop_vocabulary      varchar(64)  not null,
    omop_code            varchar(64)  not null,
    invalid_reason       varchar(1)   default null,
    origin_code          varchar(64)  not null,
    origin_system_id     int          not null,
    origin_system_name   varchar(64)  not null
  );

  create temp table omop_best_match(
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    concept_id           int          not null,
    concept_version_id   bigint       not null,
    omop_id              varchar(64)  not null,
    omop_name            varchar(256) not null,
    omop_vocabulary      varchar(64)  not null,
    omop_code            varchar(64)  not null,
    invalid_reason       varchar(1)   default null,
    origin_code          varchar(64)  not null,
    origin_system_id     int          not null,
    origin_system_name   varchar(64)  not null
  );

  --[!] Create stat tables
  drop table if exists omop_phenotype_info cascade;
  drop table if exists omop_concept_info   cascade;

  create unlogged table omop_phenotype_info(
    phenotype_id          varchar(50)  not null,
    phenotype_version_id  bigint       not null,
    coding_system_ids     int[]        not null,
    coding_system_names   text[]       not null,
    coding_system_count   int          not null,
    mapped_system_count   int          not null,
    mapped_system_rate    real         not null, -- i.e. % of concepts that use coding systems with OMOP crossmaps
    total_size            int          not null, -- i.e. total size of codelist including those from coding systems without OMOP crossmaps
    input_size            int          not null, -- i.e. size of the codelist from all concepts using coding systems with OMOP crossmaps
    output_size           int          not null,
    mapped_count          int          not null,
    mapped_rate           real         not null, -- i.e. % of mapped excluding the codes from coding systems that do not have OMOP crossmaps
    total_rate            real         not null  -- i.e. % of mapped if we include all codes including those that don't have OMOP-mappable coding system(s)
  );

  create unlogged table omop_concept_info(
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    concept_id           int          not null,
    concept_version_id   bigint       not null,
    coding_system_id     int          not null,
    coding_system_name   varchar(64)  not null,
    input_size           int          not null,
    output_size          int          not null,
    mapped_count         int          not null,
    mapped_rate          real         not null,
    unmatched_codes      text[]       not null
  );

  --[!] Create output tables
  drop table if exists omop_concept_result cascade;
  drop table if exists omop_mapping_result cascade;

  create unlogged table omop_concept_result(
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    concept_id           int          not null,
    concept_version_id   bigint       not null,
    omop_id              varchar(64)  not null,
    omop_name            varchar(256) not null,
    omop_vocabulary      varchar(64)  not null,
    omop_code            varchar(64)  not null,
    invalid_reason       varchar(1)   default null,
    origin_codes         text[]       not null,
    origin_system_ids    int[]        not null,
    origin_system_names  text[]       not null
  );

  create unlogged table omop_mapping_result(
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    omop_id              varchar(64)  not null,
    omop_name            varchar(256) not null,
    omop_vocabulary      varchar(64)  not null,
    omop_code            varchar(64)  not null,
    invalid_reason       varchar(1)   default null,
    origin_codes         text[]       not null,
    origin_system_ids    int[]        not null,
    origin_system_names  text[]       not null
  );

  --[!] Build initial mapping
  insert
    into omop_init_match (
      phenotype_id,
      phenotype_version_id,
      concept_id,
      concept_version_id,
      omop_id,
      omop_name,
      omop_vocabulary,
      omop_code,
      invalid_reason,
      origin_code,
      origin_system_id,
      origin_system_name
    )
  select
      phenotype.phenotype_id,
      phenotype.phenotype_version_id,
      phenotype.concept_id,
      phenotype.concept_version_id,
      concept.code as omop_id,
      concept.description as omop_name,
      concept.vocabulary_name as omop_vocabulary,
      concept.vocabulary_code as omop_code,
      concept.invalid_reason,
      phenotype.code as origin_code,
      phenotype.coding_system_id as origin_system_id,
      phenotype.coding_system_name as origin_system_name
    from public.entity_codelists as phenotype
    join coding_lookup as lookup
      on phenotype.coding_system_id = any(lookup.in_coding)
    join public.clinicalcode_omop_codes as concept
      on concept.vocabulary_code = phenotype.code
     and concept.coding_system_id = any(lookup.out_coding);

  --[!] Build standardised & upgraded mapping
  with
    standardised as (
      select
          mappable.phenotype_id,
          mappable.phenotype_version_id,
          mappable.concept_id,
          mappable.concept_version_id,
          concept.code as omop_id,
          concept.description as omop_name,
          concept.vocabulary_name as omop_vocabulary,
          concept.vocabulary_code as omop_code,
          concept.invalid_reason,
          mappable.origin_code,
          mappable.origin_system_id,
          mappable.origin_system_name,
          mappable.omop_id as replacement_id
        from omop_init_match as mappable
        join public.clinicalcode_omoprelationships as relationships
          on relationships.code0_id = mappable.omop_id
         and relationships.relationship = 'Maps to'
         and (relationships.invalid_reason is null or relationships.invalid_reason = '')
        join public.clinicalcode_omop_codes as concept
          on concept.code = relationships.code1_id
         and concept.vocabulary_name = 'SNOMED'
         and (concept.invalid_reason is null or concept.invalid_reason = '')
    ),
    upgradable as (
      select
          standardised.phenotype_id,
          standardised.phenotype_version_id,
          standardised.concept_id,
          standardised.concept_version_id,
          standardised.omop_id,
          standardised.omop_name,
          standardised.omop_vocabulary,
          standardised.omop_code,
          standardised.invalid_reason,
          standardised.origin_code,
          standardised.origin_system_id,
          standardised.origin_system_name
        from standardised
       union all
      select mappable.*
        from omop_init_match as mappable
        left join standardised
          on mappable.omop_id = standardised.replacement_id
       where standardised.omop_id is null
    ),
    replacements as (
      select
          upgradable.phenotype_id,
          upgradable.phenotype_version_id,
          upgradable.concept_id,
          upgradable.concept_version_id,
          concept.code as omop_id,
          concept.description as omop_name,
          concept.vocabulary_name as omop_vocabulary,
          concept.vocabulary_code as omop_code,
          concept.invalid_reason,
          upgradable.origin_code,
          upgradable.origin_system_id,
          upgradable.origin_system_name,
          upgradable.omop_id as replacement_id
        from upgradable
        join public.clinicalcode_omoprelationships as relationships
          on relationships.code0_id = upgradable.omop_id
         and (relationships.invalid_reason is null or relationships.invalid_reason = '')
         and regexp_like(relationships.relationship, '.*(Maps to|replaced by|was_a to|alt_to to).*')
        join public.clinicalcode_omop_codes as concept
          on concept.code = relationships.code1_id
         and (concept.invalid_reason is null or concept.invalid_reason = '')
       where upgradable.invalid_reason = 'U'
          or upgradable.invalid_reason = 'D'
    )
    insert
      into omop_best_match (
        phenotype_id,
        phenotype_version_id,
        concept_id,
        concept_version_id,
        omop_id,
        omop_name,
        omop_vocabulary,
        omop_code,
        invalid_reason,
        origin_code,
        origin_system_id,
        origin_system_name
      )
    select
        replacements.phenotype_id,
        replacements.phenotype_version_id,
        replacements.concept_id,
        replacements.concept_version_id,
        replacements.omop_id,
        replacements.omop_name,
        replacements.omop_vocabulary,
        replacements.omop_code,
        replacements.invalid_reason,
        replacements.origin_code,
        replacements.origin_system_id,
        replacements.origin_system_name
      from replacements
     union all
    select upgradable.*
      from upgradable
      left join replacements
        on upgradable.omop_id = replacements.replacement_id
     where replacements.omop_id is null;

  --[!] Build concept output
  with
    grouped as (
      select 
          best.phenotype_id,
          best.phenotype_version_id,
          best.concept_id,
          best.concept_version_id,
          best.omop_id,
          array_agg(distinct best.origin_code) as origin_codes,
          array_agg(distinct best.origin_system_id) as origin_system_ids,
          array_agg(distinct best.origin_system_name) as origin_system_names
        from omop_best_match as best
       group by best.phenotype_id,
                best.phenotype_version_id,
                best.concept_id,
                best.concept_version_id,
                best.omop_id
    )
  insert
    into omop_concept_result (
      phenotype_id,
      phenotype_version_id,
      concept_id,
      concept_version_id,
      omop_id,
      omop_name,
      omop_vocabulary,
      omop_code,
      invalid_reason,
      origin_codes,
      origin_system_ids,
      origin_system_names
    )
  select
      grouped.phenotype_id,
      grouped.phenotype_version_id,
      grouped.concept_id,
      grouped.concept_version_id,
      concept.code as omop_id,
      concept.description as omop_name,
      concept.vocabulary_name as omop_vocabulary,
      concept.vocabulary_code as omop_code,
      concept.invalid_reason,
      grouped.origin_codes,
      grouped.origin_system_ids,
      grouped.origin_system_names
    from grouped
    join public.clinicalcode_omop_codes as concept
      on grouped.omop_id = concept.code;

  --[!] Build final output
  with
    grouped as (
      select 
          best.phenotype_id,
          best.phenotype_version_id,
          best.omop_id,
          array_agg(distinct best.origin_code) as origin_codes,
          array_agg(distinct best.origin_system_id) as origin_system_ids,
          array_agg(distinct best.origin_system_name) as origin_system_names
        from omop_best_match as best
       group by best.phenotype_id,
                best.phenotype_version_id,
                best.omop_id
    )
  insert
    into omop_mapping_result (
      phenotype_id,
      phenotype_version_id,
      omop_id,
      omop_name,
      omop_vocabulary,
      omop_code,
      invalid_reason,
      origin_codes,
      origin_system_ids,
      origin_system_names
    )
  select
      grouped.phenotype_id,
      grouped.phenotype_version_id,
      concept.code as omop_id,
      concept.description as omop_name,
      concept.vocabulary_name as omop_vocabulary,
      concept.vocabulary_code as omop_code,
      concept.invalid_reason,
      grouped.origin_codes,
      grouped.origin_system_ids,
      grouped.origin_system_names
    from grouped
    join public.clinicalcode_omop_codes as concept
      on grouped.omop_id = concept.code;

  --[!] Compute concept map stats
  with
    input_cnt as (
      select 
          phenotype_id,
          phenotype_version_id,
          concept_id,
          concept_version_id,
          coding_system_id,
          coding_system_name,
          count(*) as input_size
        from public.entity_codelists
       group by phenotype_id, phenotype_version_id, concept_id, concept_version_id, coding_system_id, coding_system_name
    ),
    output_cnt as (
      select
          phenotype_id,
          phenotype_version_id,
          concept_id,
          concept_version_id,
          count(*) as output_size
        from public.omop_concept_result
       group by phenotype_id, phenotype_version_id, concept_id, concept_version_id
    ),
    mapped_cnt as (
      select
          entity.phenotype_id,
          entity.phenotype_version_id,
          entity.concept_id,
          entity.concept_version_id,
          count(distinct code) as mapped_count
        from public.entity_codelists as entity
        join omop_best_match as mapped
          on entity.phenotype_id = mapped.phenotype_id
         and entity.phenotype_version_id = mapped.phenotype_version_id
         and entity.concept_id = mapped.concept_id
         and entity.concept_version_id = mapped.concept_version_id
         and entity.code = mapped.origin_code
       group by entity.phenotype_id, entity.phenotype_version_id, entity.concept_id, entity.concept_version_id
    ),
    unmapped as (
      select
          entity.phenotype_id,
          entity.phenotype_version_id,
          entity.concept_id,
          entity.concept_version_id,
          array_agg(distinct entity.code) as unmatched_codes
        from public.entity_codelists as entity
        left join omop_best_match as mapped
          on entity.phenotype_id = mapped.phenotype_id
         and entity.phenotype_version_id = mapped.phenotype_version_id
         and entity.concept_id = mapped.concept_id
         and entity.concept_version_id = mapped.concept_version_id
         and entity.code = mapped.origin_code
       where mapped.phenotype_id is null
       group by entity.phenotype_id, entity.phenotype_version_id, entity.concept_id, entity.concept_version_id
    ),
    info as (
      select
          input_cnt.phenotype_id,
          input_cnt.phenotype_version_id,
          input_cnt.concept_id,
          input_cnt.concept_version_id,
          input_cnt.coding_system_id,
          input_cnt.coding_system_name,
          input_cnt.input_size,
          coalesce(output_cnt.output_size, 0) as output_size,
          coalesce(mapped_cnt.mapped_count, 0) as mapped_count,
          coalesce(unmapped.unmatched_codes, '{}'::text[]) as unmatched_codes
        from input_cnt
        left join output_cnt
          using (phenotype_id, phenotype_version_id, concept_id, concept_version_id)
        left join mapped_cnt
          using (phenotype_id, phenotype_version_id, concept_id, concept_version_id)
        left join unmapped
          using (phenotype_id, phenotype_version_id, concept_id, concept_version_id)
    )
  insert
    into omop_concept_info(
      phenotype_id,
      phenotype_version_id,
      concept_id,
      concept_version_id,
      coding_system_id,
      coding_system_name,
      input_size,
      output_size,
      mapped_count,
      mapped_rate,
      unmatched_codes
    )
  select
      info.phenotype_id,
      info.phenotype_version_id,
      info.concept_id,
      info.concept_version_id,
      info.coding_system_id,
      info.coding_system_name,
      info.input_size,
      info.output_size,
      info.mapped_count,
      100.0*(info.mapped_count::float / info.input_size::float) as mapped_rate,
      info.unmatched_codes
    from info;

  --[!] Compute phenotype map stats
  with
    counts as (
      select 
          phenotype_id,
          phenotype_version_id,
          array_agg(distinct coding_system_id) as coding_system_ids,
          array_agg(distinct coding_system_name) as coding_system_names,
          count(distinct coding_system_id) as coding_system_count,
          array_agg(
            case
              when coding_system_id in (4,5,7,9,12,15,17,23,24,25,26) then coding_system_id
              else null
            end
          ) as mapped_systems,
          count(*) as total_size,
          sum(
            case
              when coding_system_id in (4,5,7,9,12,15,17,23,24,25,26) then 1
              else 0
            end
          ) as input_size
        from public.entity_codelists as entity
       group by phenotype_id, phenotype_version_id
    ),
    inputs as (
      select
          counts.phenotype_id,
          counts.phenotype_version_id,
          counts.coding_system_ids,
          counts.coding_system_names,
          counts.coding_system_count,
          array_remove(array(select distinct e from unnest(counts.mapped_systems) as a(e)), null) as mapped_systems,
          counts.total_size,
          counts.input_size
        from counts
    ),
    output_cnt as (
      select
          phenotype_id,
          phenotype_version_id,
          count(*) as output_size
        from public.omop_mapping_result
       group by phenotype_id, phenotype_version_id
    ),
    mapped_cnt as (
      select
          entity.phenotype_id,
          entity.phenotype_version_id,
          count(distinct code) as mapped_count
        from public.entity_codelists as entity
        join omop_best_match as mapped
          on entity.phenotype_id = mapped.phenotype_id
         and entity.phenotype_version_id = mapped.phenotype_version_id
         and entity.code = mapped.origin_code
       group by entity.phenotype_id, entity.phenotype_version_id
    ),
    info as (
      select
          inputs.phenotype_id,
          inputs.phenotype_version_id,
          inputs.coding_system_ids,
          inputs.coding_system_names,
          coalesce(inputs.coding_system_count, 0) as coding_system_count,
          coalesce(array_length(inputs.mapped_systems, 1), 0) as mapped_system_count,
          case
            when coalesce(inputs.coding_system_count, 0) > 0 then 100.0*(coalesce(array_length(inputs.mapped_systems, 1), 0)::float / inputs.coding_system_count::float)
            else 0
          end as mapped_system_rate,
          coalesce(inputs.total_size, 0) as total_size,
          coalesce(inputs.input_size, 0) as input_size,
          coalesce(output_cnt.output_size, 0) as output_size,
          coalesce(mapped_cnt.mapped_count, 0) as mapped_count,
          case
            when coalesce(inputs.input_size, 0) > 0 then 100.0*(coalesce(mapped_cnt.mapped_count, 0)::float / coalesce(inputs.input_size, 0)::float)
            else 0
          end as mapped_rate,
          case
            when coalesce(inputs.total_size, 0) > 0 then 100.0*(coalesce(mapped_cnt.mapped_count, 0)::float / coalesce(inputs.total_size, 0)::float)
            else 0
          end as total_rate
        from inputs
        left join output_cnt
          using (phenotype_id, phenotype_version_id)
        left join mapped_cnt
          using (phenotype_id, phenotype_version_id)
    )
  insert
    into omop_phenotype_info(
      phenotype_id,
      phenotype_version_id,
      coding_system_ids,
      coding_system_names,
      coding_system_count,
      mapped_system_count,
      mapped_system_rate,
      total_size,
      input_size,
      output_size,
      mapped_count,
      mapped_rate,
      total_rate
    )
  select
      phenotype_id,
      phenotype_version_id,
      coding_system_ids,
      coding_system_names,
      coding_system_count,
      mapped_system_count,
      mapped_system_rate,
      total_size,
      input_size,
      output_size,
      mapped_count,
      mapped_rate,
      total_rate
    from info;

  --[!] Compute & resolve total resultset
  open _cursor for
    select
      (
        select count(*)
          from omop_phenotype_info as info
      ) as phenotype_count,
      (
        select count(*)
          from omop_phenotype_info as info
         where info.mapped_system_rate > 0 and info.total_size > 0
      ) as mapped_count,
      (
        select 100.0*(t.mappable::float / t.total::float)
        from (
          select
              sum(
                case
                  when info.mapped_system_rate > 0 and info.total_size > 0 then 1
                  else 0
                end
              ) as mappable,
              count(*) as total
          from omop_phenotype_info as info
        ) t
      ) as map_rate,
      (
        select avg(info.mapped_rate)
          from omop_phenotype_info as info
      ) as average_incl_map_rate,
      (
        select avg(info.total_rate)
          from omop_phenotype_info as info
      ) as average_excl_map_rate;
end;
$tx$ language plpgsql;
fetch all from _cursor;


--[!] <Ignore> Misc.
/*
select *
  into _rec
  from omop_mapping_result
  limit 1;

raise notice '%', to_json(_rec);

-- for _rec in (
--   select coding_system_id as coding_id, coding_system_name as coding_name
--     from public.entity_codelists
--    group by coding_system_id, coding_system_name
-- )
-- loop
--   raise notice 'CodingSystem<id: %, name: %>', _rec.coding_id, _rec.coding_name;
-- end loop;
*/
