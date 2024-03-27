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

-- Count concepts that have never had a phenotype_owner
select count(*)
  from public.clinicalcode_historicalconcept as hc
  left join public.clinicalcode_historicalconcept as hci
    on hc.id = hci.id and hc.history_id = hci.history_id
 where hci.id is null;


-- Show unlinked historical concept(s)
with
  /* Show total unlinked, incl. all versions */
  total_counts as (
    select
      (
        select count(*)
          from public.clinicalcode_historicalconcept
         where is_deleted is null or is_deleted = false
      ) as total_concepts,
      (
        select count(*)
          from public.clinicalcode_historicalconcept
         where phenotype_owner_id is null and (is_deleted is null or is_deleted = false)
      ) as unlinked_concepts
  ),
  /* Show counts by each entity (id) */
  entity_counts as (
    select
      (
        select count(*)
          from (
            select id
              from public.clinicalcode_historicalconcept
             where is_deleted is null or is_deleted = false
             group by id
          ) hci
      ) as total_concepts,
      (
        select count(*)
          from (
            select id, phenotype_owner_id
              from public.clinicalcode_historicalconcept
             where phenotype_owner_id is null and (is_deleted is null or is_deleted = false)
             group by id, phenotype_owner_id
          ) hcid
      ) as unlinked_concepts
  )

select total_concepts,
       total_concepts - unlinked_concepts as linked_concepts,
       unlinked_concepts
  from entity_counts;


-- Find phenotypes that incl. historical concepts that don't have a phenotype_owner
select entity.phenotype_id,
       entity.phenotype_version_id,
       entity.concept_id,
       entity.concept_version_id
  from (
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
         where template_id = 1
           and json_array_length(entity.template_data::json->'concept_information') > 0
      ) results
  ) as entity
  left join public.clinicalcode_historicalconcept as concept
    on (
      entity.concept_id = concept.id
      and entity.concept_version_id = concept.history_id
    )
 where concept.phenotype_owner_id is null


-- Find possible links
with 
  unlinked_concepts as (
    select *
      from public.clinicalcode_historicalconcept
     where phenotype_owner_id is null
  ),
  entity_children as (
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
         where template_id = 1
           and json_array_length(entity.template_data::json->'concept_information') > 0
      ) hge_concepts
  )

select cast(regexp_replace(entity.phenotype_id, '[a-zA-Z]+', '') as integer) as true_id,
       entity.phenotype_id,
       entity.phenotype_version_id,
       entity.concept_id,
       entity.concept_version_id
  from unlinked_concepts as concept
  join entity_children as entity
    on entity.concept_id = concept.id and entity.concept_version_id = concept.history_id
  order by true_id, entity.concept_id


-- Update all historical records of a concept, such that:
-- 
--    it's phenotype_owner_id reflects the phenotype_id
--    in which it was first present
-- 

/* Update from legacy reference first ... */
with
  legacy_reference as (
    select phenotype.id as phenotype_id,
           concept->>'concept_id' as concept_id,
           concept->>'concept_version_id' as concept_version_id,
           created
      from public.clinicalcode_phenotype as phenotype,
           json_array_elements(phenotype.concept_informations::json) as concept
  ),
  ranked_legacy_concepts as (
    select phenotype_id,
           cast(concept_id as integer) as concept_id,
           cast(concept_version_id as integer) as concept_version_id,
           rank() over (
             partition by phenotype_id
                 order by created asc
           ) as ranking
      from legacy_reference
  )

update public.clinicalcode_historicalconcept as trg
   set phenotype_owner_id = src.phenotype_id
  from (
    select *
      from ranked_legacy_concepts
     where ranking = 1
  ) as src
 where trg.id = src.concept_id
   and trg.phenotype_owner_id is null;

/* ... then update from current reference */
with
  entity_reference as (
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
         where template_id = 1
           and json_array_length(entity.template_data::json->'concept_information') > 0
      ) hge_concepts
  ),
  first_child_concept as (
    select concept_id as concept_id,
           min(concept_version_id) as concept_version_id
      from entity_reference as entity
     group by concept_id
  ),
  earliest_entity as (
    select phenotype_id,
           concept_id,
           concept_version_id
      from (
        select phenotype_id,
              rank() over (
                partition by phenotype_id
                    order by phenotype_version_id asc
              ) as ranking,
              concept.concept_id,
              concept.concept_version_id
          from entity_reference as entity
          join first_child_concept as concept
            using (concept_id, concept_version_id)
      ) as hci
     where ranking = 1
  )

update public.clinicalcode_historicalconcept as trg
   set phenotype_owner_id = src.phenotype_id
  from earliest_entity as src
 where trg.id = src.concept_id
   and trg.phenotype_owner_id is null;


-------------------------------------------------------------

-- get latest version of the phenotype owner from a concept

with
  phenotype_children as (
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
           and id = %(phenotype_id)s
      ) hge_concepts
     where (concepts->>'concept_id')::int = %(concept_id)s
  ),
  priorities as (
    select t1.*, 1 as sel_priority
      from phenotype_children as t1
     where t1.concept_version_id = %(concept_version_id)s
     union all
    select t2.*, 2 as sel_priority
      from phenotype_children as t2
  ),
  sorted_ref as (
    select phenotype_id,
           phenotype_version_id,
           concept_id,
           concept_version_id,
           row_number() over (
             partition by concept_version_id
                 order by sel_priority
           ) as reference
      from priorities
  )

select phenotype_id,
       max(phenotype_version_id) as phenotype_version_id
  from (
    select *
      from sorted_ref
     where reference = 1
  ) as pheno
  join public.clinicalcode_historicalgenericentity as entity
    on pheno.phenotype_id = entity.id
    and pheno.phenotype_version_id = entity.history_id
 group by phenotype_id;
