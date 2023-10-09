-- Examine concept linkage with parent phenotypes
with
  -- det. first appearance of a Concept in a Phenotype
  split_concepts as (
    select phenotype.id as phenotype_id,
           concept->>'concept_id' as concept_id,
           created
      from public.clinicalcode_phenotype as phenotype,
           json_array_elements(phenotype.concept_informations::json) as concept
  ),
  ranked_concepts as (
    select phenotype_id,
           concept_id,
           rank() over (
             partition by concept_id
             order by created
           ) ranking
      from split_concepts
  ),
  -- count distinct appearances
  counts as (
    select
      (select count(distinct id) from public.clinicalcode_concept) as total_concepts,
      (select count(distinct concept_id) from ranked_concepts) as linked_concepts
  )

-- calc. difference
select total_concepts,
       linked_concepts,
       total_concepts - linked_concepts as diff
  from counts;

-- show unlinked concepts
select id, name, author, owner_id, created, modified, group_id
  from public.clinicalcode_concept
 where (is_deleted is null or is_deleted = false)
   and id not in (
     select concept_id::int from ranked_concepts
   );

-------------------------------------------------------------

-- Update concept's ownership
with
    split_concepts as (
      select phenotype.id as phenotype_id, 
          concept ->> 'concept_id' as concept_id,
          created
        from public.clinicalcode_phenotype as phenotype,
          json_array_elements(phenotype.concept_informations :: json) as concept
    ),
    ranked_concepts as (
        select phenotype_id, concept_id,
          rank() over(
            partition by concept_id
                order by created
          ) ranking
          from split_concepts
    )

update public.clinicalcode_concept as trg
    set phenotype_owner_id = src.phenotype_id
   from (
     select distinct on (concept_id) *
       from ranked_concepts
   ) src
  where (trg.is_deleted is null or trg.is_deleted = false)
    and trg.id = src.concept_id::int;

-------------------------------------------------------------

-- Examine concept linkage after initial linking
with
  counts as (
    select
      (
        select count(id)
          from public.clinicalcode_concept
		     where is_deleted is null or is_deleted = false
      ) as total_concepts,
      (
        select count(*)
          from public.clinicalcode_concept
         where phenotype_owner_id is null and (is_deleted is null or is_deleted = false)
      ) as unlinked_concepts
  )

select total_concepts,
	     total_concepts - unlinked_concepts as linked_concepts,
       unlinked_concepts
  from counts;

-------------------------------------------------------------

-- Select unlinked concepts
select id
  from public.clinicalcode_concept
 where (is_deleted is null or is_deleted = false)
   and phenotype_owner_id is null;

-------------------------------------------------------------

-- Check publish status
select id,
	   concepts
  from (
	  select id,
		       concepts
	    from public.clinicalcode_historicalgenericentity as entity,
		       json_array_elements(entity.template_data::json->'concept_information') as concepts
	   where entity.publish_status = 2
  ) results
 where cast(concepts->>'concept_id' as integer) = 715
   and cast(concepts->>'concept_version_id' as integer) = 2569;

-------------------------------------------------------------

-- Get all accessible concepts (i.e. the ability for a user to view them via permissions)
select distinct on (concept_id)
       id as phenotype_id,
       cast(concepts->>'concept_id' as integer) as concept_id,
       cast(concepts->>'concept_version_id' as integer) as concept_version_id
  from (
    select id,
           concepts
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where 
           (entity.is_deleted is null or entity.is_deleted = false)
           and (
             entity.publish_status = 2
             or (
               exists (
                 select 1
                   from public.auth_user_groups as t
                  where t.user_id = 7 and t.group_id = entity.group_id
               )
               and entity.group_access in (2, 3)
             )
             or entity.owner_id = 7
             or entity.world_access = 2
           )
  ) results
 order by concept_id desc, concept_version_id desc;

-- Get latest accessible Concept available to anonymous users
select *
  from (
    select cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where 
           (entity.is_deleted is null or entity.is_deleted = false)
           and entity.publish_status = 2
           and entity.world_access = 2
     ) results
 where concept_id = 715
 order by concept_version_id desc
 limit 1;

-- Check whether user can access a Concept via associated Phenotypes
select *
  from (
    select distinct on (id)
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where 
           (
             cast(concepts->>'concept_id' as integer) = 715
             and cast(concepts->>'concept_version_id' as integer) = 2569
           )
           and (entity.is_deleted is null or entity.is_deleted = false)
           and (
             entity.publish_status = 2
             or (
               exists (
                 select 1
                   from public.auth_user_groups as t
                  where t.user_id = 7 and t.group_id = entity.group_id
               )
               and entity.group_access in (2, 3)
             )
             or entity.owner_id = 7
             or entity.world_access = 2
           )
  ) results
 limit 1;

-- Check anonymous user access
select *
  from (
    select distinct on (id)
           cast(concepts->>'concept_id' as integer) as concept_id,
           cast(concepts->>'concept_version_id' as integer) as concept_version_id
      from public.clinicalcode_historicalgenericentity as entity,
           json_array_elements(entity.template_data::json->'concept_information') as concepts
     where 
      (
        cast(concepts->>'concept_id' as integer) = 715
        and cast(concepts->>'concept_version_id' as integer) = 2569
      )
      and (entity.is_deleted is null or entity.is_deleted = false)
      and entity.publish_status = 2
  ) results
 limit 1;

-------------------------------------------------------------
