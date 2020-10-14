# -*- coding: utf-8 -*-
# Modified by: Pete Arnold
from __future__ import unicode_literals

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0002_get_concept_tree_by_concept_id_sql'),
    ]

    operations = [
        migrations.RunSQL("""
            DO $$
			BEGIN
-- --------------------------------------------------------------------------
-- get_parent_concept_tree_by_concept_id
-- modified: Pete Arnold
--           18fed mis Ionawr 2019
--
-- Add the function manually with:
--    return:     TABLE(  concept_id INTEGER)
--    parameter:    IN root_concept_id integer
--    language:    plpgsql
--    options:    VOLATILE
--                Returns set - yes
--                Estimated cost - 100
--                Estimated rows - 1000
-- ----------------------------------------------------------------------------
-- Get all the parent concepts that contain (and are thus dependent on changes
-- in) the specified child concept.
-- ----------------------------------------------------------------------------

--DROP FUNCTION public.get_parent_concept_tree_by_concept_id(integer);

CREATE OR REPLACE FUNCTION public.get_parent_concept_tree_by_concept_id(IN root_concept_id INTEGER)
    RETURNS TABLE(
        concept_id INTEGER    -- The list of concepts containing the root.
        )
    LANGUAGE plpgsql VOLATILE
    COST 100
    ROWS 1000
    AS
$BODY$
DECLARE 
    max_depth INT := 0;
BEGIN
    -- The other entries in here have been maintained for debugging purposes.
    -- It is not expected that this will impact performance.
    DROP TABLE IF EXISTS ConceptTree;
    CREATE TEMPORARY TABLE ConceptTree
    (
        concept_id INT,
        concept_name VARCHAR(500),
        concept_parent_id INT NULL,
        concept_path INT[]
    );
    -- Check that the root concept has not been deleted before filling the
    -- table.
    IF (SELECT COUNT(*) 
        FROM clinicalcode_concept c 
        WHERE c.id = root_concept_id AND c.is_deleted IS NOT TRUE) > 0 THEN
        -----------------------------------------------------------------------
        -- Create a table of concepts, starting with the root concept, get all
        -- the components which use this concept (have this as a
        -- concept_ref_id), then working through each of these concepts'
        -- components until there are no more dependencies. Use an array to
        -- track the path through the concepts to avoid forming any infinite
        -- loops.
        -----------------------------------------------------------------------
        WITH RECURSIVE get_concepts(concept_id, concept_name, concept_parent_id,
            concept_path, is_deleted) AS 
        (
            -- Get the root concept.
            SELECT  DISTINCT c.id AS concept_id, c.name AS concept_name, 
                root_concept_id AS concept_parent_id,
                array[c.id] AS concept_path, c.is_deleted
            FROM     clinicalcode_concept c
            WHERE     c.id = root_concept_id AND
                c.is_deleted IS NOT TRUE
            -- Get the parents.
            UNION ALL
            SELECT  parent.concept_id,
                parent.concept_name,
                parent.concept_parent_id,
                child.concept_path||parent.concept_id AS concept_path,
                parent.is_deleted
            FROM (
                SELECT  com.concept_id AS concept_id, ch.name AS concept_name, 
                    com.concept_ref_id AS concept_parent_id,
                    ch.is_deleted
                FROM clinicalcode_component com
                LEFT OUTER JOIN clinicalcode_concept ch
                ON     ch.id = com.concept_id
                WHERE     ch.is_deleted IS NOT TRUE
            ) 
            AS     parent, get_concepts AS child
            WHERE     parent.concept_parent_id = child.concept_id AND
                parent.concept_id <> ALL(child.concept_path)
        )
        INSERT INTO ConceptTree(concept_id, concept_name, concept_parent_id,
            concept_path)
        SELECT  DISTINCT rec.concept_id, rec.concept_name, rec.concept_parent_id,
            rec.concept_path
        FROM get_concepts AS rec;
    END IF;
    -- Just return the ancestor concept numbers.
    RETURN QUERY SELECT 
        DISTINCT ct.concept_id
    FROM ConceptTree ct;
END;
$BODY$;
--ALTER FUNCTION public.get_parent_concept_tree_by_concept_id(INTEGER) OWNER TO postgres;
			END
            $$
        """)
    ]
