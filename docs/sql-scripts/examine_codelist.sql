-- Build final code list

with
	concept as (
		select *
			from public.clinicalcode_historicalconcept
		where id = 762
			and history_id = 11409
		order by history_id asc
		limit 1
	),
	component as (
		select concept.id as concept_id,
					concept.history_id as concept_history_id,
					concept.history_date as concept_history_date,
					component.id as component_id,
					max(component.history_id) as component_history_id,
					component.logical_type as logical_type,
					codelist.id as codelist_id,
					max(codelist.history_id) as codelist_history_id,
					codes.id as code_id,
					codes.code,
					codes.description
			from concept as concept
			join public.clinicalcode_historicalcomponent as component
				on component.concept_id = concept.id
			and component.history_date <= concept.history_date
			and component.history_type <> '-'
			left join public.clinicalcode_historicalcomponent as deletedcomponent
				on deletedcomponent.concept_id = concept.id
			and deletedcomponent.id = component.id
			and deletedcomponent.history_date <= concept.history_date
			and deletedcomponent.history_type = '-'
			join public.clinicalcode_historicalcodelist as codelist
				on codelist.component_id = component.id
			and codelist.history_date <= concept.history_date
			and codelist.history_type <> '-'
			join public.clinicalcode_historicalcode as codes
				on codes.code_list_id = codelist.id
			and codes.history_date <= concept.history_date
			and codes.history_type <> '-'
			where deletedcomponent.id is null
			group by concept.id,
							concept.history_id,
							concept.history_date, 
							component.id, 
							component.logical_type, 
							codelist.id,
							codes.id,
							codes.code,
							codes.description
)

select included_codes.*,
       attributes.attributes
  from component as included_codes
  left join component as excluded_codes
    on excluded_codes.code = included_codes.code
   and excluded_codes.logical_type = 2
  left join public.clinicalcode_conceptcodeattribute as attributes
    on attributes.concept_id = included_codes.concept_id
   and attributes.code = included_codes.code
 where included_codes.logical_type = 1
   and excluded_codes.code is null


-------------------------------------------------------------

-- Examine components

select c0.id,
			 c0.history_id
	from public.clinicalcode_historicalcomponent as c0
	join public.clinicalcode_historicalcomponent as c1
		on (
				c1.concept_id = c0.concept_id
				and c1.history_date <= c0.history_date
				and c1.history_type <> '-'
		)
	where c0.concept_id = 714
		and c0.history_date <= '2021-10-06 15:58:47.054569+00'::timestamptz
	group by c0.id, c0.history_id
	order by c0.id asc, c0.history_id desc


-------------------------------------------------------------

-- Derive json_object phenotype-children results

with
  entities as (
    select *
      from public.clinicalcode_historicalgenericentity
     where id = ANY('{PH1586}')
       and history_id = ANY('{2914}')
  ),
  children as (
    select entity.id as parent_id,
           entity.history_id as parent_history_id,
           concept.id as id,
           concept.history_id as history_id,
           concept.name as name,
           codingsystem.id as coding_system,
           codingsystem.name as coding_system_name,
           'C' as prefix,
           'concept' as type,
           'concept_information' as field
      from entities as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
      join public.clinicalcode_historicalconcept as concept
        on concept.id = cast(concepts->>'concept_id' as integer)
       and concept.history_id = cast(concepts->>'concept_version_id' as integer)
      join public.clinicalcode_codingsystem as codingsystem
        on codingsystem.id = concept.coding_system_id
  )

select
  json_agg(
    json_build_object(
      'id', entity.id,
      'history_id', entity.history_id,
      'name', entity.name,
      'author', entity.author,
      'children', child.children_data
    )
  )
  from entities as entity
  left join (
    select parent_id,
           parent_history_id,
           json_agg(json_build_object(
             'id', id,
             'history_id', history_id,
             'name', "name",
             'prefix', prefix,
             'type', "type",
             'field', field
           )) as children_data
      from children
      group by parent_id, parent_history_id
  ) as child
    on entity.id = child.parent_id
   and entity.history_id = child.parent_history_id
