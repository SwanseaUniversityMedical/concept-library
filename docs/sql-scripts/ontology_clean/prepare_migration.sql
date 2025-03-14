-- 1. Find invalid migration(s)
select *
  from public.django_migrations;


-- 2. Delete invalid migration(s)
delete from public.django_migrations
 where substring(name, '^0(\d+)')::int >= 113 and id >= 167;


-- 3. Delete legacy trigger(s)
drop trigger if exists ge_search_vec_tr on public.clinicalcode_genericentity;

drop trigger if exists hge_search_vec_tr on public.clinicalcode_historicalgenericentity;


-- 4. Clear references to legacy ontology tags on GenericEntity
with
  entities as (
    select
           entity.id,
           entity.template_data,
           array(select jsonb_array_elements(entity.template_data->'ontology'))::int[] as ontology_ids
      from public.clinicalcode_genericentity as entity
     where entity.template_data is not null
       and entity.template_data ? 'ontology'
       and jsonb_typeof(entity.template_data->'ontology') = 'array'
       and jsonb_array_length(entity.template_data->'ontology') > 0
  ),
  cleaned as (
    select
          src.*,
          src.template_data #- '{ontology}' as cleaned_data
      from entities as src
  )
update public.clinicalcode_genericentity as trg
   set template_data = src.cleaned_data
  from cleaned as src
 where trg.id = src.id;


-- 6. Clear references to legacy ontology tags on HistoricalGenericEntity
with
  entities as (
    select
           entity.id,
           entity.template_data,
           array(select jsonb_array_elements(entity.template_data->'ontology'))::int[] as ontology_ids
      from public.clinicalcode_historicalgenericentity as entity
     where entity.template_data is not null
       and entity.template_data ? 'ontology'
       and jsonb_typeof(entity.template_data->'ontology') = 'array'
       and jsonb_array_length(entity.template_data->'ontology') > 0
  ),
  cleaned as (
    select
          src.*,
          src.template_data #- '{ontology}' as cleaned_data
      from entities as src
  )
update public.clinicalcode_historicalgenericentity as trg
   set template_data = src.cleaned_data
  from cleaned as src
 where trg.id = src.id;


-- 7. Drop legacy ontology tables
drop table public.clinicalcode_ontologytag cascade;

drop table public.clinicalcode_ontologytagedge cascade;

