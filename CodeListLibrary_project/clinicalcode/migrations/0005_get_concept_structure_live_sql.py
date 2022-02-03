# -*- coding: utf-8 -*-



from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0004_concept_unique_codes_sql'),
    ]

    operations = [
        migrations.RunSQL("""
            DO $$
			BEGIN
			
-- ===========================================================================
-- Function: public.get_concept_structure_Live(integer)

-- Returns concept_component_structure
                                        
-- created: Muhammad Elmessary
--           21/02/2020

--DROP FUNCTION public.get_concept_structure_Live(integer);



CREATE OR REPLACE FUNCTION public.get_concept_structure_Live(IN root_concept_id integer)
  RETURNS TABLE(code character varying, description character varying
  ,concept_ref_id INT ,
        concept_id INT ,
        logical_type INT,
        component_type INT,
        level_depth INT,
        pkt INT
        
  ) AS
$BODY$
  DECLARE 
    max_depth INT :=0;
    counter INT :=0;
    i INT :=0;
    j INT :=0;
    t RECORD;
BEGIN
    -- define temp. table  

    DROP TABLE IF EXISTS Codes;
    CREATE TEMPORARY TABLE Codes 
    (
        code character varying(100),
        description character varying(1000),
        concept_ref_id  INT NULL,
        concept_id INT,
        logical_type INT,
        component_type INT,
        level_depth INT
    );
    ---------------------------------------------------------------------

    -- Table to contain the final concept tree structure
    -- (these include all component's code to be processed to get the final code list).
    
    DROP TABLE IF EXISTS ConceptCodes;
    CREATE TEMPORARY TABLE ConceptCodes AS
        SELECT *
        FROM Codes;    

    ALTER TABLE ConceptCodes ADD pkt SERIAL;
    ---------------------------------------------------------------------

    -- check if root concept has been deleted 
    IF (SELECT COUNT(*) 
        FROM clinicalcode_historicalconcept c 
        WHERE c.id = root_concept_id AND c.is_deleted IS NOT True) > 0 THEN
-----------------------------------------------------------------------
        -- Get a table of all the codes involved in the concepts in the tree.
        -----------------------------------------------------------------------

        WITH RECURSIVE get_codes(concept_ref_id, concept_id, concept_name,
                     logical_type, component_name, component_id, unique_id,
                     component_type, code, code_description, level_depth,
                     all_parents) AS 
        (

        SELECT * 
        FROM (
            SELECT  com.concept_ref_id, 
                c.id AS concept_id,
                c.name AS concept_name, 
                com.logical_type,
                com.name AS component_name, 
                com.id AS component_id,
                cr.id AS unique_id, 
                com.component_type, 
                cd.code,
                cd.description AS code_description, 
                1 AS level_depth,
                array[c.id] AS all_parents
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com ON com.concept_id = c.id
                JOIN clinicalcode_coderegex cr ON cr.component_id = com.id
                JOIN clinicalcode_codelist cl ON cr.code_list_id = cl.id
                JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
            WHERE c.id = root_concept_id AND (com.component_type = 3 OR com.component_type = 4)    AND c.is_deleted IS NOT TRUE
            UNION ALL
            SELECT  com.concept_ref_id, 
                c.id AS concept_id,
                c.name AS concept_name, 
                com.logical_type,
                com.name AS component_name, 
                com.id AS component_id,
                cl.id AS unique_id, 
                com.component_type, 
                cd.code, 
                cd.description AS code_description, 
                1 AS level_depth,
                array[c.id] AS all_parents
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com ON com.concept_id = c.id
                JOIN clinicalcode_codelist cl ON cl.component_id = com.id
                JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
            WHERE c.id = root_concept_id AND com.component_type = 2 AND c.is_deleted IS NOT TRUE
            UNION ALL
            SELECT     com.concept_ref_id, 
                c.id AS concept_id,
                c.name AS concept_name, 
                com.logical_type,
                com.name AS component_name, 
                com.id AS component_id,
                c.id AS unique_id, 
                com.component_type, 
                '' AS code,
                '' AS code_description, 
                1 AS level_depth, 
                array[c.id] AS all_parents
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com on com.concept_id = c.id
            WHERE c.id = root_concept_id AND com.component_type = 1 AND c.is_deleted IS NOT TRUE
        ) AS unused_alias
        UNION ALL
        -- now get child nodes from the root, this is done recursively call
        -- back to get_codes
        SELECT  child_codes.concept_ref_id, child_codes.concept_id,
            child_codes.concept_name, child_codes.logical_type,
            child_codes.component_name, child_codes.component_id,
            child_codes.unique_id, child_codes.component_type,
            child_codes.code, child_codes.code_description,
            parent_codes.level_depth + 1,
            parent_codes.all_parents||child_codes.concept_id
        FROM (    
            SELECT  com.concept_ref_id, c.id AS concept_id,
                c.name AS concept_name, com.logical_type,
                com.name AS component_name, com.id AS component_id,
                cr.id AS unique_id, com.component_type, cd.code AS code,
                cd.description AS code_description, 1 as level_depth
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com ON com.concept_id = c.id
                JOIN clinicalcode_coderegex cr ON cr.component_id = com.id
                JOIN clinicalcode_codelist cl ON cr.code_list_id = cl.id
                JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
            WHERE (com.component_type = 3 OR com.component_type = 4)
                AND c.is_deleted IS NOT TRUE
            UNION ALL
            SELECT  com.concept_ref_id, c.id AS concept_id,
                c.name AS concept_name, com.logical_type,
                com.name AS component_name, com.id AS component_id,
                cl.id AS unique_id, com.component_type, cd.code, 
                cd.description AS code_description, 1 as level_depth
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com ON com.concept_id = c.id
                JOIN clinicalcode_codelist cl ON cl.component_id = com.id 
                JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
            WHERE com.component_type = 2 AND c.is_deleted IS NOT TRUE
            UNION ALL
            SELECT  com.concept_ref_id, c.id AS concept_id,
                c.name AS concept_name, com.logical_type,
                com.name AS component_name, com.id AS component_id,
                c.id AS unique_id, com.component_type, '' AS code,
                '' AS code_description, 1 as level_depth
            FROM clinicalcode_concept c
                JOIN clinicalcode_component com ON com.concept_id = c.id
            WHERE com.component_type = 1 AND c.is_deleted IS NOT TRUE
        ) AS child_codes, get_codes parent_codes
        WHERE child_codes.concept_id = parent_codes.concept_ref_id
              AND  child_codes.concept_id <> ALL(parent_codes.all_parents)
        )
        INSERT INTO Codes(code, description, concept_ref_id, concept_id,
                  logical_type, component_type, level_depth)
        SELECT  rec.code, rec.code_description, rec.concept_ref_id,
            rec.concept_id, rec.logical_type, rec.component_type,
            rec.level_depth 
        FROM get_codes AS rec;

        -- Add all codes from components (both inclusion and exclusion).
        INSERT INTO ConceptCodes(code, description, concept_ref_id,
                concept_id, logical_type, component_type, level_depth)
        SELECT     c.code, c.description, c.concept_ref_id,
            c.concept_id, c.logical_type, c.component_type , c.level_depth
        FROM Codes c;


 END IF;
        
    -- Returns concept_component_structure.
    RETURN QUERY SELECT *
            FROM ConceptCodes c           
            ORDER BY c.pkt;


 END;

$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100
  ROWS 1000;

-- ===========================================================================
	END
    $$
        """)
    ]
