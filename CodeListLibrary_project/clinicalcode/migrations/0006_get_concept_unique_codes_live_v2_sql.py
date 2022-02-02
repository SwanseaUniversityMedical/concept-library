# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0005_get_concept_structure_live_sql'),
    ]

    operations = [
        migrations.RunSQL("""
            DO $$
			BEGIN
			
-- ===========================================================================
-- -- Function: get_concept_unique_codes_live_v2(integer)

-- Returns concept_unique_code as the new child concept as the code store under its component
                                        
-- created: Muhammad Elmessary
--           04/04/2020

-- DROP FUNCTION get_concept_unique_codes_live_v2(integer);


CREATE OR REPLACE FUNCTION get_concept_unique_codes_live_v2(IN root_concept_id integer)
  RETURNS TABLE(code character varying, description character varying) AS
$BODY$

BEGIN
 
    ---------------------------------------------------------------------
    -- define temp. table  
    -- Table to contain the final set of codes from the concepts 

    DROP TABLE IF EXISTS ConceptCodes;
    CREATE TEMPORARY TABLE ConceptCodes
    (
        code character varying(100),
        description character varying(1000),
        concept_ref_id INT NULL,
        concept_id INT,
        logical_type INT,
        component_type INT
    );
    ---------------------------------------------------------------------



    -- check if root concept has been deleted 
    IF (SELECT COUNT(*) 
        FROM clinicalcode_concept c 
        WHERE c.id = root_concept_id AND c.is_deleted IS NOT True) > 0 THEN
      
        ---------------------------------------------------------------------
        
        INSERT INTO ConceptCodes(code, description, concept_ref_id, concept_id, logical_type, component_type)
        SELECT  tt.code, tt.code_description, tt.concept_ref_id,
                tt.concept_id, tt.logical_type, tt.component_type
        --SELECT * 
        FROM (
                SELECT  -- expresion / expresion-select
                    com.concept_ref_id, 
                    c.id AS concept_id,
                    c.name AS concept_name, 
                    com.logical_type,
                    com.name AS component_name, 
                    com.id AS component_id,
                    cr.id AS unique_id, 
                    com.component_type, 
                    cd.code,
                    cd.description AS code_description
                FROM clinicalcode_concept c
                    JOIN clinicalcode_component com ON com.concept_id = c.id
                    JOIN clinicalcode_coderegex cr ON cr.component_id = com.id
                    JOIN clinicalcode_codelist cl ON cl.id = cr.code_list_id
                    JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
                WHERE c.id = root_concept_id AND (com.component_type = 3 OR com.component_type = 4)    AND c.is_deleted IS NOT TRUE
                UNION ALL
                SELECT  -- query builder
                    com.concept_ref_id, 
                    c.id AS concept_id,
                    c.name AS concept_name, 
                    com.logical_type,
                    com.name AS component_name, 
                    com.id AS component_id,
                    cl.id AS unique_id, 
                    com.component_type, 
                    cd.code, 
                    cd.description AS code_description
                FROM clinicalcode_concept c
                    JOIN clinicalcode_component com ON com.concept_id = c.id
                    JOIN clinicalcode_codelist cl ON cl.component_id = com.id
                    JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
                WHERE c.id = root_concept_id AND com.component_type = 2 AND c.is_deleted IS NOT TRUE
                UNION ALL
                SELECT    -- child concept
                    com.concept_ref_id, 
                    c.id AS concept_id,
                    c.name AS concept_name, 
                    com.logical_type,
                    com.name AS component_name, 
                    com.id AS component_id,
                    c.id AS unique_id, 
                    com.component_type, 
                    cd.code, 
                    cd.description AS code_description
                FROM clinicalcode_concept c
            JOIN clinicalcode_component com ON com.concept_id = c.id
                    JOIN clinicalcode_codelist cl ON cl.component_id = com.id
                    JOIN clinicalcode_code cd ON cd.code_list_id = cl.id
                WHERE c.id = root_concept_id AND com.component_type = 1 AND c.is_deleted IS NOT TRUE
        ) tt ;

    ----------------------------------
    END IF;

    -- Return the list of distinct codes and their description.
    RETURN QUERY SELECT DISTINCT ccf.code, ccf.description
            FROM ConceptCodes ccf
            WHERE ccf.logical_type = 1 AND ccf.code <> ''
                and ccf.code NOT IN (SELECT c.code from ConceptCodes c WHERE c.logical_type = 2)
            ORDER BY ccf.code;

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
