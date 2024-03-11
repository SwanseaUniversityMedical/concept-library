with
  entities as (
    select entity.id as id,
           entity.history_id as version_id,
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
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
  )


-------------------------------------------------------------

-- Det. codelist size across all concepts of phenotype

select phenotype_id,
       phenotype_version_id,
       count(distinct concept_id) as concept_len,
       count(code) as code_len
  from codelists
 group by phenotype_id,
          phenotype_version_id
 order by count(code) desc;


-------------------------------------------------------------

-- Det. codelist size for each concept in each phenotype

select phenotype_id,
       phenotype_version_id,
       concept_id,
       concept_version_id,
       count(code) as code_len
  from codelists
 group by phenotype_id,
         phenotype_version_id,
         concept_id,
         concept_version_id
 order by count(code) desc;


-------------------------------------------------------------

-- Assess specific phenotypes and their concept(s)

with
    concept as (
		select distinct on (1)
		       id as concept_id,
		       history_id as concept_version_id,
		       *
		  from public.clinicalcode_historicalconcept
		 where id = 3313
		 order by 1, 2 desc
		 limit 1
	),
	components as (
		select distinct on (1)
			   c0.id,
			   c0.history_id,
		       entity.history_date as history_date
		  from concept as entity
		  join public.clinicalcode_historicalcomponent as c0
		    on c0.concept_id = entity.concept_id
		   and c0.history_date <= entity.history_date
		  left join public.clinicalcode_historicalcomponent as c1
			on c1.id = c0.id
		   and c1.concept_id = entity.id
		   and c1.history_date <= entity.history_date
		   and c1.history_type = '-'
		 where c0.history_type <> '-'
		   and c1.id is null
		 order by 1
	),
	codelist as (
		select code.id,
			   code.code,
			   code.description
		  from components as component
		  join public.clinicalcode_historicalcodelist as codelist
		    on codelist.component_id = component.id
		   and codelist.history_date <= component.history_date
		   and codelist.history_type <> '-'
		  join public.clinicalcode_historicalcode as code
			on code.code_list_id = codelist.id
		   and code.history_date <= component.history_date
		  left join public.clinicalcode_historicalcode as deletedcode
			on deletedcode.id = code.id
		   and deletedcode.code_list_id = codelist.id
		   and deletedcode.history_date <= component.history_date
		   and deletedcode.history_type = '-'
		 where code.history_type <> '-'
		   and deletedcode.id is null
	)

select component.id,
       component.history_id,
       count(code) as code_len
  from components as component
  join public.clinicalcode_historicalcodelist as codelist
    on codelist.component_id = component.id
  join public.clinicalcode_historicalcode as code
    on code.code_list_id = codelist.id
   and code.history_date <= component.history_date
 group by component.id,
          component.history_id
 order by count(code) desc;

