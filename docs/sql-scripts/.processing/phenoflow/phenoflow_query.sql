--> Used to collect all historical records of Phenotypes assoc. with some unique Phenoflow obj
--> See Phenoflow @ https://kclhi.org/phenoflow/

with
  phenoflow_objs as (
    select
          ent.id,
          ent.history_id,
          (ent.template_data::jsonb->>'phenoflowid')::int as phenoflow_id
      from public.clinicalcode_historicalgenericentity as ent
     where ent.template_data::jsonb ? 'phenoflowid'
       and ent.template_data::jsonb->>'phenoflowid' ~ E'^\\d+$'
  ),
  aggregated_objs as (
    select
        ent.phenoflow_id,
        json_agg(json_build_object(
          'id', ent.id,
          'history_id', ent.history_id
        )) as related_phenotypes
      from phenoflow_objs as ent
     group by ent.phenoflow_id
  )
select
    json_agg(json_build_object(
      'phenoflow_id', ent.phenoflow_id,
      'related_phenotypes', ent.related_phenotypes
    )) as results
  from aggregated_objs as ent;
