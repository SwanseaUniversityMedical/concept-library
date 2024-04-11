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
        && array[13]
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
  )

select
	   phenotype_id,
     phenotype_name,
	   string_agg(distinct coding_system_name, ', ') as coding_systems,
     string_agg(distinct code, ', ') as codes
  from codelists as codelist
 group by phenotype_id, phenotype_name
 order by cast(regexp_replace(phenotype_id, '[a-zA-Z]+', '') as integer) asc
