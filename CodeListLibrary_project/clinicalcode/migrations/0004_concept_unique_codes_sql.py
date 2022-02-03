# -*- coding: utf-8 -*-
# Modified by: Pete Arnold

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinicalcode', '0003_get_parent_concept_tree_by_concept_id_sql'),
    ]

    operations = [
        migrations.RunSQL("""
            DO $$
			BEGIN
			
-- ===========================================================================
-- Function: public.concept_unique_codes(integer)

-- concept_unique_codes(concept_id)
-- recursive queries to get all included and excluded codes for a root concept and its children
-- all child concept components aare dealt wth separately 
-- we then return all inclusive codes minus any codes marked to be excluded
                                        
-- modified: Muhammad Elmessary
--           15/08/2019

-- DROP FUNCTION public.concept_unique_codes(integer);

CREATE OR REPLACE FUNCTION public.concept_unique_codes(IN root_concept_id integer)
  RETURNS TABLE(code character varying, description character varying) AS
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
        concept_ref_id INT NULL,
        concept_id INT,
        logical_type INT,
        component_type INT,
        level_depth INT
    );
    ---------------------------------------------------------------------

    -- Table to contain the final set of codes from the concepts in the
    -- concept tree (these include all component to be processed to get the final code list).
    DROP TABLE IF EXISTS ConceptCodes;
    CREATE TEMPORARY TABLE ConceptCodes AS
        SELECT *
        FROM Codes;    

    ALTER TABLE ConceptCodes ADD pkt SERIAL;
    ---------------------------------------------------------------------

    -- Table to store the final list for a specific level_depth
    DROP TABLE IF EXISTS ConceptCodesFinal;
    CREATE TEMPORARY TABLE ConceptCodesFinal AS
        SELECT *
        FROM ConceptCodes;

    ALTER TABLE ConceptCodesFinal ADD parent_logical_type INT;
    ALTER TABLE ConceptCodesFinal DROP pkt;
    ALTER TABLE ConceptCodesFinal ADD pkt_ref INT;
    ALTER TABLE ConceptCodesFinal ADD pkt_ref_parent INT;
    ---------------------------------------------------------------------

    -- Table to filter the final list for a specific level_depth (removes exclusion)
    DROP TABLE IF EXISTS ConceptCodesFinal_temp;
    CREATE TEMPORARY TABLE ConceptCodesFinal_temp AS
        SELECT *
        FROM ConceptCodesFinal;
    ---------------------------------------------------------------------

    -- check if root concept has been deleted 
    IF (SELECT COUNT(*) 
        FROM clinicalcode_concept c 
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


        
        -- get the max depth of the hierarchy tree
        SELECT MAX(c.level_depth) INTO STRICT max_depth FROM ConceptCodes c;


          -- loop through each tree level, building up a final list of codes that have been included for each level (child concept is a closed box)
          IF max_depth IS NOT NULL THEN
        -- loop through Tree from bottom up (only if there is a child concept)
        IF max_depth > 1 THEN
            FOR i in REVERSE max_depth..2 LOOP
                
                -- clear temp. table each loop
                delete from ConceptCodesFinal_temp;

                INSERT INTO ConceptCodesFinal_temp(code, description, concept_ref_id, concept_id, logical_type, component_type, level_depth, parent_logical_type, pkt_ref, pkt_ref_parent)
                SELECT cci.code, cci.description, ccparent.concept_ref_id, cci.concept_id, cci.logical_type, cci.component_type, i --cci.level_depth
                     , ccparent.logical_type AS parent_logical_type, cci.pkt AS pkt_ref, ccparent.pkt AS pkt_ref_parent
                FROM ConceptCodes cci
                JOIN ConceptCodes ccparent 
                ON   cci.concept_id = ccparent.concept_ref_id 
                 and cci.component_type <> 1 and ccparent.component_type = 1
                WHERE cci.level_depth = i  and ccparent.level_depth = i-1 ;

                IF i>1 THEN
                    -- delete processed codes from main store table
                    DELETE FROM ConceptCodes cci
                    WHERE cci.pkt in (SELECT c.pkt_ref from ConceptCodesFinal_temp c);

                    DELETE FROM ConceptCodes cci
                    WHERE cci.pkt in (SELECT DISTINCT c.pkt_ref_parent from ConceptCodesFinal_temp c )
                      and cci.component_type = 1;
                END IF;   

                
                -- empty the table
                delete from ConceptCodesFinal;

                -- filter items that are to be included  in this level for each child concept
                FOR t IN
                SELECT distinct concept_ref_id FROM ConceptCodesFinal_temp  ORDER BY concept_ref_id
                LOOP
                    INSERT INTO ConceptCodesFinal (code, description, concept_ref_id, concept_id, logical_type, component_type, level_depth, parent_logical_type, pkt_ref, pkt_ref_parent)
                    SELECT tt.code, tt.description, tt.concept_ref_id, tt.concept_id, tt.logical_type, tt.component_type, tt.level_depth, tt.parent_logical_type,  tt.pkt_ref, tt.pkt_ref_parent
                    FROM ConceptCodesFinal_temp tt 
                    WHERE tt.concept_ref_id = t.concept_ref_id
                       and tt.logical_type = 1
                       and tt.code NOT IN (SELECT c.code from ConceptCodesFinal_temp c WHERE c.concept_ref_id = t.concept_ref_id and c.logical_type = 2);
                END LOOP;


                -- update the base table with the processed codes and make their logical include/exclude equal to their parent concept
                INSERT INTO ConceptCodes(code, description, concept_ref_id, concept_id, logical_type, component_type, level_depth)
                SELECT cci.code, cci.description,cci.concept_ref_id, cci.concept_id, cci.parent_logical_type -- make their logical include/exclude equal to their parent concept
                     , cci.component_type, i --cci.level_depth
                FROM ConceptCodesFinal cci
                WHERE cci.level_depth = i;


                -- delete items that are to be excluded  (all codes now (depth=i) are level)
                DELETE FROM ConceptCodes cci
                WHERE cci.level_depth = i and cci.component_type <> 1 and 
                  cci.code in (SELECT c.code from ConceptCodes c WHERE c.logical_type = 2 and c.level_depth = i and c.component_type <> 1);

               -- updte/move processed codes to a lower depth
               UPDATE  ConceptCodes cc
               SET level_depth = i-1
               WHERE cc.level_depth = i ;

            END LOOP;
            END IF;
        END IF;


    -- delete items that are to be excluded  (all codes are level 1 now)
    DELETE FROM ConceptCodes cct
    WHERE cct.code in (SELECT c.code from ConceptCodes c WHERE c.logical_type = 2);


    END IF;

    -- Return the list of distinct codes and their description.
    RETURN QUERY SELECT DISTINCT ccf.code, ccf.description
            FROM ConceptCodes ccf
            WHERE ccf.logical_type = 1 AND ccf.code <> ''
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
