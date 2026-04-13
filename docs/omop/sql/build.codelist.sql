do $tx$
begin
  --[!] Drop table if exists
  if exists(
    select 1
      from information_schema.tables
    where table_schema = 'public'
      and table_name in ('entity_codelists')
  ) then
    drop table if exists public.entity_codelists cascade;
  end if;

  --[!] Create temp tables
  raise notice '[Codelist::<BEGIN>] Table creation';

  create temp table components (
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    phenotype_name       varchar(255) not null,
    concept_id           bigint       not null,
    concept_version_id   bigint       not null,
    concept_history_date timestamptz  not null,
    concept_name         varchar(255) not null,
    component_id         bigint       not null,
    component_history_id bigint       not null,
    logical_type         integer      not null,
    codelist_id          bigint       not null,
    codelist_history_id  bigint       not null,
    coding_system_id     bigint       not null,
    coding_system_name   varchar(255) not null,
    code_id              bigint       not null,
    code                 varchar(255) not null,
    description          text         not null default ''
  );

  --[!] Create output table
  create unlogged table public.entity_codelists (
    id                   bigint       not null,
    phenotype_id         varchar(50)  not null,
    phenotype_version_id bigint       not null,
    phenotype_name       varchar(255) not null,
    concept_id           bigint       not null,
    concept_version_id   bigint       not null,
    concept_name         varchar(255) not null,
    coding_system_id     bigint       not null,
    coding_system_name   varchar(255) not null,
    code                 varchar(255) not null,
    description          text         not null default ''
  );

  raise notice '[Codelist::<COMPLETE>] Table creation';

  --[!] Build component list
  raise notice '[Codelist::<BEGIN>] Component creation';

  with entities as (
    select entity.id as id,
           entity.history_id as version_id,
		   entity.name,
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where (entity.is_deleted is null or entity.is_deleted = false)
       and entity.template_data::jsonb ? 'concept_information'
       and json_typeof(entity.template_data::json->'concept_information') = 'array'
       and json_array_length(entity.template_data::json->'concept_information') > 0
  )
  insert into components (
    phenotype_id,
    phenotype_version_id,
    phenotype_name,
    concept_id,
    concept_version_id,
    concept_history_date,
    concept_name,
    component_id,
    component_history_id,
    logical_type,
    codelist_id,
    codelist_history_id,
    coding_system_id,
    coding_system_name,
    code_id,
    code,
    description
  )
    select entity.id as phenotype_id,
           entity.version_id as phenotype_version_id,
           entity.name as phenotype_name,
           concept.id as concept_id,
           max(concept.history_id) as concept_version_id,
           concept.history_date as concept_history_date,
           concept.name as concept_name,
           component.id as component_id,
           max(component.history_id) as component_history_id,
           component.logical_type as logical_type,
           codelist.id as codelist_id,
           max(codelist.history_id) as codelist_history_id,
           concept.coding_system_id as coding_system_id,
           coding.name as coding_system_name,
           codes.id as code_id,
           codes.code,
           codes.description
      from entities as entity
      join public.clinicalcode_historicalconcept as concept
        on concept.id = entity.concept_id
       and concept.history_id = entity.concept_version_id
      join public.clinicalcode_codingsystem as coding
        on coding.id = concept.coding_system_id
      join public.clinicalcode_historicalcomponent as component
        on component.concept_id = concept.id
       and component.history_date <= concept.history_date
       and component.history_type <> '-'
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
       and codes.history_type <> '-'
     where deleted_component.id is null
     group by entity.id,
              entity.version_id,
              entity.name,
              concept.id,
              concept.history_id,
              concept.history_date,
              concept.name,
              component.id, 
              component.logical_type, 
              codelist.id,
              concept.coding_system_id,
              coding.name,
              codes.id,
              codes.code,
              codes.description;

  raise notice '[Codelist::<COMPLETE>] Component creation';

  --[!] Build codelist
  raise notice '[Codelist::<BEGIN>] Codelist creation';

  with codesets as (
    select included_codes.*,
           row_number() over (
             partition by included_codes.phenotype_id,
                          included_codes.phenotype_version_id,
                          included_codes.concept_id,
                          included_codes.concept_version_id,
                          included_codes.code
                 order by included_codes.code_id desc
           ) as rn
      from components as included_codes
      left join components as excluded_codes
        on excluded_codes.phenotype_id = included_codes.phenotype_id
       and excluded_codes.phenotype_version_id = included_codes.phenotype_version_id
       and excluded_codes.concept_id = included_codes.concept_version_id
       and excluded_codes.concept_version_id = included_codes.concept_version_id
       and excluded_codes.code = included_codes.code
       and excluded_codes.logical_type = 2
     where included_codes.logical_type = 1
       and excluded_codes.code is null
  )
  insert into public.entity_codelists (
    id,
    phenotype_id,
    phenotype_version_id,
    phenotype_name,
    concept_id,
    concept_version_id,
    concept_name,
    coding_system_id,
    coding_system_name,
    code,
    description
  )
    select row_number() over (
             order by regexp_replace(phenotype_id::text, '[a-zA-Z]+', '')::int asc,
                      phenotype_version_id asc,
                      concept_id asc,
                      concept_version_id asc,
                      code desc
           ) as id,
           phenotype_id,
           phenotype_version_id,
           phenotype_name,
           concept_id,
           concept_version_id,
           concept_name,
           coding_system_id,
           coding_system_name,
           code,
           description
      from codesets
     where rn = 1;

  raise notice '[Codelist::<COMPLETE>] Codelist creation';

  --[!] Clean temp tables
  drop table if exists components;
end;
$tx$ language plpgsql;
