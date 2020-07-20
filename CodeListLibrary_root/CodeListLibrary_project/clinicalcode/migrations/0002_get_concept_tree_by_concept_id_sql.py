# -*- coding: utf-8 -*-
# Modified by: Pete Arnold
from __future__ import unicode_literals

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL("""
            DO $$
			BEGIN
-- --------------------------------------------------------------------------
-- get_concept_tree_by_concept_id
-- modified: Pete Arnold
--           14eg mis Tachwedd 2018

-- Add the function manually with:
--    return:     TABLE(code character varying, description character varying)
--    parameter:    IN root_concept_id integer
--    language:    plpgsql
--    options:    VOLATILE
--                Returns set - yes
--                Estimated cost - 100
--                Estimated rows - 1000
-- ----------------------------------------------------------------------------
-- recursive queries to get all included and excluded codes for a root concept and its children
-- we then return all inclusive codes minus any codes marked to be excluded
-- inclusion logical_type = 1, exclusion logical_type = 2
-- concept component type = 1, code list component type = 2, regex component type = 3
-- Note that the return parameter is labelled concept_idx rather than
-- concept_id. This was necessitated by the confusion:
--    ERROR:  column reference "concept_id" is ambiguous
--    LINE 9:     array[concept_id] AS all_parents, c.is_deleted
--                      ^
--    DETAIL:  It could refer to either a PL/pgSQL variable or a table column.
-- ----------------------------------------------------------------------------

--DROP FUNCTION public.get_concept_tree_by_concept_id(INTEGER);

CREATE OR REPLACE FUNCTION 
    public.get_concept_tree_by_concept_id(IN root_concept_id INTEGER)
    RETURNS TABLE(concept_name CHARACTER VARYING, component_name CHARACTER VARYING,
        concept_ref_id INTEGER, concept_idx INTEGER, logical_type INTEGER,
        component_type INTEGER, level_depth INTEGER, parents_list INTEGER[])
    LANGUAGE plpgsql VOLATILE
    COST 100
    ROWS 1000
    AS
$BODY$
DECLARE 
    max_depth INT := 0;
BEGIN
    DROP TABLE IF EXISTS ConceptTree;
    CREATE TEMPORARY TABLE ConceptTree
    (
        concept_name VARCHAR(500),
        component_name VARCHAR(500),
        concept_ref_id INT NULL,
        concept_id INT,
        logical_type INT,
        component_type INT,
        level_depth INT,
        is_deleted BOOLEAN,
        all_parents INT[]
        --, is_leaf BOOLEAN
    );
    --DROP TABLE IF EXISTS ConceptTreeFinal;
    --CREATE TEMPORARY TABLE ConceptTreeFinal AS
    --    SELECT * 
    --    FROM ConceptTree;
    --ALTER TABLE ConceptTreeFinal DROP is_deleted;
    --ALTER TABLE ConceptTreeFinal DROP is_leaf;
    
    -- Check that the root concept has not been deleted before filling the
    -- table.
    IF (SELECT COUNT(*) 
        FROM clinicalcode_concept c 
        WHERE c.id = root_concept_id AND c.is_deleted IS NOT TRUE) > 0 THEN
        -----------------------------------------------------------------------
        -- Create a table of concepts/components, starting with the root
        -- concept/each of its concept components (ignore non-concept
        -- components), then working through each of these component concepts
        -- and their respective components and so on. Use an array to track
        -- the concepts that are part of each concept's ancestry to avoid
        -- forming any infinite loops.
        -----------------------------------------------------------------------
        WITH RECURSIVE get_concepts(concept_name, component_name, concept_ref_id,
                        concept_id, logical_type, component_type, level_depth,
                        all_parents, is_deleted) AS 
        (
            SELECT  c.name AS concept_name, com.name AS component_name,
                com.concept_ref_id, c.id AS concept_id,
                com.logical_type, com.component_type,
                CASE WHEN com.concept_ref_id IS NULL THEN 0 ELSE 1 END AS level_depth,
                array[concept_id] AS all_parents, c.is_deleted
            FROM clinicalcode_concept c
                LEFT OUTER JOIN clinicalcode_component com ON com.concept_id = c.id
            WHERE c.id = root_concept_id AND c.is_deleted IS NOT TRUE
                AND com.component_type = 1
            UNION ALL
            SELECT  child_items.concept_name, child_items.component_name, 
                child_items.concept_ref_id, child_items.concept_id,
                child_items.logical_type, child_items.component_type,
                parent_items.level_depth + 1 AS level_depth,
                parent_items.all_parents||child_items.concept_id,
                child_items.is_deleted
            FROM (
                SELECT  c.name AS concept_name, com.name AS component_name, 
                    com.concept_ref_id, c.id AS concept_id,
                    com.logical_type, com.component_type,
                    1 AS level_depth, c.is_deleted
                FROM clinicalcode_concept c
                    LEFT OUTER JOIN clinicalcode_component com ON com.concept_id = c.id
                WHERE com.component_type = 1 AND c.is_deleted IS NOT TRUE
            ) AS child_items, get_concepts parent_items
            WHERE child_items.concept_id = parent_items.concept_ref_id
                AND child_items.concept_id <> ALL(parent_items.all_parents)
        )
        INSERT INTO ConceptTree(concept_name, component_name, 
            concept_ref_id, concept_id, logical_type, component_type,
            level_depth, all_parents, is_deleted)
        SELECT  rec.concept_name, rec.component_name, rec.concept_ref_id,
            rec.concept_id, rec.logical_type, rec.component_type,
            rec.level_depth, rec.all_parents, rec.is_deleted
        FROM get_concepts AS rec;

        /* ************************************************************
           Remove the following code as it is not clear what was the
           intended output.
           ************************************************************
        -- Get the maximum depth of the concept table.
        SELECT MAX(c.level_depth) INTO STRICT max_depth FROM ConceptTree c;
        -- Identify the leaf nodes.
        WITH ct AS (
            SELECT ct1.concept_ref_id
            FROM ConceptTree ct1
            WHERE ct1.concept_ref_id NOT IN 
            (SELECT ct2.concept_id FROM ConceptTree ct2)
        )
        UPDATE ConceptTree SET
        is_leaf = TRUE
        FROM ct
        WHERE ct.concept_ref_id = ConceptTree.concept_ref_id;
        -- This is a final view of the concept hierarchy tree including its logical type (include/exclude)
        WITH RECURSIVE whosYourDaddy AS (
            SELECT  c.concept_name, c.component_name, c.concept_ref_id, c.concept_id,
                c.logical_type, c.component_type, c.level_depth 
            FROM ConceptTree c 
            WHERE c.is_leaf IS TRUE AND c.is_deleted IS NOT TRUE
            UNION ALL
            SELECT  c.concept_name, c.component_name, c.concept_ref_id, c.concept_id,
                c.logical_type, c.component_type, c.level_depth 
            FROM ConceptTree c
                JOIN whosYourDaddy ON whosYourDaddy.concept_id = c.concept_ref_id
            WHERE c.is_deleted IS NOT TRUE
        )
        INSERT INTO ConceptTreeFinal(concept_name, component_name,
            concept_ref_id, concept_id, logical_type,
            component_type, level_depth)
        SELECT w.concept_name, w.component_name, w.concept_ref_id,
            w.concept_id, w.logical_type, w.component_type,
            w.level_depth 
        FROM whosYourDaddy w
        GROUP BY w.concept_name, w.component_name, w.concept_ref_id,
            w.concept_id, w.logical_type, w.component_type,
            w.level_depth;
        */
    END IF;
        
    RETURN QUERY SELECT ct.concept_name, ct.component_name, ct.concept_ref_id,
        ct.concept_id, ct.logical_type, ct.component_type, ct.level_depth,
        ct.all_parents
    FROM ConceptTree ct;
END;
$BODY$;
--ALTER FUNCTION public.get_concept_tree_by_concept_id(INTEGER) OWNER TO postgres;
			END
            $$
        """)
    ]
