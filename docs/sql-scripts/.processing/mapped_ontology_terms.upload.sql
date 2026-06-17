--> Upload mapped Phenotype-Ontology
create temp table tmp_onts(
  id             varchar(50) not null,
  ontology_label text        default '',
  ontology_id    varchar(64) not null
);

copy tmp_onts(
  id,
  ontology_label,
  ontology_id
)
 from '/path/to/resultset.out.csv'
 with (
    FORMAT csv,
    DELIMITER ',',
    HEADER,
    ENCODING 'UTF8',
    QUOTE '"',
    ESCAPE '"'
  );

--> Push changes to entities
--[!] Note: somewhat slow due to trigger
with
  idents as (
    select
        t0.id,
        t1.id as ontology_id
      from tmp_onts t0
      join public.clinicalcode_ontologytag t1
        on t1.reference_id = upper(t0.ontology_id)
  ),
  onts as (
    select
        id,
        jsonb_agg(ontology_id) as ontology_ids
      from idents
     group by id
  )
update public.clinicalcode_genericentity as trg
   set template_data['ontology'] = src.ontology_ids
  from onts as src
 where trg.id = src.id;

--> Push changes to historical versions
--[!] Note: somewhat slow due to trigger
update public.clinicalcode_historicalgenericentity as trg
   set template_data['ontology'] = src.template_data->'ontology'
  from public.clinicalcode_genericentity as src
 where trg.id = src.id
   and jsonb_typeof(src.template_data->'ontology') = 'array'
   and jsonb_array_length(src.template_data->'ontology') > 0;

--> Drop temp. table
drop table tmp_onts;
