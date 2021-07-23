''' 
    --------------------------------------------------------------------------
    DB Utilities

    --------------------------------------------------------------------------
'''
#from dateutil.parser import parse
from django.db import connection, connections #, transaction
from django.db.models import Q
from django.contrib.auth.models import User, Group
from django.utils.timezone import now
from simple_history.utils import update_change_reason

from itertools import *

from .models.Code import Code
from .models.CodeList import CodeList
from .models.CodeRegex import CodeRegex
from .models.CodingSystem import CodingSystem
from .models.Component import Component
from .models.Concept import Concept
from .models.ConceptTagMap import ConceptTagMap
from .models.Tag import Tag
from .models.WorkingSet import WorkingSet
from .models.WorkingSetTagMap import WorkingSetTagMap
from .models.PublishedConcept import PublishedConcept
from .models.Phenotype import Phenotype
from .models.PublishedPhenotype import PublishedPhenotype
from .models.ConceptCodeAttribute import ConceptCodeAttribute

from .permissions import *

import datetime
import utils
import json
import ast
from collections import OrderedDict
from collections import OrderedDict as ordr 
import numpy as np
import pandas as pd
# pandas needs to be installed by "pip2"
# pip2 install pandas

from django.core.exceptions import ObjectDoesNotExist #, PermissionDenied
from django.core.validators import URLValidator
import re
from psycopg2.errorcodes import INVALID_PARAMETER_VALUE
from django.conf import settings

def deleteConcept(pk, user):
    ''' Delete a concept based on a concept id '''
    # get selected concept
    concept = Concept.objects.get(pk=pk)
    concept.is_deleted = True
    concept.deleted = datetime.datetime.now()
    concept.deleted_by = user
    concept.changeReason = standardiseChangeReason("Deleted")
    concept.save()


def restoreConcept(pk, user):
    ''' Restore a concept '''
    # get selected concept
    concept = Concept.objects.get(pk=pk)
    concept.is_deleted = False
    concept.deleted = None
    concept.deleted_by = None
    concept.changeReason = standardiseChangeReason("restored")
    concept.save()


def format_sql_parameter(param):
    # add a '' around parameter if the parameter is of type unicode
    if utils.isDateTime(param):
        return "'{}'".format(str(param))
    elif utils.isInt(param) or utils.isFloat(param):
        return "{}".format(str(param))
    elif type(param) is unicode:
        return "UPPER('{}')".format(str(param))

    return param


def deleteConceptRelatedObjects(pk):
    ''' Delete a concept components based on a concept id '''
    # get selected concept
    concept = Concept.objects.get(pk=pk)

    # get all the ConceptCodeAttribute attached to the concept
    concept_ConceptCodeAttributes = concept.conceptcodeattribute_set.all()
 
    for cca in concept_ConceptCodeAttributes:
        if cca:
            cca.delete()
            
    # need to save root concept to have proper date-time stamp for retrieving history data
    if concept and concept_ConceptCodeAttributes:
        #concept.changeReason = "ConceptCodeAttributes deleted"
        #concept.save()
        concept.save_without_historical_record()
        
    # get all the components attached to the concept
    components = concept.component_set.all()

    # for all components delete the expression, query builder, individually select codes and codes
    for com in components:
        codelist = None
        coderegex = None

        has_codelist = hasattr(com, 'codelist')
        has_coderegex = hasattr(com, 'coderegex')

        if has_codelist:
            codelist = com.codelist
        if has_coderegex:
            coderegex = com.coderegex

        if has_coderegex:
            has_codelist = hasattr(coderegex, 'code_list')

            if has_codelist:
                codelist = coderegex.code_list

                codes = None

                if hasattr(codelist, 'codes'):
                    codes = codelist.codes.all()

                    for code in codes:
                        if code:
                            code.delete()

                if codelist:
                    codelist.delete()
            if coderegex:
                coderegex.delete()
        else:
            if has_codelist:
                codes = None

                if hasattr(codelist, 'codes'):
                    codes = codelist.codes.all()

                if hasattr(codelist, 'codes'):
                    for code in codes:
                        if code:
                            code.delete()
                if codelist:
                    codelist.delete()
        if com:
            com.delete()

    if concept and components:
        #concept.changeReason = "Components deleted"
        #concept.save()
        concept.save_without_historical_record()


def fork(pk, user):
    '''
        Create a copy of a concept.
        Creates a new concept and recreates any attached coderegex, codelist
        and codes.
    '''
    has_components = False
    has_ConceptCodeAttributes = False
    concept = Concept.objects.get(pk=pk)
    old_ConceptCodeAttributes = concept.conceptcodeattribute_set.all()
    old_components = concept.component_set.all()
    # Reset the concept primary key to none so that it is treated as a new
    # concept.
    concept.pk = None
    concept.owner_id = user.id
    concept.owner_access = Permissions.EDIT
    concept.modified_by_id = user.id
    #concept.changeReason = "Forked root from concept %s" % pk
    concept.save()
#     #concept.save_without_historical_record()
    concept.history.latest().delete() 
    
    for cca in old_ConceptCodeAttributes:
        cca.pk = None
        cca.created_by = user
        cca.concept = concept
        cca.save()

    # For all components reset the coderegex, codelist and codes. This will
    # ensure that they are treated as new entities and are attached to the
    # newly forked concept.
    for com in old_components:
        has_components = True
        old_codelist = None
        old_coderegex = None
        # Check if it is a codelist or coderegex.
        has_codelist = hasattr(com, 'codelist')
        has_coderegex = hasattr(com, 'coderegex')
        if has_codelist:
            old_codelist = com.codelist
        if has_coderegex:
            old_coderegex = com.coderegex
        # Reset the component primary key to none so that it is treated as a
        # new component.
        com.pk = None
        com.created_by = user
        # Attached the forked concept to the component.
        com.concept = concept
        com.save()
        # If it is a coderegex then we must check if a code list is attached.
        # if the component is a code list then we must get the attached code
        # list and codes
        if has_coderegex:
            has_codelist = hasattr(old_coderegex, 'code_list')
            if has_codelist:
                old_codelist = old_coderegex.code_list
                if old_codelist:
                    old_codes = None
                    # get all the codes attached to the code list
                    if hasattr(old_codelist, 'codes'):
                        old_codes = old_codelist.codes.all()
                    # reset code list primary key to None and attach the newly forked component
                    old_codelist.pk = None
                    old_codelist.component = com
                    old_codelist.save()
                    # check if we have codes attached to the codelist
                    if hasattr(old_codelist, 'codes'):
                        for code in old_codes:
                            # for each code reset the code primary key and attach the newly forked codelist
                            code.pk = None
                            code.codelist = old_codelist
                            code.save()
            # reset the code regex primary key to None and attach the newly forked component and codelist
            old_coderegex.pk = None
            old_coderegex.component = com
            old_coderegex.code_list = old_codelist
            old_coderegex.save()
        elif has_codelist:
            old_codes = None
            # get all the codes that are attached to the code list
            if hasattr(old_codelist, 'codes'):
                old_codes = old_codelist.codes.all()
            if old_codelist:
                # reset the code list primary key and attach the newly forked component
                old_codelist.pk = None
                old_codelist.component = com
                old_codelist.save()
                # check if we have codes attached to the code list
                if hasattr(old_codelist, 'codes'):
                    # for each code reset the primary key to none and attach the newly forked code list
                    for code in old_codes:
                        code.pk = None
                        code.codelist = old_codelist
                        code.save()
    # Save the concept again because the code lists, code regexes and codes get
    # saved after the concept is saved so we need to reflect these added
    # components in the history.
    if has_components or has_ConceptCodeAttributes:
        #concept.changeReason = "Forked components"
        #concept.save()
        concept.save_without_historical_record()
        
    # Return the new concept primary key.
    return concept.pk


def forkHistoryConcept(user, concept_history_id):
    '''
        Fork an historical concept as a new concept with a new id.
    '''
    has_components = False
    has_ConceptCodeAttribute = False
    concept = getHistoryConcept(concept_history_id)
    # Recreate the historical concept. Note that we do use create here since
    # that will create and save the concept and we will not be able to set
    # the changeReason resulting in two entries in the history for the same
    # process.
    concept_obj = Concept(
        name=concept['name'],
        description=concept['description'],
        created_by=User.objects.filter(pk=concept['created_by_id']).first(),
        author=concept['author'],
        entry_date=concept['entry_date'],
        modified_by=User.objects.filter(pk=user.id).first(),
        validation_performed=concept['validation_performed'],
        validation_description=concept['validation_description'],
        publication_doi=concept['publication_doi'],
        publication_link=concept['publication_link'],
        secondary_publication_links=concept['secondary_publication_links'],
        paper_published=concept['paper_published'],
        source_reference=concept['source_reference'],
        citation_requirements=concept['citation_requirements'],
        coding_system=CodingSystem.objects.filter(pk=concept['coding_system_id']).first(),
        created=concept['created'],
        modified=concept['modified'], 
        owner_id=user.id,
        group_id=concept['group_id'],
        owner_access=Permissions.EDIT,
        group_access=concept['group_access'],
        world_access=concept['world_access'],
        tags=concept['tags'],
        code_attribute_header=concept['code_attribute_header']
    )
    concept_obj.changeReason = "Forked root from concept %s/%s/%s" % (concept['id'], concept_history_id, concept['entry_date'])
    concept_obj.save()
    concept_obj.history.latest().delete() 
    
    if concept_obj:
        # get the historic date this was effective from
        concept_history_date = concept['history_date']

        # get concept ConceptCodeAttributes  that were active from the time of the concepts effective date
        concept_ConceptCodeAttributes = getHistory_ConceptCodeAttribute(concept_id = concept['id']
                                                           , concept_history_date = concept_history_date
                                                           , code_attribute_header = concept['code_attribute_header']
                                                           , expand_attrs_into_cols = False )
 
        for cca in concept_ConceptCodeAttributes:
            has_ConceptCodeAttribute = True
            cca_obj = ConceptCodeAttribute.objects.create(
                concept=concept_obj,
                code=cca['code'],
                attributes=cca['attributes'],
                created_by=User.objects.filter(pk=cca['created_by_id']).first(),
                created=cca['created'],
                modified=cca['modified']
            )

        # get components that were active from the time of the concepts effective date
        components = getHistoryComponents(concept['id'], concept_history_date, skip_codes=True)

        for com in components:
            has_components = True

            # recreate the historical component
            concept_ref = Concept.objects.filter(pk=com['concept_ref_id']).first()
            concept_ref_history_id = com['concept_ref_history_id']
            # stop FORK from automatically referring to the latest version of child concepts
            #if(concept_ref is not None):
            #   concept_ref_history_id = Concept.objects.get(id=com['concept_ref_id']).history.latest().pk
                
            com_obj = Component.objects.create(
                comment=com['comment'],
                component_type=com['component_type'],
                concept=concept_obj,
                concept_ref=concept_ref,
                created_by=User.objects.filter(pk=com['created_by_id']).first(),
                logical_type=com['logical_type'],
                modified_by=User.objects.filter(pk=com['modified_by_id']).first(),
                name=com['name'],
                created=com['created'],
                modified=com['modified'],
                concept_ref_history_id=concept_ref_history_id
                )


            # check if the historical component was created
            if com_obj:
                # check if it is a code list component
                if com['component_type'] == 1 or com['component_type'] == 2:
                    # get historical code list that was active from the time of the concepts effective date
                    codelist = getHistoryCodeListByComponentId(com['id'], concept_history_date)

                    # recreate historical code list
                    codelist_obj = CodeList.objects.create(
                        component=com_obj,
                        description=codelist['description'],
                        sql_rules=codelist['sql_rules'],
                        created=codelist['created'],
                        modified=codelist['modified'])

                    # check if the historical code list was created
                    if codelist_obj:
                        # get historical codes that were active from the time of the concepts effective date
                        codes = getHistoryCodes(codelist['id'], concept_history_date)

                        for code in codes:
                            # recreate historical code
                            Code.objects.create(
                                code_list=codelist_obj,
                                code=code['code'],
                                description=code['description'])

                # check if it is a Code regex component
                elif com['component_type'] == 3 or com['component_type'] == 4:
                    codelist_obj = None

                    # get historical code regex that was active from the time of the concepts effective date
                    coderegex = getHistoryCodeRegex(com['id'], concept_history_date)

                    if coderegex['code_list_id'] is not None:
                        # get historical code list that was active from the time of the concepts effective date
                        codelist = getHistoryCodeListById(coderegex['code_list_id'], concept_history_date)

                        # recreate historical code list
                        codelist_obj = CodeList.objects.create(
                            component=com_obj,
                            description=codelist['description'],
                            sql_rules=codelist['sql_rules'],
                            created=codelist['created'],
                            modified=codelist['modified'])

                        if codelist_obj:
                            # get historical codes that were active from the time of the concepts effective date
                            codes = getHistoryCodes(codelist['id'], concept_history_date)

                            for code in codes:
                                # recreate historical code
                                Code.objects.create(
                                    code_list=codelist_obj,
                                    code=code['code'],
                                    description=code['description'])

                    # recreate historical code regex
                    CodeRegex.objects.create(
                        component=com_obj,
                        regex_type=coderegex['regex_type'],
                        regex_code=coderegex['regex_code'],
                        sql_rules=coderegex['sql_rules'],
                        code_list=codelist_obj)
    # Save the concept again because the code lists, code regexes and codes get
    # saved after the concept is saved so we need to reflect these added
    # components in the history.
    if has_components or has_ConceptCodeAttribute:
        #concept_obj.changeReason = "Forked historic components"
        #concept_obj.save()
        concept_obj.save_without_historical_record()
        
    # Return the new concept primary key.
    return concept_obj.pk, "Forked from concept %s/%s/%s" % (concept['id'], concept_history_id, concept['entry_date'])


""" ---------------------------------------------------------------------------
    Appears to be unused.
    ---------------------------------------------------------------------------
def getConceptAsOf(concept_id, history_date):
    ''' get a historical concept from a point in time '''

    concept = Concept.objects.get(concept_id=concept_id)

    concept_history = concept.history.as_of(history_date)

    return ""
    ---------------------------------------------------------------------------
"""

def getConceptTreeByConceptId(concept_id):
    '''
        get concept tree based on a supplied concept id
    '''
    with connection.cursor() as cursor:

        cursor.execute("SELECT * FROM get_concept_tree_by_concept_id(%s);" , [concept_id])

        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


def getParentConceptTreeByConceptId(concept_id):
    '''
        starting at the child concept we work our way through to the parents concepts
    '''
    with connection.cursor() as cursor:

        cursor.execute("SELECT * FROM get_parent_concept_tree_by_concept_id(%s);" , [concept_id])

        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


def getGroupOfCodesByConceptId(concept_id):
    '''
        get unique set of codes for a concept (its children concepts contain code directly stored)
    '''
        
    with connection.cursor() as cursor:
        #cursor.execute("SELECT * FROM get_concept_unique_codes_live_v2(%s);" , [concept_id])
        
        # The codes export must have only one row per unique code. 
        # That is a hard requirement. Event with different descriptions
        cursor.execute('''SELECT 
                            DISTINCT c.code code, MAX(c.description) description
                        FROM get_concept_unique_codes_live_v2(%s) c
                        GROUP BY c.code
                        ORDER BY c.code
                        ;                        
                        '''
                        , [concept_id]
                        )


        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
                


def getGroupOfCodesByConceptId_xxx(concept_id):
    '''
        get unique set of codes for a concept and all of its children concepts
    '''
    
    return getConceptUniqueCodesLive(concept_id)


def getGroupOfConceptsByWorkingsetId_historical(workingset_id , workingset_history_id=None):
    '''
        get concept_informations of the specified working set 
        - from a specific version (or live version if workingset_history_id is None) 

    '''
    
    if workingset_history_id is None:
        workingset_history_id = WorkingSet.objects.get(pk=workingset_id).history.latest('history_id').history_id
        
    concepts = OrderedDict([])
    concept_informations = json.loads(WorkingSet.history.get(id=workingset_id, history_id=workingset_history_id).concept_informations
                                    , object_pairs_hook=OrderedDict)
    
    c = OrderedDict([])
    for c in concept_informations:
        concepts.update(c)

    return concepts

    
def get_concept_versions_in_workingset(workingset_id , workingset_history_id=None):
    '''
        get concept_version of the specified working set 
        - from a specific version (or live if workingset_history_id is None)
    '''
    
    with connection.cursor() as cursor:
        if workingset_history_id is None:
            concept_version = WorkingSet.objects.get(id=workingset_id).concept_version
        else:
            concept_version = WorkingSet.history.get(id=workingset_id , history_id=workingset_history_id).concept_version
        

        return concept_version
    
    
def getHistoryCodeListByComponentId(component_id, concept_history_date):
    '''
        return a list of code list components from a point in time
    '''
    my_params = {
        'component_id': component_id,
        'concept_history_date': concept_history_date
        }

    with connection.cursor() as cursor:
        cursor.execute('''SELECT hcl.id,
        hcl.history_id,
        hcl.history_date,
        hcl.history_change_reason,
        hcl.history_type,
        hcl.component_id,
        hcl.history_user_id,
        hcl.created,
        hcl.modified,
        hcl.description,
        hcl.sql_rules
        FROM public.clinicalcode_historicalcodelist hcl
        WHERE (hcl.component_id = %(component_id)s and hcl.history_date <= %(concept_history_date)s::timestamptz AND hcl.history_type <> '-')
        ORDER BY hcl.history_date DESC, hcl.history_id DESC LIMIT 1;''' , my_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()

        if row is None:
            return None

        row_dict = dict(izip(col_names, row))

        return row_dict


def getHistoryCodeListById(code_list_id, concept_history_date):
    ''' Get historic code regex attached to a component that was effective from a point in time based on concept history date '''

    if code_list_id is None:
        return

    my_params = {
        'code_list_id': code_list_id,
        'concept_history_date': concept_history_date
        }

    with connection.cursor() as cursor:
        cursor.execute('''SELECT hcl.id,
        hcl.history_id,
        hcl.history_date,
        hcl.history_change_reason,
        hcl.history_type,
        hcl.component_id,
        hcl.history_user_id,
        hcl.created,
        hcl.modified,
        hcl.description,
        hcl.sql_rules
        FROM public.clinicalcode_historicalcodelist hcl
        WHERE (hcl.id = %(code_list_id)s and hcl.history_date <= %(concept_history_date)s::timestamptz AND hcl.history_type <> '-')
        ORDER BY hcl.history_date DESC, hcl.history_id DESC LIMIT 1;''' , my_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(izip(col_names, row))

        return row_dict


def getHistoryCodeRegex(component_id, concept_history_date):
    ''' Get historic code regex attached to a component that was effective from a point in time based on concept history date '''

    my_params = {
        'component_id': component_id,
        'concept_history_date': concept_history_date
        }

    with connection.cursor() as cursor:
        cursor.execute('''SELECT hcr.id,
        hcr.regex_type,
        hcr.regex_code,
        hcr.column_search,
        hcr.sql_rules,
        hcr.history_id,
        hcr.history_date,
        hcr.history_change_reason,
        hcr.history_type,
        hcr.component_id,
        hcr.history_user_id,
        hcr.code_list_id
        FROM clinicalcode_historicalcoderegex AS hcr
        WHERE (hcr.component_id = %(component_id)s AND hcr.history_date <= %(concept_history_date)s::timestamptz AND hcr.history_type <> '-')
        ORDER BY hcr.history_date DESC, hcr.history_id DESC LIMIT 1;''', my_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(izip(col_names, row))

        return row_dict


def getHistoryCodes(code_list_id, concept_history_date):
    '''
        Get historic codes attached to a code list that were effective from a
        point in time based on concept effective date.
    '''
    my_params = {
        'code_list_id': code_list_id,
        'concept_history_date': concept_history_date
        }
    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the code historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all codes that don't have a
        -- delete event by the specified date.
        SELECT 
            c.id,
            c.code,
            c.description,
            c.history_id,
            c.history_change_reason,
            c.history_type,
            c.code_list_id,
            c.history_user_id
        FROM clinicalcode_historicalcode AS c
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the codes for this component codelist and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalcode
                WHERE  (code_list_id = %(code_list_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the codes that have been deleted
                -- for this component codelist.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalcode
                WHERE  (code_list_id = %(code_list_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON c.history_id = d.history_id
        ORDER BY c.id
        ''' , my_params)
        col_names = [col[0] for col in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor.fetchall()]


def getHistoryComponentByHistoryId(component_history_id):
    '''
        Get historic component based on a component history id.
    '''
    with connection.cursor() as cursor:
        cursor.execute('''SELECT hc.id,
        hc.created,
        hc.modified,
        hc.comment,
        hc.component_type,
        hc.name,
        hc.history_id,
        hc.history_date,
        hc.history_change_reason,
        hc.history_type,
        hc.concept_id,
        hc.concept_ref_id,
        hc.concept_ref_history_id,
        COALESCE(rcon.name, '') as concept_name,
        ucb.username as created_by_username,
        hc.history_user_id,
        umb.username as modified_by_username,
        hc.logical_type
        FROM public.clinicalcode_historicalcomponent AS hc
        LEFT OUTER JOIN clinicalcode_concept AS rcon ON rcon.id = hc.concept_ref_id
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hc.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hc.modified_by_id
        WHERE (hc.history_id = %s)''' , [component_history_id])

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        component = dict(izip(col_names, row))
        
       
        
        types = list(t[0] for t in Component.LOGICAL_TYPES)
        logical_type = int(component['logical_type'])
        if logical_type in types:
            logical_type = Component.LOGICAL_TYPES[logical_type - 1][1]
        else:
            logical_type = 'n/a'
        component['get_logical_type_display'] = logical_type
            
        return component


def getHistoryConcept(concept_history_id):
    ''' Get historic concept based on a concept history id '''

    with connection.cursor() as cursor:
        cursor.execute('''SELECT hc.created,
        hc.modified,
        hc.id,
        hc.name,
        hc.description,
        hc.author,
        hc.entry_date,
        hc.validation_performed,
        hc.validation_description,
        hc.publication_doi,
        hc.publication_link,
        hc.secondary_publication_links,
        hc.paper_published,
        hc.source_reference,
        hc.citation_requirements,
        hc.created_by_id,
        hc.modified_by_id,
        hc.owner_id,
        hc.group_id,
        hc.owner_access,
        hc.group_access,
        hc.world_access,
        ucb.username as created_by_username,
        umb.username as modified_by_username,
        hc.coding_system_id,
        cs.name as coding_system_name,
        hc.history_id,
        hc.history_date,
        hc.history_change_reason,
        hc.history_user_id,
        uhu.username as history_user,
        hc.history_type,
        hc.is_deleted,
        hc.deleted,
        hc.deleted_by_id,
        hc.tags,
        hc.code_attribute_header
        FROM clinicalcode_historicalconcept AS hc
        JOIN clinicalcode_codingsystem AS cs ON hc.coding_system_id = cs.id
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hc.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hc.modified_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hc.history_user_id
        WHERE (hc.history_id = %s)''' , [concept_history_id])

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(izip(col_names, row))

        return row_dict


def getHistoryWorkingset(workingset_history_id):
    ''' Get historic workingset based on a workingset history id '''

    with connection.cursor() as cursor:
        cursor.execute('''SELECT hw.created,
        hw.modified,
        hw.id,
        hw.name,
        hw.description,
        hw.author,
        hw.publication,
        hw.publication_doi,
        hw.publication_link,
        hw.secondary_publication_links,
        hw.source_reference,
        hw.citation_requirements,
        hw.owner_id,
        hw.group_id,
        hw.owner_access,
        hw.group_access,
        hw.world_access,
        hw.concept_informations,
        hw.concept_version,
        hw.created_by_id,
        hw.updated_by_id,
        ucb.username as created_by_username,
        umb.username as modified_by_username,
        hw.history_id,
        hw.history_date,
        hw.history_change_reason,
        hw.history_user_id,
        uhu.username as history_user,
        hw.history_type,
        hw.is_deleted,
        hw.deleted,
        hw.deleted_by_id        
        FROM clinicalcode_historicalworkingset AS hw
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hw.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hw.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hw.history_user_id
        WHERE (hw.history_id = %s)''' , [workingset_history_id])

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(izip(col_names, row))

        return row_dict


def getHistoryWorkingsetTagMaps(workingset_id, workingset_history_date):
    ''' Get historic workingset tag maps that are attached to a workingset that were effective from a point in time '''

    my_params = {
        'workingset_id': workingset_id,
        'workingset_history_date': workingset_history_date
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the tags historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all codes that don't have a
        -- delete event by the specified date.
        SELECT 
            hw.id,
            hw.created,
            hw.modified,
            hw.history_id,
            hw.history_date,
            hw.history_change_reason,
            hw.history_type,
            hw.workingset_id,
            hw.created_by_id,
            hw.history_user_id,
            hw.tag_id
        FROM clinicalcode_historicalworkingsettagmap AS hw
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the tags for this working set and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalworkingsettagmap
                WHERE  (workingset_id = %(workingset_id)s AND 
                        history_date <= %(workingset_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the tags that have been deleted
                -- for this WS.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalworkingsettagmap
                WHERE  (workingset_id = %(workingset_id)s AND 
                        history_date <= %(workingset_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hw.history_id = d.history_id
        ORDER BY hw.id
        ''' , my_params)
        
        col_names = [col[0] for col in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor.fetchall()]



def getConceptsFromJSON(pk="", concepts_json=""):
    '''
        Extract concept the ids from a workingset's JSON field.
    '''

    tempLst = []
    conceptIDs = []
    if pk.strip() != "":
        rows = getGroupOfConceptsByWorkingsetId_historical(pk)
        conceptIDs = rows.keys()
    elif concepts_json.strip() != "":
        rows = ast.literal_eval(concepts_json)
        conceptIDs = [k for d in rows for k in d.keys()]

    return conceptIDs

def getConceptBrands(request, concept_list):
    '''
        return concept brands 
    '''
    conceptBrands = {}
    concepts = Concept.objects.filter(id__in=concept_list).values('id','name', 'group')
    
    for c in concepts:
        conceptBrands[c['id']] = [] # ''
        if c['group'] != None:
            g = Group.objects.get(pk=c['group'])
            for item in request.BRAND_GROUPS:
                for brand, groups in item.iteritems():
                    if g.name in groups: 
                        #conceptBrands[c['id']].append('<img src="{% static "img/brands/' + brand + '/logo.png %}" height="10px" title="' + brand + '" alt="' + brand + '" />') 
                        conceptBrands[c['id']].append(brand) 
                        
                            
    return conceptBrands


def chkListIsAllIntegers(lst):
    '''
        Check all elements of a list are integers.
    '''
    try:
        return all(type(int(x)) is int for x in lst)
    except:
        return False


def revertHistoryWorkingset(user, workingset_history_id):
    ''' Revert a selected historical working set and create it as a new working set using an existing working set id '''
    #has_components = False
    workingset = getHistoryWorkingset(workingset_history_id)

    # get selected working set
    workingset_obj = WorkingSet.objects.get(pk=workingset['id'])

    # Don't allow revert if the active object is deleted
    if workingset_obj.is_deleted: raise PermissionDenied

    # update working set with historical information
    workingset_obj.name = workingset['name']
    workingset_obj.author = workingset['author']
    workingset_obj.description = workingset['description']
    workingset_obj.publication = workingset['publication']

    workingset_obj.created_by = User.objects.filter(pk=workingset['created_by_id']).first()

    workingset_obj.updated_by = User.objects.filter(pk=user.id).first()

    workingset_obj.publication_doi = workingset['publication_doi']
    workingset_obj.publication_link = workingset['publication_link']
    workingset_obj.secondary_publication_links = workingset['secondary_publication_links']
    workingset_obj.source_reference = workingset['source_reference']
    workingset_obj.citation_requirements = workingset['citation_requirements']
    workingset_obj.owner = User.objects.filter(pk=workingset['owner_id']).first()
    workingset_obj.group = Group.objects.filter(pk=workingset['group_id']).first()
    workingset_obj.owner_access = workingset['owner_access']
    workingset_obj.group_access = workingset['group_access']
    workingset_obj.world_access = workingset['world_access']
    workingset_obj.created = workingset['created']
    workingset_obj.modified = workingset['modified']
    workingset_obj.concept_informations = workingset['concept_informations']
    
    workingset_obj.concept_version = workingset['concept_version']
    ##The concepts will automatically refer to the latest version. 
    #workingset_obj.concept_version = getWSConceptsHistoryIDs(str(workingset['concept_informations']))
    
    workingset_obj.changeReason = "Working set reverted from version "+str(workingset_history_id)+""

    if workingset_obj:
        # get the historic date this was effective from
        workingset_history_date = workingset['history_date']
        #workingset_obj.save()

        # get tags that were active from the time of the working set effective date
        workingset_tag_maps = getHistoryWorkingsetTagMaps(workingset['id'], workingset_history_date)

        for wtm in workingset_tag_maps:
            has_tags = True

            wtm_obj = WorkingSetTagMap.objects.create(
                workingset=workingset_obj,
                tag=Tag.objects.filter(pk=wtm['tag_id']).first(),
                created_by=User.objects.filter(pk=wtm['created_by_id']).first(),
                created=wtm['created'],
                modified=wtm['modified']
            )
        
        workingset_obj.save()

def deleteWorkingset(pk, user):
    ''' Delete a working set based on a working set id '''
    # get selected concept
    workingset = WorkingSet.objects.get(pk=pk)
    workingset.is_deleted = True
    workingset.deleted = datetime.datetime.now()
    workingset.deleted_by = user
    workingset.changeReason = standardiseChangeReason("Deleted")
    workingset.save()


def deleteWorkingsetRelatedObjects(pk):
    ''' Delete a working set components and tags based on a working set id '''
    # get selected workingset
    workingset = WorkingSet.objects.get(pk=pk)

    # get all the tags attached to the workingset
    workingset_tag_maps = workingset.workingsettagmap_set.all()

    for wtm in workingset_tag_maps:
        if wtm:
            wtm.delete()


    if workingset and workingset_tag_maps:
        #workingset.changeReason = "Tags deleted"
        #workingset.save()
        workingset.save_without_historical_record()


def standardiseChangeReason(reason):
    reason = (reason[:98] + '..') if len(reason) > 98 else reason
    return reason


""" NOT USED.
def saveWorkingsetChangeReason(id, reason):
    workingset = WorkingSet.objects.get(pk=id)
    workingset.changeReason = standardiseChangeReason(reason)
    workingset.save()
"""


def modifyConceptChangeReason(id, reason):
    '''
        Save an historical reason for a concept change.
        By using update_change_reason we avoid having two saves when the first
        derives from a form (i.e. form.save()) which will not save any
        changeReason value. Using another concept.save() after that produces
        two entries in the history, the first with no reason and the second
        with the specified reason.
        This will modify the current history entry and does not increment
        the sequence number.
    '''
    concept = Concept.objects.get(id=id)
    update_change_reason(concept, standardiseChangeReason(reason))


def saveConceptWithChangeReason(id, reason, modified_by_user=None):
    '''
        Save an historical reason for a concept change.
        By using update_change_reason we avoid having two saves when the first
        derives from a form (i.e. form.save()) which will not save any
        changeReason value. Using another concept.save() after that produces
        two entries in the history, the first with no reason and the second
        with the specified reason.
    '''
    concept = Concept.objects.get(id=id)
    if modified_by_user != None:
        concept.modified_by = modified_by_user
        
    concept.changeReason = standardiseChangeReason(reason)
    concept.save()


def saveDependentConceptsChangeReason(concept_ref_id, reason):
    # Not used after stopping update propagation
    # We can send emails - later - to notify users
    # about changes 
    # (care not to send multiple emails for a single update)
    return
    ############################################
    
def saveDependentConceptsChangeReason_OLD(concept_ref_id, reason):
        #self.kwargs['pk'], "Updated component concept #" + self.kwargs['pk'])
    '''
        Save an historical reason for concepts that are affected by a concept
        change.
        This will modify the current history entry and does not increment
        the sequence number.
    '''
    # Get all the dependent concepts.
    concepts = getParentConceptTreeByConceptId(concept_ref_id)
    for concept_id in concepts:
        # The initial concept is already saved, so skip to component save.
        if concept_id['concept_id'] != int(concept_ref_id):
            concept = Concept.objects.get(id=concept_id['concept_id'])
            try:
                concept.modified_by = User.objects.get(username__iexact='system')
            except:
                concept.modified_by = None
            concept.changeReason = standardiseChangeReason(reason)
            concept.save()
         
        # >>>>>>>>>>>>>>>>>
        
        # Now need to get all components which have this concept with the new
        # version number; concepts only.

        version = Concept.objects.get(id=concept_id['concept_id']).history.latest()
        # concept-components only
        components = Component.objects.filter(concept_ref=concept_id['concept_id']).filter(component_type=1)
        for component in components:
            component.concept_ref_history_id = version.pk
            component.save()
            #----------------------------------------------
            # UPDATE codelist/codes under the child concept component directly
            updateChildConceptCodes(concept_id = component.concept_id, 
                    component_id = component.pk,
                    referenced_concept_id = concept_id['concept_id'], 
                    concept_ref_history_id = version.pk,
                    insert_or_update = 'update' )
            #----------------------------------------------

    # working set's functions must be called after concept's ones finish
    # Save a history entry for affected working sets
    saveDependentWorkingsetChangeReason(id, concepts, reason)

def updateChildConceptCodes(concept_id, component_id, referenced_concept_id, 
                            concept_ref_history_id, insert_or_update ):
    # UPDATE codelist/codes under the child concept component directly
    save_child_concept_codes(concept_id = concept_id, 
                    component_id = component_id,
                    referenced_concept_id = referenced_concept_id, 
                    concept_ref_history_id = concept_ref_history_id,
                    insert_or_update = 'update' # insert_or_update
                    )


def saveDependentWorkingsetChangeReason(id, parent_concepts, reason):
    # Not used after stopping update propagation
    #return
    ############################################
    '''
        Save an historical reason for working set that are affected by a concept
        change.
    '''

    parent_concepts_ids = [d['concept_id'] for d in parent_concepts]

    #we should use filter here, bypassed for now!!
    #workingsets = WorkingSet.objects.filter(concept_informations__has_any_keys = parent_concepts_ids)
    workingsets = WorkingSet.objects.all()

    # check workingset if has any of the concepts ids
    # Save a history entry for each workingset.
    workingsets_ids = []
    for workingset in workingsets:
        ws_conceptIDs = getConceptsFromJSON(concepts_json=workingset.concept_informations)
        ws_conceptIDs = [int(x) for x in ws_conceptIDs]
        if any((True for x in parent_concepts_ids if x in ws_conceptIDs)):
            workingsets_ids.append(workingset.pk)
            try:
                workingset.updated_by = User.objects.get(username__iexact='system')
            except:
                workingset.updated_by = None    
            workingset.concept_version = getWSConceptsHistoryIDs(workingset.concept_informations,
                                                                 saved_concept_version=workingset.concept_version,
                                                                 concepts_to_update=list(set(ws_conceptIDs) & set(parent_concepts_ids))
                                                                )
            workingset.changeReason = standardiseChangeReason(reason)
            workingset.save()

def hasCircularReference (child_concept_id, parent_concept_id):
    '''
        Check Circular Reference when adding a child concept.
    '''
    # Get all the dependent concepts.
    concepts = getParentConceptTreeByConceptId(parent_concept_id)
    for concept_id in concepts:
        if concept_id['concept_id'] == child_concept_id :
            return True 
    

    return False
  
def hasConcurrentUdates (concept_id, shown_version_id):
    '''
        Check concurrent updates of a concept.
    '''
    
    # disable for now
    return False
    #############################
    
    latest_history_id = Concept.objects.get(pk=concept_id).history.latest('history_id').history_id

    if shown_version_id != latest_history_id :
        return True
    else: 
        return False          
            
            
def getWSConceptsHistoryIDs(concept_informations, saved_concept_version={}, concepts_to_update=[], 
                            concept_ids_list = []):
    '''
        get Concept latest history ID to json field in the Workingset.
        you can specify a list of concepts to update and ignore the rest
        saved_concept_version=[], concepts_to_update=[] Both should be empty or assigned
    '''
    if concept_informations.strip()=="":
        return {}

    if len(concept_ids_list) == 0:
        concepIDs = getConceptsFromJSON(concepts_json = concept_informations)
        if len(concepIDs) == 0:
            return {}
    else:
        concepIDs = concept_ids_list

    stored_concepts = json.loads(concept_informations, object_pairs_hook=OrderedDict)

    new_concept_version = OrderedDict([])

    # loop for concept info
    for concept_info in stored_concepts:
        for key, value in concept_info.iteritems():
            latest_history_id = Concept.objects.get(pk=key).history.latest('history_id').history_id
            if(len(concepts_to_update)>0 and saved_concept_version):
                if(int(key) in concepts_to_update):
                    new_concept_version[key] = latest_history_id
                else:
                    new_concept_version[key] = saved_concept_version[key]
            else:
                new_concept_version[key] = latest_history_id

    return dict(new_concept_version)


def getWSConceptsVersionsData(concept_informations, submitted_concept_version):
    '''
        prepare Concepts versions.
    '''
    if concept_informations.strip()=="":
        return {}

    concepIDs = getConceptsFromJSON(concepts_json = concept_informations)
    if len(concepIDs) == 0:
        return {}


    stored_concepts = json.loads(concept_informations, object_pairs_hook=OrderedDict)

    new_concept_version = OrderedDict([])

    # loop for concept info
    for concept_info in stored_concepts:
        for key, value in concept_info.iteritems():
            if(submitted_concept_version[key] == "latest"):
                latest_history_id = Concept.objects.get(pk=key).history.latest('history_id').history_id
                new_concept_version[key] = latest_history_id
            else:
                new_concept_version[key] = int(submitted_concept_version[key])

    return dict(new_concept_version)


def restoreWorkingset(pk, user):
    ''' Restore a working set '''
    # get selected working set
    workingset = WorkingSet.objects.get(pk=pk)
    workingset.is_deleted = False
    workingset.deleted = None
    workingset.deleted_by = None
    workingset.changeReason = standardiseChangeReason("Restored")
    workingset.save()
        


def getHistoryConceptTagMaps(concept_id, concept_history_date):
    ''' Get historic concept tag maps that are attached to a concept 
        that were effective from a point in time
    '''

    my_params = {
        'concept_id': concept_id,
        'concept_history_date': concept_history_date
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the tags historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all codes that don't have a
        -- delete event by the specified date.
        SELECT 
            hc.id,
            hc.created,
            hc.modified,
            hc.history_id,
            hc.history_date,
            hc.history_change_reason,
            hc.history_type,
            hc.concept_id,
            hc.created_by_id,
            hc.history_user_id,
            hc.tag_id
        FROM clinicalcode_historicalconcepttagmap AS hc
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the tags for this concept and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalconcepttagmap
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the tags that have been deleted
                -- for this concept.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalconcepttagmap
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hc.history_id = d.history_id
        ORDER BY hc.id
        ''' , my_params)
        col_names = [col[0] for col in cursor.description]
        return [dict(zip(col_names, row)) for row in cursor.fetchall()]


def getHistoryComponents(concept_id, concept_history_date, skip_codes=False, check_published_child_concept=False):
    '''
        Get historic components attached to a concept that were effective from
        a point in time.
    '''
    my_params = {
        'concept_id': concept_id,
        'concept_history_date': concept_history_date
    }
    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the component historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all components that don't have a
        -- delete event by the specified date.
        SELECT *
        FROM clinicalcode_historicalcomponent AS c
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the components for this concept and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalcomponent
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the components that have been deleted
                -- for this concept/timestamp.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalcomponent
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON c.history_id = d.history_id
        ORDER BY c.id
        ''' , my_params)
        columns = [col[0] for col in cursor.description]
        components = [dict(zip(columns, row)) for row in cursor.fetchall()]
        # Modify the logical_type data with the display data in Component.
        # This allows the component display to look the same as on the other
        # pages.
        types = list(t[0] for t in Component.LOGICAL_TYPES)
        for component in components:
            if component['component_type'] in [3, 4]:
                coderegex = getHistoryCodeRegex(component['id'], concept_history_date)
                component['regex_code'] = coderegex['regex_code']
                
            if component['component_type'] == 1:    # concept
                # Adding extra data here to indicate which group the component
                # belongs to (only for concepts).
                component_group_id = Concept.objects.get(id=component['concept_ref_id']).group_id
                if component_group_id is not None:
                    component['group'] = Group.objects.get(id=component_group_id).name
                    
                # if child concept, check if this version is published
                if check_published_child_concept:
                    component['is_published'] = checkIfPublished(Concept, component['concept_ref_id'], component['concept_ref_history_id'])
                    
            logical_type = int(component['logical_type'])
            if logical_type in types:
                logical_type = Component.LOGICAL_TYPES[logical_type - 1][1]
            else:
                logical_type = 'n/a'
            #component['logical_type'] = logical_type
            component['get_logical_type_display'] = logical_type
            #get_logical_type_display
            
            # If we wish to include the popover display of codes available, we will
            # need to add the codelist.codes.all data here for each component.
            if not skip_codes:
                codelist = getHistoryCodeListByComponentId(component['id'], concept_history_date)
                if codelist is not None:
                    codes = getHistoryCodes(codelist['id'], concept_history_date)
                else:
                    codes = []
    
                component['codes'] = codes
            

        
        return components


def getHistoryTags(concept_id, concept_history_date):
    ''' Get historic tags attached to a concept that were effective from a point in time '''

    my_params = {
        'concept_id': concept_id,
        'concept_history_date': concept_history_date
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the tags historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all codes that don't have a
        -- delete event by the specified date.
        SELECT 
            hc.id,
            hc.created,
            hc.modified,
            hc.history_id,
            hc.history_date,
            hc.history_change_reason,
            hc.history_type,
            hc.concept_id,
            hc.created_by_id,
            hc.history_user_id,
            hc.tag_id
        FROM clinicalcode_historicalconcepttagmap AS hc
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the tags for this concept and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalconcepttagmap
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the tags that have been deleted
                -- for this concept.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalconcepttagmap
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hc.history_id = d.history_id
        ORDER BY hc.id
        ''' , my_params)
        
        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]



def getHistoryTags_Workingset(workingset_id, workingset_history_date):
    ''' Get historic tags attached to a workingset that were effective from a point in time '''

    my_params = {
        'workingset_id': workingset_id,
        'workingset_history_date': workingset_history_date
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the tags historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all codes that don't have a
        -- delete event by the specified date.
        SELECT 
            hc.id,
            hc.created,
            hc.modified,
            hc.history_id,
            hc.history_date,
            hc.history_change_reason,
            hc.history_type,
            hc.workingset_id,
            hc.created_by_id,
            hc.history_user_id,
            hc.tag_id
        FROM clinicalcode_historicalworkingsettagmap AS hc
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the tags for this concept and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalworkingsettagmap
                WHERE  (workingset_id = %(workingset_id)s AND 
                        history_date <= %(workingset_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the tags that have been deleted
                -- for this concept.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalworkingsettagmap
                WHERE  (workingset_id = %(workingset_id)s AND 
                        history_date <= %(workingset_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hc.history_id = d.history_id
        ORDER BY hc.id
        ''' , my_params)

        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]



def revertHistoryConcept(user, concept_history_id):
    ''' Revert a selected historical concept and create it as a new concept using an existing concept id '''
    has_components = False
    has_ConceptCodeAttributes = False
    concept = getHistoryConcept(concept_history_id)

    # get selected concept
    concept_obj = Concept.objects.get(pk=concept['id'])
    
    # Don't allow revert if the active object is deleted
    if concept_obj.is_deleted:  raise PermissionDenied 
    
    # update concept with historical information
    concept_obj.name = concept['name']
    concept_obj.description = concept['description']
    concept_obj.created_by = User.objects.filter(pk=concept['created_by_id']).first()
    concept_obj.author = concept['author']
    concept_obj.entry_date = concept['entry_date']
    concept_obj.modified_by = User.objects.filter(pk=user.id).first()
    concept_obj.validation_performed = concept['validation_performed']
    concept_obj.validation_description = concept['validation_description']
    concept_obj.publication_doi = concept['publication_doi']
    concept_obj.publication_link = concept['publication_link']
    concept_obj.secondary_publication_links = concept['secondary_publication_links']
    concept_obj.paper_published = concept['paper_published']
    concept_obj.source_reference = concept['source_reference']
    concept_obj.citation_requirements = concept['citation_requirements']
    concept_obj.coding_system = CodingSystem.objects.filter(pk=concept['coding_system_id']).first()
    concept_obj.created = concept['created']
    concept_obj.modified = concept['modified']
    concept_obj.owner = User.objects.filter(pk=concept['owner_id']).first() 
    concept_obj.group = Group.objects.filter(pk=concept['group_id']).first()   
    concept_obj.owner_access = concept['owner_access']
    concept_obj.group_access = concept['group_access']
    concept_obj.world_access = concept['world_access']
    concept_obj.tags = concept['tags']
    concept_obj.code_attribute_header = concept['code_attribute_header']
    concept_obj.changeReason = "Reverted root historic concept"
    concept_obj.save()
    
    if concept_obj:
        # get the historic date this was effective from
        concept_history_date = concept['history_date']

        # get ConceptCodeAttributes that were active from the time of the concepts effective date
        concept_ConceptCodeAttributes = getHistory_ConceptCodeAttribute(concept_id = concept['id']
                                                           , concept_history_date = concept_history_date
                                                           , code_attribute_header = concept['code_attribute_header']
                                                           , expand_attrs_into_cols = False )
 
        for cca in concept_ConceptCodeAttributes:
            has_ConceptCodeAttributes = True
             
            cca_obj = ConceptCodeAttribute.objects.create(
                            concept=concept_obj,
                            code=cca['code'],
                            attributes=cca['attributes'],
                            created_by=User.objects.filter(pk=cca['created_by_id']).first(),
                            created=cca['created'],
                            modified=cca['modified']
                        )
            
                                    

        # get components that were active from the time of the concepts effective date
        components = getHistoryComponents(concept['id'], concept_history_date, skip_codes=True)

        for com in components:
            has_components = True

            # recreate the historical component
            concept_ref = Concept.objects.filter(pk=com['concept_ref_id']).first()
            concept_ref_history_id = com['concept_ref_history_id']
            # stop REVERT from automatically referring to the latest version of child concepts
            #if(concept_ref is not None):
            #    concept_ref_history_id = Concept.objects.get(id=com['concept_ref_id']).history.latest().pk
                
            com_obj = Component.objects.create(
                comment=com['comment'],
                component_type=com['component_type'],
                concept=concept_obj,
                concept_ref=concept_ref,  #Concept.objects.filter(pk=com['concept_ref_id']).first(),
                created_by=User.objects.filter(pk=com['created_by_id']).first(),
                logical_type=com['logical_type'],
                modified_by=User.objects.filter(pk=com['modified_by_id']).first(),
                name=com['name'],
                created=com['created'],
                modified=com['modified'],
                concept_ref_history_id= concept_ref_history_id    #com['concept_ref_history_id']  
                )

            # check if the historical component was created
            if com_obj:
                # check if it is a code list component
                if com['component_type'] == 1 or com['component_type'] == 2:
                    # get historical code list that was active from the time of the concepts effective date
                    codelist = getHistoryCodeListByComponentId(com['id'], concept_history_date)

                    # recreate historical code list
                    codelist_obj = CodeList.objects.create(
                        component=com_obj,
                        description=codelist['description'],
                        sql_rules=codelist['sql_rules'],
                        created=codelist['created'],
                        modified=codelist['modified'])

                    # check if the historical code list was created
                    if codelist_obj:
                        # get historical codes that were active from the time of the concepts effective date
                        codes = getHistoryCodes(codelist['id'], concept_history_date)

                        for code in codes:
                            # recreate historical code
                            Code.objects.create(
                                code_list=codelist_obj,
                                code=code['code'],
                                description=code['description'])

                # check if it is a Code Regex component
                elif com['component_type'] == 3 or com['component_type'] == 4:
                    codelist_obj = None

                    # get historical code regex that was active from the time of the concepts effective date
                    coderegex = getHistoryCodeRegex(com['id'], concept_history_date)

                    if coderegex['code_list_id'] is not None:
                        # get historical code list that was active from the time of the concepts effective date
                        codelist = getHistoryCodeListById(coderegex['code_list_id'], concept_history_date)

                        # recreate historical code list
                        codelist_obj = CodeList.objects.create(
                            component=com_obj,
                            description=codelist['description'],
                            sql_rules=codelist['sql_rules'],
                            created=codelist['created'],
                            modified=codelist['modified'])

                        if codelist_obj:
                            # get historical codes that were active from the time of the concepts effective date
                            codes = getHistoryCodes(codelist['id'], concept_history_date)

                            for code in codes:
                                # recreate historical code
                                Code.objects.create(
                                    code_list=codelist_obj,
                                    code=code['code'],
                                    description=code['description'])

                    # recreate historical coderegex
                    CodeRegex.objects.create(
                        component=com_obj,
                        regex_type=coderegex['regex_type'],
                        regex_code=coderegex['regex_code'],
                        sql_rules=coderegex['sql_rules'],
                        code_list=codelist_obj)

    # save the concept again because the code lists, code regexes and codes get saved after the concept is saved
    # so we need to reflect these added components in the history
    if has_components or has_ConceptCodeAttributes:
        concept_obj.history.latest().delete() 
        concept_obj.changeReason = "Reverted historic components"
        concept_obj.save()


#====================================================================

def build_sql_parameters(rules): 
    # NOT USED ???
    
    ''' based on rules supplied by jquery querybuilder we need to format the condition value
        strings need '' attached
        dates need to be formatted
        integers left alone'''

    cond_list = []

    for cond in rules['rules']:

        if 'condition' not in cond:
            if cond['operator'] == 'is_null' or cond['operator'] == 'is_not_null' or cond['operator'] == 'is_empty' or cond['operator'] == 'is_not_empty':
                continue
            elif cond['type'] == 'string':
                cond_list.append("'{}'".format(cond['value']))
            elif cond['type'] == 'date':
                if cond['operator'] == 'between' or cond['operator'] == 'not_between':
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value'][0]))
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value'][1]))
                else:
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value']))
            elif cond['type'] == 'datetime':
                if cond['operator'] == 'between' or cond['operator'] == 'not_between': 
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value'][0]))
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value'][1]))
                else:
                    cond_list.append("to_date('{}', 'YYYY-MM-DD')".format(cond['value']))
            elif cond['type'] == 'integer':
                if cond['operator'] == 'between' or cond['operator'] == 'not_between':
                    cond_list.append(cond['value'][0])
                    cond_list.append(cond['value'][1])
                else:
                    cond_list.append(cond['value'])
            elif cond['type'] == 'double':
                if cond['operator'] == 'between' or cond['operator'] == 'not_between':
                    cond_list.append(cond['value'][0])
                    cond_list.append(cond['value'][1])
                else:
                    cond_list.append(cond['value'])
            else:
                cond_list.append("'{}'".format(cond['value']))
        else:
            cond_list = cond_list + build_sql_parameters(cond)

    return cond_list


def is_valid_column_name(name):
    is_valid = False
    
    #t.READ_CODE)
    name = name.replace("t.", "")
    
    try:
        # re.match("^[A-Za-z0-9_-]+$"
        if re.match(r'[\w-]+$', name):
            is_valid = True
        
        if len(name) <=1:
            is_valid =False
               
        if not is_valid:
            raise NameError('NOT is_valid_column_name() error (' + str(name).replace("'", "\'") + ').')    
                 
        return is_valid 
    except Exception as e:
        is_valid = False
        print('NOT is_valid_column_name() error (' + str(e).replace("'", "\'") + ').')
        raise
        return is_valid 


def get_where_query(component_type, code_field, desc_field,
                    search_text, search_params, column_search, regex_type, 
                    regex_code, filter, case_sensitive_search):
# to return string and param list
    '''
        Format a WHERE query from the given parameters.
        Assume that the parameters have already been checked for validity.
        !!! This should not UPPER a standard filter - Y% and y% should produce
            a different set of codes.
    '''
    
    if not is_valid_column_name(code_field): 
        raise NameError('NOT is_valid_column_name() error (' + str(code_field).replace("'", "\'") + ').')
    
    if not is_valid_column_name(desc_field):
        raise NameError('NOT is_valid_column_name() error (' + str(desc_field).replace("'", "\'") + ').')
    
        
    strSQL = ""
    paramList = []
    if regex_type == CodeRegex.SIMPLE:
        if component_type == Component.COMPONENT_TYPE_QUERY_BUILDER:
            # the search here case-insensitive always
            # assume search_text s safe since it was checked against injection before
            strSQL = " WHERE ( %s )" % (search_text)            
            strSQL = strSQL.format(search_params) # seems does nothing ?
            strSQL = strSQL.replace("?", "%s")
            strSQL = strSQL % tuple((get_placeholder(item) for item in search_params))
            paramList.extend(search_params)
            
        elif component_type in (Component.COMPONENT_TYPE_EXPRESSION_SELECT, Component.COMPONENT_TYPE_EXPRESSION):
            if column_search == CodeRegex.CODE:
                # check user choice of case-sensitive
                strSQL = " WHERE %s " % (code_field) if case_sensitive_search else " WHERE UPPER(%s) " % (code_field)  
                strSQL = strSQL + " LIKE  %s " if case_sensitive_search else strSQL + " LIKE  UPPER(%s) " 

                paramList.append(regex_code)
            elif column_search == CodeRegex.DESCRIPTION:                
                # check user choice of case-sensitive
                strSQL = " WHERE %s " % (desc_field) if case_sensitive_search else " WHERE UPPER(%s) " % (desc_field)
                strSQL = strSQL + " LIKE  %s "  if case_sensitive_search else  strSQL + " LIKE  UPPER(%s) " 
                paramList.append(regex_code)
                
    elif regex_type == CodeRegex.POSIX:
        if column_search == CodeRegex.CODE:
            strSQL = " WHERE %s " % (code_field)  
            strSQL = strSQL + " ~  %s "  if case_sensitive_search else strSQL + " ~*  %s "  
            paramList.append(regex_code)
        elif column_search == CodeRegex.DESCRIPTION:
            strSQL = " WHERE %s " % (desc_field)   
            strSQL = strSQL + " ~  %s "  if case_sensitive_search else strSQL + " ~*  %s "  
            paramList.append(regex_code)
            
    if filter:   #???
        strSQL += filter
        
        
    return {'strSQL': strSQL , 'paramList': paramList}

def get_placeholder(param):
    if type(param) is unicode:
        return "UPPER(%s)"
    else:
        return "%s"


def create_codelist_codes(component_type, database_connection_name, table_name, code_field, desc_field, search_text
                          , search_params, column_search, regex_type, regex_code, code_list_id, user_id
                          , filter
                          , case_sensitive_search = False):
    # for Query Builder
    
    # get where query
    where_sql = get_where_query(component_type,
                                "t." + code_field,
                                "t." + desc_field,
                                search_text,
                                search_params,
                                column_search,
                                regex_type,
                                regex_code,
                                filter,
                                case_sensitive_search)

    current_date = now()

    insert_historical_sql = get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql, current_date, user_id)

    with connections[database_connection_name].cursor() as cursor:
        #cursor.execute(insert_historical_sql)
        cursor.execute(insert_historical_sql['strSQL'] , insert_historical_sql['paramList'])



def update_codelist_codes(component_type, database_connection_name, table_name, code_field, desc_field, search_text
                          , search_params, column_search, regex_type, regex_code, code_list_id, user_id
                          , filter
                          , case_sensitive_search = False):
    # for Query Builder
    
    paramList = []
    # get where query
    where_sql_dic = get_where_query(component_type,
                                "t." + code_field,
                                "t." + desc_field,
                                search_text,
                                search_params,
                                column_search,
                                regex_type,
                                regex_code,
                                filter,
                                case_sensitive_search)

    current_date = now()

    update_sql1= "with deleted_rows AS ( "
    update_sql2= "DELETE FROM public.clinicalcode_code c WHERE code_list_id = %s AND NOT EXISTS( " % (str(code_list_id))
    update_sql3= "SELECT 1 FROM %s t " % (table_name)
    #update_sql4= "%s AND c.code = t."+code_field+" and c.description = t."+desc_field+") " % (where_sql)
    update_sql4= where_sql_dic['strSQL'] + " AND c.code = t."+code_field+" and c.description = t."+desc_field+") "
    paramList.extend(where_sql_dic['paramList'])  
    update_sql5= "RETURNING * ) "
    update_sql6= "INSERT INTO public.clinicalcode_historicalcode(id, code, description, history_date, history_type, code_list_id, history_user_id) "
    update_sql7= "SELECT id, code, description, '%s', '-', code_list_id, %s FROM deleted_rows; " % (str(current_date), str(user_id))
    update_sql8_dic= get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql_dic, current_date, user_id)
    paramList.extend(update_sql8_dic['paramList'])

    update_sql = update_sql1+update_sql2+update_sql3+update_sql4+update_sql5+update_sql6+update_sql7+update_sql8_dic['strSQL']
    
    with connections[database_connection_name].cursor() as cursor:
        #cursor.execute(update_sql)
        cursor.execute(update_sql, paramList)


def create_expression_codes(component_type, database_connection_name, table_name, code_field, desc_field
                            , search_text, search_params, column_search, regex_type, regex_code, code_list_id
                            , user_id, filter, case_sensitive_search):

    # get where query
    where_sql = get_where_query(component_type,
                                "t." + code_field,
                                "t." + desc_field,
                                '',
                                '',
                                column_search,
                                regex_type,
                                regex_code,
                                filter,
                                case_sensitive_search)

    current_date = now()

    insert_historical_sql = get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql, current_date, user_id)

    with connections[database_connection_name].cursor() as cursor:
        #cursor.execute(insert_historical_sql)
        cursor.execute(insert_historical_sql['strSQL'] , insert_historical_sql['paramList'])



def get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql, current_date, user_id):
    
    paramList =[]
    
    select_sql = "SELECT t.%s as code, %s as code_list_id, t.%s as description FROM %s t " % (code_field, str(code_list_id), desc_field, table_name)
    select_sql += " LEFT OUTER JOIN public.clinicalcode_code cc ON cc.code = t."+code_field+" and cc.description = t."+desc_field
    select_sql += " AND cc.code_list_id = %s " 
    paramList.append(str(code_list_id))
    #select_sql += "%s " % (where_sql['strSQL'])
    select_sql += where_sql['strSQL']
    paramList.extend(where_sql['paramList'])

    insert_sql = "with saved_rows AS ("
    insert_sql += "INSERT INTO public.clinicalcode_code(code, code_list_id, description) %s and cc.code IS NULL " % (select_sql)
    insert_sql += "RETURNING * ) "
    insert_sql += "INSERT INTO public.clinicalcode_historicalcode(id, code, description, history_date, history_type, code_list_id, history_user_id) "
    insert_sql += "SELECT id, code, description, '%s', '+', code_list_id, %s FROM saved_rows;" % (str(current_date), str(user_id))

    return {'strSQL': insert_sql , 'paramList': paramList}



def update_expression_codes(component_type, database_connection_name, table_name, code_field, desc_field
                            , search_text, search_params, column_search, regex_type, regex_code, code_list_id, user_id, filter
                            , case_sensitive_search):
    
    paramList =[]
    
    # get where query
    where_sql_dic = get_where_query(component_type,
                                "t." + code_field,
                                "t." + desc_field,
                                '',
                                '',
                                column_search,
                                regex_type,
                                regex_code,
                                filter,
                                case_sensitive_search)

    current_date = now()

    update_sql = "with deleted_rows AS ( "
    update_sql += "DELETE FROM public.clinicalcode_code c WHERE code_list_id = %s AND NOT EXISTS( " % (str(code_list_id))
    update_sql += "SELECT 1 FROM %s t " % (table_name)
    #update_sql += "%s AND c.code = t."+code_field+" and c.description = t."+desc_field+") " % (where_sql)
    update_sql += where_sql_dic['strSQL'] + " AND c.code = t."+code_field+" and c.description = t."+desc_field+") "  
    paramList.extend(where_sql_dic['paramList'])
    update_sql += "RETURNING * ) "
    update_sql += "INSERT INTO public.clinicalcode_historicalcode(id, code, description, history_date, history_type, code_list_id, history_user_id) "
    update_sql += "SELECT id, code, description, '%s', '-', code_list_id, %s FROM deleted_rows; " % (str(current_date), str(user_id))

    #update_sql += get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql_dic, current_date, user_id)
    sql_1 = get_codes_insert_query(code_field, code_list_id, desc_field, table_name, where_sql_dic, current_date, user_id)
    update_sql +=  sql_1['strSQL']
    paramList.extend(sql_1['paramList'])
    
    with connections[database_connection_name].cursor() as cursor:
        #cursor.execute(update_sql)
#         print(update_sql)
#         print(paramList)
        cursor.execute(update_sql, paramList)



def search_codes(component_type, database_connection_name, table_name,
                 code_field, desc_field, search_text, search_params,
                 column_search, logical_type, regex_type, regex_code='',
                 filter = '',
                 case_sensitive_search = False):
    '''
        Search code based on SQL LIKE or regex.
    '''
    strSQL = "SELECT DISTINCT %s AS code, %s AS description FROM %s t " % (code_field, desc_field, table_name)
    with connections[database_connection_name].cursor() as cursor:
        paramList = []
        get_where_query_dic = get_where_query(
                                                component_type, code_field, desc_field, search_text,
                                                search_params, column_search, regex_type, regex_code, filter, 
                                                case_sensitive_search)
        strSQL += get_where_query_dic['strSQL']
        strSQL += ' ORDER BY t.%s ' % (code_field)
        paramList.extend(get_where_query_dic['paramList'])
#         print(strSQL)
#         print(paramList)
        cursor.execute(strSQL , paramList)
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def chk_deleted_children(user, set_class, set_id, returnErrors = True
                         , WS_concepts_json = ""
                         , WS_concept_version = ""
                         , set_history_id = None):
    '''
        check if there are any deleted children of a concept or a working set
        THIS DOES NOT CHECK PRMISSIONS
    '''

    errors = dict()

    concepts = []
    permitted = False
    isDeleted = False
    # The Working Set and Concept systems are fundamentally different, so we
    # need to check that here. Why?
    if (set_class == WorkingSet):
        permitted = allowed_to_view(user, WorkingSet, set_id, set_history_id=set_history_id)
        if (not permitted):
            errors[set_id] = 'Working set not permitted.'
        # Need to parse the concept_informations section of the database and use
        # the concepts here to form a list of concept_ref_ids.
        if WS_concepts_json.strip() != "":
            concepts =  getConceptsFromJSON(concepts_json = WS_concepts_json)
        else:
            concepts = getGroupOfConceptsByWorkingsetId_historical(set_id , set_history_id)

        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(int(concept))
        pass
    elif set_class == Phenotype:
        permitted = allowed_to_view(user, Phenotype, set_id)
        if (not permitted):
            errors[set_id] = 'Phenotype not permitted.'
            # Need to parse the concept_informations section of the database and use
            # the concepts here to form a list of concept_ref_ids.
        if WS_concepts_json.strip() != "":
            concepts = [x['concept_id'] for x in json.loads(WS_concepts_json)] #getConceptsFromJSON(concepts_json=WS_concepts_json)
        else:
            concepts = getGroupOfConceptsByPhenotypeId_historical(set_id, set_history_id)

        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(concept[0])
        pass
    elif (set_class == Concept):
        permitted = allowed_to_view(user, Concept, set_id, set_history_id=set_history_id)
        if (not permitted):
            errors[set_id] = 'Concept not permitted.'
            
        # Now, with no sync propagation, we check only one level for permissions
        concepts = get_history_child_concept_components(set_id, concept_history_id=set_history_id)
        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(concept['concept_ref_id'])
            
#         # Need to refer to all the components that have this id as its concept_id.
#         # For each of these we need to create a list of concept ids from the
#         # concept_ref_ids.
#         # Basically, we need the ConceptTree table from concept_unique_codes(SQL).
#         # At the moment we need to extract both the id and ref_id values from 
#         # what is a complete list but incomplete tree.
#         concepts = getConceptTreeByConceptId(set_id)
#         unique_concepts = set()
#         for concept in concepts:
#             unique_concepts.add(concept['concept_idx'])     #concept_id
#             unique_concepts.add(concept['concept_ref_id'])
    else:
        pass
    # In both cases, we end up with a list of concept_ref_ids to which we need
    # view permission to all in order to grant permission.
    
    # Now check all the unique Concepts for deletion (live version).
    AllnotDeleted = True
    for concept in unique_concepts:
        isDeleted = False               
        
        isDeleted = (Concept.objects.filter(Q(id=concept)).exclude(is_deleted=True).count() == 0)
        if(isDeleted):
            errors[concept] = 'Child concept deleted.'
            AllnotDeleted = False
        
            
    if returnErrors:
        return AllnotDeleted, errors
    else:
        return AllnotDeleted


def chk_children_permission_and_deletion(user, set_class, set_id, WS_concepts_json="", set_history_id=None, submitted_concept_version=None):
    '''
        check if there are any deleted/ or not permitted children
            of a concept or a working set.
        Regardless of being superuser.
    '''
    
    from collections import defaultdict
    
    is_ok = False
    error_dict = {}
    
    is_permitted_to_all , error_perms = allowed_to_view_children(user, set_class, set_id
                                                                , returnErrors = True
                                                                , WS_concepts_json = WS_concepts_json
                                                                , WS_concept_version = submitted_concept_version
                                                                , set_history_id=set_history_id)
    children_not_deleted , error_del = chk_deleted_children(user, set_class, set_id
                                                            , returnErrors = True
                                                            , WS_concepts_json = WS_concepts_json
                                                            , WS_concept_version = submitted_concept_version
                                                            , set_history_id=set_history_id)
        
    is_ok = (is_permitted_to_all & children_not_deleted)

    dd = defaultdict(list)
     
    for d in (error_perms, error_del): # you can list as many input dicts as you want here
        for key, value in d.iteritems():
            dd[key].append(value)
     
    error_dict = dict(dd)

    return is_ok, error_dict


##########################################################
def get_concept_structure_Live(concept_id):
    '''
        get_concept_structure_Live
    '''
    with connection.cursor() as cursor:

        cursor.execute("SELECT * FROM get_concept_structure_Live(%s);" , [concept_id])
        
        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]



def getConceptUniqueCodesLive(concept_id):
    concept_id = int(concept_id)
    
    concept_code_structure = get_concept_structure_Live(concept_id)
    df = pd.DataFrame.from_dict(concept_code_structure)
    
    if df.empty:
        columns = ['code' , 'description']
        rows = [tuple(r) for r in df.to_numpy()] 
        net_output = [
                dict(zip(columns, row))
                for row in rows
            ]
        return net_output
    
    #max_depth = df["level_depth"].max()

    df2 = get_all_levels_codes(df , concept_id)
    
    
        
    return_codes = df2[['code' , 'description']]
    return_codes.drop_duplicates(['code' , 'description'])
    return_codes = return_codes[(return_codes['code'] != '')]
    final_code_list = return_codes.sort_values(by=['code'])   
        
#   columns = list(final_code_list.columns.values)
 
    
    columns = ['code' , 'description']
    rows = [tuple(r) for r in final_code_list.to_numpy()] 
    net_output = [
            dict(zip(columns, row))
            for row in rows
        ]

    return net_output


def get_all_levels_codes(df1 , concept_id , level = 1 , includeExclude = None):
    
    df = df1   
    #max_depth = df["level_depth"].max()
        
    level_codes = df[(df['component_type'] != 1) & (df['level_depth'] == level) & (df['concept_id'] == concept_id)]  # & (df['code'] != '')
       
    #-------------------
    child_concepts = df[(df['component_type'] == 1) & (df['level_depth'] == level) & (df['concept_id'] == concept_id)]  # & (df['code'] != '')
    
    if not child_concepts.empty:
        for c in child_concepts.itertuples():
            next_level_codes = get_all_levels_codes(df1 
                                                , concept_id = c.concept_ref_id 
                                                , level = c.level_depth + 1 # go to next level
                                                , includeExclude = c.logical_type)

            level_codes = pd.concat([level_codes , next_level_codes] , ignore_index=True)
    #-------------------
    
    return_codes = get_net_codes(level_codes)
    
    # mask the net codes with their parent include/Exclude flag
    if includeExclude != None:
        return_codes['logical_type'] = [includeExclude] * len(return_codes.index)
        
    return return_codes

#---------------------------------------------------------------------------   
def get_net_codes(dfi):     
    '''
        returns includes codes and after removing excluded codes
    '''
    
    x_codes = dfi[(dfi['logical_type'] == 2)]  # & (dfi['code'] != '') 
    exclude_codes = x_codes.drop_duplicates(['code'])[['code']]
    
    i_codes = dfi[(dfi['logical_type'] == 1) & (~dfi['code'].isin(exclude_codes['code']) )]  # & (dfi['code'] != '') 
    
    include_codes = i_codes.drop_duplicates(['code' , 'description'])
    
    return include_codes


#---------------------------------------------------------------------------
def save_child_concept_codes(concept_id, component_id, referenced_concept_id, 
                            concept_ref_history_id, insert_or_update ):
    # everything is synced to live version
    componentObj = Component.objects.get(pk=component_id)
    if insert_or_update.lower() == 'insert':
        # create codelist obj.       
        code_list = CodeList.objects.create(component=componentObj, description='child-concept')
        
        # create code objects
        # get codes of the re. concept  / for chosen version
        if Concept.objects.get(pk=referenced_concept_id).history.latest().pk == concept_ref_history_id:
            codes = getGroupOfCodesByConceptId(referenced_concept_id)
        else:
            codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id = referenced_concept_id,
                                                    concept_history_id = concept_ref_history_id )

        for row in codes:          
            obj, created = Code.objects.get_or_create(
                                                    code_list = code_list,
                                                    code = row['code'],
                                                    defaults={
                                                        'description': row['description']
                                                    }
                                                    )
        
        
        
        
    elif insert_or_update.lower() == 'update':
        # should be 1 codelist
        code_list = CodeList.objects.get(component=componentObj)
        
        # find the add and remove codes
        if Concept.objects.get(pk=referenced_concept_id).history.latest().pk == concept_ref_history_id:              
            new_codes = getGroupOfCodesByConceptId(referenced_concept_id)
        else:
            new_codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id = referenced_concept_id,
                                                    concept_history_id = concept_ref_history_id )

        new_codes_lst = [d['code'] for d in new_codes]
        # old saved codes
        existing_codes = code_list.codes.order_by('code')
        old_codes = list(existing_codes.values('code'))
        old_codes_lst = [d['code'] for d in old_codes]

        
        # added_codes are in new_codes but not in old_codes
        added_codes = list(set(new_codes_lst) - set(old_codes_lst))
        # deleted_codes are in old_codes but not in new_codes
        deleted_codes = list(set(old_codes_lst) - set(new_codes_lst))

        # delete old codes
        for code in deleted_codes:
            codes_to_del = Code.objects.filter(code_list_id=code_list.pk, code=code)

            for code_to_del in codes_to_del:
                try:
                    code_to_del.delete()
                except ObjectDoesNotExist:
                    code_to_del = None

        # add new codes
        for code in added_codes:
            # check it doesn't already exist
            codes_to_add = Code.objects.filter(code_list_id=code_list.pk, code=code)

            if not codes_to_add:
                Code.objects.create(code_list=code_list,
                                    code=code,
                                    description= next(item for item in new_codes if item["code"] == code)['description']
                                    )
                
#---------------------------------------------------------------------------
def getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_history_id):
    '''
        get unique set of codes for a concept of a specific version id
    '''
    df = pd.DataFrame(columns=['logical_type', 'code', 'description', 'component_name', 'component_id', 'component_type'])
    
    history_concept = getHistoryConcept(concept_history_id)
    concept_history_date = history_concept['history_date']
    
    # get historical components
    components = getHistoryComponents(concept_id, concept_history_date)
    has_components = False
    has_codes = False
    
    i = -1
    for com in components:
        has_components = True
        # each component already contains the logical_type and codes
        codes = com['codes']
        
        # This loop is slow for very long list !!!
        for code in codes:
            has_codes = True
            i = i + 1
            df.loc[i] = [com['logical_type'], 
                         code['code'], code['description'],  # current code
                         com['name'], com['id'], com['component_type']
                        ]

    #------------------------------------------------
    if df.empty:
        columns = ['code' , 'description']
        rows = [tuple(r) for r in df.to_numpy()] 
        net_output = [
                dict(zip(columns, row))
                for row in rows
            ]
        return net_output
    #------------------------------------------------
    
    uniqueCodes = get_net_codes(df)
    return_codes = uniqueCodes[['code' , 'description']]
    return_codes.drop_duplicates(['code' , 'description'])
    return_codes = return_codes[(return_codes['code'] != '')]
    final_code_list = return_codes.sort_values(by=['code'])   
    
    # The codes export must have only one row per unique code. 
    # That is a hard requirement. Event with different descriptions
    final_code_list = final_code_list.groupby('code' , as_index=False).max()
    final_code_list = final_code_list.sort_values(by=['code'])
        
    columns = ['code' , 'description']
    rows = [tuple(r) for r in final_code_list.to_numpy()] 
    net_output = [
            dict(zip(columns, row))
            for row in rows
        ]

    return net_output

#---------------------------------------------------------------------------
############################################################################
def convert_concept_ids_to_WSjson(concept_ids_list , no_attributes=True):
    #""[{\"8\":{\"\":\"\"}},{\"11\":{\"\":\"\"}},{\"15\":{\"\":\"\"}},{\"26\":{\"\":\"\"}}]""
    ret_val = "["
    i = 0
    for c in concept_ids_list:
        ret_val += "," if i>0 else ""
        ret_val += "{\"" + str(c) + "\":{\"\":\"\"}}"
        i += 1
        
    ret_val += "]"
    return ret_val

#---------------------------------------------------------------------------
def isValidWorkingSet(request, working_set):       
    '''
        Check that the Working-Set data is valid.
        
        MUST have the first parameter as a request for the @login_required decorator.
    '''
    is_valid = True
    concept_keys = []
    errors = {}
    attribute_names = {}
    
    if working_set.name.isspace() or len(working_set.name) < 3 or working_set.name is None:
        errors['name'] = "Workingset name should be at least 3 characters"
        is_valid = False
         
    if working_set.author.isspace() or len(working_set.author) < 3 or working_set.author is None:
        errors['author'] = "Author should be at least 3 characters"
        is_valid = False
        
#     if context['publication'].isspace() or len(context['publication']) < 10 or context['publication'] is None:
#         errors['publication'] = "Workingset publication should be at least 10 characters"
#         is_valid = False
        
    if working_set.description.isspace() or len(working_set.description) < 10 or working_set.description is None:
        errors['description'] = "Workingset description should be at least 10 characters"
        is_valid = False
    
    if not working_set.publication_link.isspace()  and len(working_set.publication_link) > 0 and not working_set.publication_link is None:
        # if publication_link is given, it must be a valid URL
        validate = URLValidator()

        try:
            validate(working_set.publication_link)
            #print("String is a valid URL")
        except Exception as exc:
            #print("String is not valid URL")
            errors['publication_link'] = "working_set publication_link is not valid URL"
            is_valid = False
    
    if working_set.concept_informations is not None and len(working_set.concept_informations) > 0:
        if not chkListIsAllIntegers(getConceptsFromJSON(concepts_json=working_set.concept_informations)):
            errors['wrong_concept_id'] = "You must choose a concept from the search dropdown list."
            is_valid = False
        
        decoded_concepts = json.loads(working_set.concept_informations)
    
        # validation the type of input for attributes
        for data in decoded_concepts:
            for key, value in data.iteritems():
                attribute_names[key] = []
                
                for header, concept_data in value.iteritems():
                    #Allow Working sets with zero attributes 
                    if len(value)==1 and header=="" and concept_data=="":
                        continue
                    
                    header_type = header.encode("utf-8").split("|")
                    header = header_type[0]
                    type = header_type[1]
                        
                    if header.strip() == "":
                        errors['header'] = "Specify names of all attributes"
                        is_valid = False
                        
                    if not header in attribute_names[key]:
                        attribute_names[key].append(header)
                    else:
                        errors['attributes'] = "Attributes name must not repeat (" + header + ")"
                        is_valid = False
                      
                    #verify that the attribute name starts with a character
                    if not re.match("^[A-Za-z]", header):
                        errors['attributes_start'] = "Attribute name must start with a character (" + header + ")"
                        is_valid = False 
                        
                    #verify that the attribute name contains only letters, numbers and underscores 
                    if not re.match("^[A-Za-z0-9_]*$", header):
                        errors['attributes_name'] = "Attribute name must contain only alphabet/numbers and underscores (" + header + ")"
                        is_valid = False      
                  
                    #----------------------------------------------------------------------------------------------  
                    if type == "1":  # INT
                        if concept_data !="":   # allows empty values
                            try:
                                int(concept_data)
                            except ValueError:
                                errors['type'] = "The values of attribute(" + header + ") should be integer"
                                is_valid = False
                    elif type == "2":   # FLOAT
                        if concept_data !="":   # allows empty values
                            try:
                                float(concept_data)
                            except ValueError:
                                errors['type'] = "The values of attribute(" + header + ") should be float"
                                is_valid = False
                    elif type.lower() == "type":    # check type is selected
                        errors['type'] = "Choose a type of the attribute"
                        is_valid = False
                        
            if(data.keys()[0] and data.keys()[0].strip() !=""):
                concept_keys.append(data.keys()[0])
            else: 
                errors['empty_id'] = "Fill in concepts inputs by clicking on autocomplete prompt"
                is_valid = False
        
    if len(set(concept_keys)) != len(concept_keys):
        errors['repeated_id'] = "The concepts should not repeat!"
        is_valid = False
    
    return is_valid, errors


#---------------------------------------------------------------------------
def get_history_child_concept_components(concept_id, concept_history_id=None):
    '''
        Get historic components of type=concept 
        attached to a concept for a specific version or live one.
    '''

    if concept_history_id is None:
        # live version
        conceptComp = Component.objects.filter(concept_id=concept_id, component_type=1).values('concept_ref_id' , 'concept_ref_history_id')
        childConcepts = list(conceptComp)
        return childConcepts
    else:
        # old version
        concept_history = getHistoryConcept(concept_history_id)
        concept_history_date = concept_history['history_date']
    
        my_params = {
        'concept_id': concept_id,
        'concept_history_date': concept_history_date
        }
    
        with connection.cursor() as cursor:
            cursor.execute('''
                -- Select all the data from the component historical record for all
                -- the entries that are contained in the JOIN which produces a list of
                -- the latest history IDs for all components that don't have a
                -- delete event by the specified date.
                SELECT c.concept_ref_id, c.concept_ref_history_id
                FROM clinicalcode_historicalcomponent AS c
                INNER JOIN (
                    SELECT a.id, a.history_id
                    FROM (
                        -- Get the list of all the components for this concept and
                        -- before the timestamp and return the latest history ID.
                        SELECT id, MAX(history_id) AS history_id
                        FROM   clinicalcode_historicalcomponent
                        WHERE  (concept_id = %(concept_id)s AND 
                                history_date <= %(concept_history_date)s::timestamptz AND
                                component_type = 1)
                        GROUP BY id
                    ) AS a 
                    LEFT JOIN (
                        -- Get the list of all the components that have been deleted
                        -- for this concept/timestamp.
                        SELECT DISTINCT id
                        FROM   clinicalcode_historicalcomponent
                        WHERE  (concept_id = %(concept_id)s AND 
                                history_date <= %(concept_history_date)s::timestamptz AND
                                history_type = '-' AND
                                component_type = 1)
                    ) AS b
                    -- Join only those from the first group that are not in the deleted
                    -- group.
                    ON a.id = b.id
                    WHERE b.id IS NULL
                ) AS d
                ON c.history_id = d.history_id  AND  c.component_type = 1
                ORDER BY c.id
            ''' , my_params)
            
            columns = [col[0] for col in cursor.description]
            #columns = ['concept_ref_id' , 'concept_ref_history_id']
            childConcepts = [dict(zip(columns
                                   , row
                                   )) for row in cursor.fetchall()]
            
           
            return childConcepts
        
def get_can_edit_subquery(request):
    # check can_edit in SQl - faster way
    
    can_edit_subquery = ""
    if not request.user.is_authenticated():
        can_edit_subquery = " ( FALSE ) can_edit , "   #    2= published only
    else:  
        if settings.CLL_READ_ONLY:
            can_edit_subquery = " ( FALSE ) can_edit , " 
        else:
            if request.user.is_superuser:
                # can_edit_subquery = " ( TRUE ) can_edit , " 
                can_edit_subquery = ''' (CASE WHEN rn=1 AND
                                                (
                                                    COALESCE(is_deleted, FALSE) IS NOT TRUE 
                                                )
                                        THEN TRUE 
                                        ELSE FALSE 
                                        END
                                        ) can_edit ,
                                    '''
            else:
                user_groups = list(request.user.groups.all().values_list('id', flat=True))
                group_access_cond = ""
                if user_groups:
                    group_access_cond = " OR (group_id IN(" + ', '.join(map(str, user_groups)) + ") AND group_access = 3) "
                    
                # since all params here are derived from user object, no need for parameterising here. 
                can_edit_subquery = ''' (CASE WHEN rn=1 AND
                                                (
                                                    owner_id=%s
                                                    OR world_access = 3
                                                    %s
                                                )
                                        THEN TRUE 
                                        ELSE FALSE 
                                        END
                                        ) can_edit ,

                            '''% (str(request.user.id), group_access_cond)
    return can_edit_subquery

                    
def get_visible_live_or_published_concept_versions(request
                                                    , get_live_and_or_published_ver = 3 # 1= live only, 2= published only, 3= live+published
                                                    , searchByName = ""
                                                    , author = ""
                                                    , concept_id_to_exclude = 0
                                                    , exclude_deleted = True
                                                    , filter_cond = ""
                                                    , show_top_version_only = False
                                                    ):
    ''' Get all visible live or published concept versions 
    - return all columns
    '''
    
    #from psycopg2.extensions import AsIs, quote_ident
    
    my_params = []
    
    user_cond = ""
    if not request.user.is_authenticated():
        get_live_and_or_published_ver = 2   #    2= published only
    else:  
        if request.user.is_superuser:
            user_cond = ""
        else:
            user_groups = list(request.user.groups.all().values_list('id', flat=True))
            group_access_cond = ""
            if user_groups:
                group_access_cond = " OR (group_id IN(" + ', '.join(map(str, user_groups)) + ") AND group_access IN(2,3)) "
                
            # since all params here are derived from user object, no need for parameterising here. 
            user_cond = ''' AND (
                                    owner_id=%s 
                                    OR world_access IN(2,3)
                                    %s
                                )
                    '''% (str(request.user.id), group_access_cond)
    
        #my_params.append(user_cond)
    
    can_edit_subquery = get_can_edit_subquery(request)

    where_clause = " WHERE 1=1 "
    
    if concept_id_to_exclude > 0 :
        my_params.append(str(concept_id_to_exclude))
        where_clause += " AND id NOT IN (%s) "
    
    if searchByName != '':
        my_params.append("%"+str(searchByName)+"%")
        where_clause += " AND upper(name) like upper(%s) "
        
    if author != '':
        my_params.append("%"+str(author)+"%")
        where_clause += " AND upper(author) like upper(%s) "
        
        
    if exclude_deleted:
        where_clause += " AND COALESCE(is_deleted, FALSE) IS NOT TRUE "

    if filter_cond.strip() !="":
        where_clause += " AND " + filter_cond

    # --- second where clause  --- 
    if get_live_and_or_published_ver == 1:      # 1= live only
        where_clause_2 = " AND  (rn=1 " + user_cond + " ) "
    elif get_live_and_or_published_ver == 2:    # 2= published only
        where_clause_2 = " AND (is_published=1) "
    elif get_live_and_or_published_ver == 3:    # 3= live+published
        where_clause_2 = " AND (is_published=1 OR  (rn=1 " + user_cond + " )) "
    else:
        raise INVALID_PARAMETER_VALUE
        
    # --- third where clause  --- 
    where_clause_3 = ""
    if show_top_version_only:
        where_clause_3 = " WHERE rn_res = 1 "

    
    with connection.cursor() as cursor:
        cursor.execute("""
                        SELECT 
                        *
                        FROM
                        (
                            SELECT 
                                """
                                + can_edit_subquery +
                                """
                                *
                                , ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn_res
                                , (CASE WHEN is_published=1 THEN 'published' ELSE 'not published' END) published
                                , (SELECT name FROM clinicalcode_codingsystem WHERE id=r.coding_system_id LIMIT 1) coding_system_name
                                , (SELECT username FROM auth_user WHERE id=r.owner_id LIMIT 1) owner_name
                                , (SELECT username FROM auth_user WHERE id=r.created_by_id LIMIT 1) created_by_username
                                , (SELECT username FROM auth_user WHERE id=r.modified_by_id LIMIT 1) modified_by_username
                                , (SELECT username FROM auth_user WHERE id=r.deleted_by_id LIMIT 1) deleted_by_username
                                , (SELECT name FROM auth_group WHERE id=r.group_id LIMIT 1) group_name
                                , (SELECT created FROM clinicalcode_publishedconcept WHERE concept_id=r.id and concept_history_id=r.history_id  LIMIT 1) publish_date
                            FROM
                            (
                            SELECT 
                               ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn,
                               (SELECT count(*) 
                                   FROM clinicalcode_publishedconcept 
                                   WHERE concept_id=t.id and concept_history_id=t.history_id 
                               ) is_published,
                               created, modified, id, name, description, author, entry_date, 
                               validation_performed, validation_description, publication_doi, 
                               publication_link, secondary_publication_links, paper_published, 
                               source_reference, citation_requirements, is_deleted, deleted, 
                               owner_access, group_access, world_access, history_id, history_date, 
                               history_change_reason, history_type, coding_system_id, created_by_id, 
                               deleted_by_id, group_id, history_user_id, modified_by_id, owner_id
                               , tags, code_attribute_header
                            FROM clinicalcode_historicalconcept t
                            ) r
                            """ 
                            + where_clause  
                            + where_clause_2 +
                            """
                        ) rr
                        """
                        + where_clause_3 +
                        """
                        ORDER BY id, history_id desc
                        """, my_params
                        )
        col_names = [col[0] for col in cursor.description]

        return [
            dict(zip(col_names, row))
            for row in cursor.fetchall()
        ]


def get_list_of_visible_concept_ids(data, return_id_or_history_id="both"):
    ''' return list of visible concept/(or phenotypes) ids/versions 
    - data: list of dic is the output of get_visible_live_or_published_concept_versions()
                                    or get_visible_live_or_published_phenotype_versions()
    '''
    
    if return_id_or_history_id.lower().strip() == "id":
        return list(set( [c['id'] for c in data] ))
    elif return_id_or_history_id.lower().strip() == "history_id":
        return list(set( [c['history_id'] for c in data] ))
    else:   #    both
        return [(c['id'], c['history_id']) for c in data]


#=============================================================================
def get_visible_live_or_published_phenotype_versions(request
                                                    , get_live_and_or_published_ver = 3 # 1= live only, 2= published only, 3= live+published
                                                    , searchByName = ""
                                                    , author = ""
                                                    , phenotype_id_to_exclude = 0
                                                    , exclude_deleted = True
                                                    , filter_cond = ""
                                                    , show_top_version_only = False
                                                    ):
    ''' Get all visible live or published phenotype versions 
    - return all columns
    '''
    
    #from psycopg2.extensions import AsIs, quote_ident
    
    my_params = []
    
    user_cond = ""
    if not request.user.is_authenticated():
        get_live_and_or_published_ver = 2   #    2= published only
    else:  
        if request.user.is_superuser:
            user_cond = ""
        else:
            user_groups = list(request.user.groups.all().values_list('id', flat=True))
            group_access_cond = ""
            if user_groups:
                group_access_cond = " OR (group_id IN(" + ', '.join(map(str, user_groups)) + ") AND group_access IN(2,3)) "
                
            # since all params here are derived from user object, no need for parameterising here. 
            user_cond = ''' AND (
                                    owner_id=%s 
                                    OR world_access IN(2,3)
                                    %s
                                )
                    '''% (str(request.user.id), group_access_cond)
    
        #my_params.append(user_cond)
    can_edit_subquery = get_can_edit_subquery(request)
    
    where_clause = " WHERE 1=1 "
    
    if phenotype_id_to_exclude > 0 :
        my_params.append(str(phenotype_id_to_exclude))
        where_clause += " AND id NOT IN (%s) "
    
    if searchByName != '':
        my_params.append("%"+str(searchByName)+"%")
        where_clause += " AND upper(name) like upper(%s) "
        
    if author != '':
        my_params.append("%"+str(author)+"%")
        where_clause += " AND upper(author) like upper(%s) "
        
        
    if exclude_deleted:
        where_clause += " AND COALESCE(is_deleted, FALSE) IS NOT TRUE "

    if filter_cond.strip() !="":
        where_clause += " AND " + filter_cond

    # --- second where clause  --- 
    if get_live_and_or_published_ver == 1:      # 1= live only
        where_clause_2 = " AND  (rn=1 " + user_cond + " ) "
    elif get_live_and_or_published_ver == 2:    # 2= published only
        where_clause_2 = " AND (is_published=1) "
    elif get_live_and_or_published_ver == 3:    # 3= live+published
        where_clause_2 = " AND (is_published=1 OR  (rn=1 " + user_cond + " )) "
    else:
        raise INVALID_PARAMETER_VALUE
        
    # --- third where clause  --- 
    where_clause_3 = ""
    if show_top_version_only:
        where_clause_3 = " WHERE rn_res = 1 "
         
           
    with connection.cursor() as cursor:
        cursor.execute("""
                        SELECT 
                        *
                        FROM
                        (
                            SELECT 
                                """
                                + can_edit_subquery +
                                """
                                *
                                , ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn_res
                                , (CASE WHEN is_published=1 THEN 'published' ELSE 'not published' END) published
                                , (SELECT username FROM auth_user WHERE id=r.owner_id LIMIT 1) owner_name
                                , (SELECT username FROM auth_user WHERE id=r.created_by_id LIMIT 1) created_by_username
                                , (SELECT username FROM auth_user WHERE id=r.updated_by_id LIMIT 1) modified_by_username
                                , (SELECT username FROM auth_user WHERE id=r.deleted_by_id LIMIT 1) deleted_by_username
                                , (SELECT name FROM auth_group WHERE id=r.group_id LIMIT 1) group_name
                                , (SELECT created FROM clinicalcode_publishedphenotype WHERE phenotype_id=r.id and phenotype_history_id=r.history_id  LIMIT 1) publish_date
                            FROM
                            (
                            SELECT 
                               ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn,
                               (SELECT count(*) 
                                   FROM clinicalcode_publishedphenotype 
                                   WHERE phenotype_id=t.id and phenotype_history_id=t.history_id 
                               ) is_published,
                               id, created, modified, title, name, layout, phenotype_uuid, type, 
                               validation, valid_event_data_range,  
                               sex, author, status, hdr_created_date, hdr_modified_date, description, implementation,
                               concept_informations, publication_doi, publication_link, secondary_publication_links, 
                               source_reference, citation_requirements, is_deleted, deleted, 
                               owner_access, group_access, world_access, history_id, history_date, 
                               history_change_reason, history_type, created_by_id, deleted_by_id, 
                               group_id, history_user_id, owner_id, updated_by_id, validation_performed, 
                               phenoflowid, tags, clinical_terminologies, publications
                            FROM clinicalcode_historicalphenotype t
                            ) r
                            """ 
                            + where_clause  
                            + where_clause_2 +
                            """
                        ) rr
                        """
                        + where_clause_3 +
                        """
                        ORDER BY id, history_id desc
                        """, my_params
                        )
        col_names = [col[0] for col in cursor.description]

        return [
            dict(zip(col_names, row))
            for row in cursor.fetchall()
        ]

def getHistoryPhenotype(phenotype_history_id):
    ''' Get historic phenotype based on a phenotype history id '''

    with connection.cursor() as cursor:
        cursor.execute('''SELECT 
        hph.id,
        hph.created,
        hph.modified,
        hph.title,
        hph.name,
        hph.layout,
        hph.phenotype_uuid,
        hph.type,
        hph.validation,
        hph.valid_event_data_range,
        hph.sex,
        hph.author,
        hph.status,
        hph.hdr_created_date,
        hph.hdr_modified_date,
        hph.description,
        hph.concept_informations,
        hph.publication_doi,
        hph.publication_link,
        hph.secondary_publication_links,
        hph.source_reference,
        hph.implementation,
        hph.citation_requirements,
        hph.phenoflowid,
        hph.is_deleted,
        hph.deleted,
        hph.owner_access,
        hph.group_access,
        hph.world_access,
        hph.history_id,
        hph.history_date,
        hph.history_change_reason,
        hph.history_type,
        hph.created_by_id,
        hph.deleted_by_id,
        hph.group_id,
        hph.history_user_id,
        hph.owner_id,
        hph.updated_by_id,
        hph.validation_performed,
        hph.tags,
        hph.clinical_terminologies,
        hph.publications,
        ucb.username as created_by_username,
        umb.username as modified_by_username,
        uhu.username as history_user
        
        FROM clinicalcode_historicalphenotype AS hph
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hph.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hph.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hph.history_user_id
        WHERE (hph.history_id = %s)''' , [phenotype_history_id])

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(izip(col_names, row))

        return row_dict


def getGroupOfConceptsByPhenotypeId_historical(phenotype_id, phenotype_history_id=None):
    '''
        get concept_informations of the specified phenotype 
        - from a specific version (or live version if phenotype_history_id is None) 

    '''
    if phenotype_history_id is None:
        phenotype_history_id = Phenotype.objects.get(pk=phenotype_id).history.latest('history_id').history_id
        
    concept_id_version = []
    concept_informations = json.loads(Phenotype.history.get(id=phenotype_id, history_id=phenotype_history_id).concept_informations)
    
    for c in concept_informations:
        concept_id_version.append((c['concept_id'], c['concept_version_id']))
        
    return concept_id_version




def getPhenotypeConceptJson(concept_ids_list):
    if len(concept_ids_list) < 1:
        return None

    concept_history_ids = getPhenotypeConceptHistoryIDs(concept_ids_list)

    concept_json = []
    for concept_id in concept_ids_list:
        concept_json.append({
            "concept_id": concept_id,
            "concept_version_id": concept_history_ids[concept_id],
            "attributes": []
        })     
    return json.dumps(concept_json)

def getPhenotypeConceptHistoryIDs(concept_ids_list):
    concept_history_ids = {}
    for concept_id in concept_ids_list:
        latest_history_id = Concept.objects.get(pk=concept_id).history.latest('history_id').history_id
        concept_history_ids[concept_id] = latest_history_id
    return concept_history_ids

def get_CodingSystems_from_Phenotype_concept_informations(concept_informations):
        
    concept_id_list = [x['concept_id'] for x in json.loads(concept_informations)] 
    concept_hisoryid_list = [x['concept_version_id'] for x in json.loads(concept_informations)]    
    CodingSystem_ids = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list).order_by().values('coding_system_id').distinct()
    
    return list(CodingSystem_ids.values_list('coding_system_id', flat=True))




def getHistoryDataSource_Phenotype(phenotype_id, phenotype_history_date):
    ''' Get historic DataSources attached to a phenotype that were effective from a point in time '''

    my_params = {
        'phenotype_id': phenotype_id,
        'phenotype_history_date': phenotype_history_date
    }

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the DataSources historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all DataSources that don't have a
        -- delete event by the specified date.
        SELECT 
            hc.id,
            hc.created,
            hc.modified,
            hc.history_id,
            hc.history_date,
            hc.history_change_reason,
            hc.history_type,
            hc.phenotype_id,
            hc.created_by_id,
            hc.history_user_id,
            hc.datasource_id
        FROM clinicalcode_historicalphenotypedatasourcemap AS hc
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the DataSources for this phenotype and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalphenotypedatasourcemap
                WHERE  (phenotype_id = %(phenotype_id)s AND 
                        history_date <= %(phenotype_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the DataSources that have been deleted
                -- for this phenotype.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalphenotypedatasourcemap
                WHERE  (phenotype_id = %(phenotype_id)s AND 
                        history_date <= %(phenotype_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hc.history_id = d.history_id
        ORDER BY hc.id
        ''' , my_params)

        columns = [col[0] for col in cursor.description]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


def get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id):
    '''
        Get the codes of the phenotype concepts
        for a specific version
        Parameters:     request    The request.
                        pk         The phenotype id.
                        phenotype_history_id  The version id
        Returns:        list of Dict with the codes. 
    '''
            
    # here, check live version
    current_ph = Phenotype.objects.get(pk=pk)


    if current_ph.is_deleted == True:
        raise PermissionDenied
    #--------------------------------------------------
    
    current_ph_version = Phenotype.history.get(id=pk, history_id=phenotype_history_id)

    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = getGroupOfConceptsByPhenotypeId_historical(pk, phenotype_history_id)

    titles = (['code', 'description'
               , 'code_attributes'
               , 'coding_system', 'concept_id', 'concept_version_id'
               , 'concept_name'
               , 'phenotype_id', 'phenotype_version_id', 'phenotype_name'
               ]
            )

    codes = []

    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name
        
        rows_no = 0
        concept_codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        #---------
        code_attribute_header = Concept.history.get(id=concept_id, history_id=concept_version_id).code_attribute_header
        concept_history_date = Concept.history.get(id=concept_id, history_id=concept_version_id).history_date
        codes_with_attributes = []
        if code_attribute_header:
            codes_with_attributes = getConceptCodes_withAttributes_HISTORICAL(concept_id = concept_id
                                                                           , concept_history_date = concept_history_date
                                                                           , allCodes = concept_codes
                                                                           , code_attribute_header = code_attribute_header
                                                                           )

            concept_codes = codes_with_attributes
        #---------
        
        for cc in concept_codes:
            rows_no += 1
            attributes_dict = {}
            if code_attribute_header:
                for attr in code_attribute_header:
                    if request.GET.get('format', '').lower() == 'xml':
                        # clean attr names/ remove space, etc
                        attr2 = utils.clean_str_as_db_col_name(attr)
                    else:
                        attr2 = attr
                    attributes_dict[attr2] = cc[attr]
                    
            codes.append(ordr(zip(titles,  
                            [
                                cc['code'],
                                cc['description'].encode('ascii', 'ignore').decode('ascii')
                            ]
                            + [attributes_dict] 
                            + 
                            [
                                concept_coding_system,
                                concept_id,
                                concept_version_id,
                                Concept.history.get(id=concept_id, history_id=concept_version_id).name,
                                current_ph_version.id, current_ph_version.history_id, current_ph_version.name
                            ]
                        )))

        if rows_no == 0:
            codes.append(ordr(zip(titles,  
                            [
                                '',
                                ''
                            ]
                            + [attributes_dict]
                            + 
                            [
                                concept_coding_system,
                                concept_id,
                                concept_version_id,
                                Concept.history.get(id=concept_id, history_id=concept_version_id).name,
                                current_ph_version.id, current_ph_version.history_id, current_ph_version.name
                            ]
                        )))

    return codes


#---------------------------------------------------------------------------
def isValidDataSource(request, datasource):
    is_valid = True
    errors = {}

    if not datasource.name or len(datasource.name) < 3 or datasource.name is None: #TODO CHECK UNIQUE
        errors['name'] = "DataSource name should be at least 3 characters"
        is_valid = False
    
    # Removed for now as not all data sources have uids
    """
    if datasource.uid or len(datasource.uid) < 3 or datasource.uid is None:
        errors['uid'] = "DataSource uid should be at least 3 characters" #TODO CHECK UNIQUE
        is_valid = False
    """
    
    """if not datasource.description or len(datasource.description) < 3 or datasource.description is None:
        errors['description'] = "DataSource description should be at least 3 characters"
        is_valid = False"""
    
    # Removed for now as not all data sources have urls
    """ 
    if len(datasource.url) > 0 and not datasource.url is None:
        validate = URLValidator()
    try:
        validate(datasource.url)
    except Exception as exc:
        errors['url'] = "datasource url is not valid URL"
        is_valid = False"""
    
    return is_valid, errors
#---------------------------------------------------------------------------

#---------------------------------------------------------------------------
def isValidPhenotype(request, phenotype):       
    '''
        Check that the Phenotype data is valid.
        
        MUST have the first parameter as a request for the @login_required decorator.
    '''
    is_valid = True
    concept_keys = []
    errors = {}
    attribute_names = {}
    
    if not phenotype.title or len(phenotype.title) < 3 or phenotype.title is None:
        errors['title'] = "Phenotype title should be at least 3 characters"
        is_valid = False

    if not phenotype.name or len(phenotype.name) < 3 or phenotype.name is None:
        errors['name'] = "Phenotype name should be at least 3 characters"
        is_valid = False
         
    if not phenotype.author or len(phenotype.author) < 3 or phenotype.author is None:
        errors['author'] = "Phenotype author should be at least 3 characters"
        is_valid = False
    
    # Removed for now
    """if not phenotype.layout or len(phenotype.layout) < 3 or phenotype.layout is None:
        errors['layout'] = "Phenotype layout should be at least 3 characters"
        is_valid = False"""
    
    if not phenotype.phenotype_uuid or len(phenotype.phenotype_uuid) < 3 or phenotype.phenotype_uuid is None:
        errors['phenotype_uuid'] = "Phenotype phenotype_uuid should be at least 3 characters"
        is_valid = False
    
    if not phenotype.type or len(phenotype.type) < 3 or phenotype.type is None:
        errors['type'] = "Phenotype type should be at least 3 characters"
        is_valid = False

    if not phenotype.publication_link  and len(phenotype.publication_link) > 0 and not phenotype.publication_link is None:
        validate = URLValidator()
        try:
            validate(phenotype.publication_link)
        except Exception as exc:
            errors['publication_link'] = "Phenotype publication_link is not valid URL"
            is_valid = False
    
    """if phenotype.concept_informations is not None and len(phenotype.concept_informations) > 0:
        if not chkListIsAllIntegers(getConceptsFromJSON(concepts_json=phenotype.concept_informations)):
            errors['wrong_concept_id'] = "You must choose a concept from the search dropdown list."
            is_valid = False

        decoded_concepts = json.loads(phenotype.concept_informations)
        for data in decoded_concepts:
            for key, value in data.iteritems():
                attribute_names[key] = []
                for header, concept_data in value.iteritems():
                    if len(value)==1 and header=="" and concept_data=="":
                        continue
                    
                    header_type = header.encode("utf-8").split("|")
                    header = header_type[0]
                    type = header_type[1]
                        
                    if header.strip() == "":
                        errors['header'] = "Specify names of all attributes"
                        is_valid = False
                        
                    if not header in attribute_names[key]:
                        attribute_names[key].append(header)
                    else:
                        errors['attributes'] = "Attributes name must not repeat (" + header + ")"
                        is_valid = False
                      
                    if not re.match("^[A-Za-z]", header):
                        errors['attributes_start'] = "Attribute name must start with a character (" + header + ")"
                        is_valid = False 
                        
                    if not re.match("^[A-Za-z0-9_]*$", header):
                        errors['attributes_name'] = "Attribute name must contain only alphabet/numbers and underscores (" + header + ")"
                        is_valid = False      
                  
                    if type == "1":  # INT
                        if concept_data !="":   # allows empty values
                            try:
                                int(concept_data)
                            except ValueError:
                                errors['type'] = "The values of attribute(" + header + ") should be integer"
                                is_valid = False
                    elif type == "2":   # FLOAT
                        if concept_data !="":   # allows empty values
                            try:
                                float(concept_data)
                            except ValueError:
                                errors['type'] = "The values of attribute(" + header + ") should be float"
                                is_valid = False
                    elif type.lower() == "type":    # check type is selected
                        errors['type'] = "Choose a type of the attribute"
                        is_valid = False
                        
            if(data.keys()[0] and data.keys()[0].strip() !=""):
                concept_keys.append(data.keys()[0])
            else: 
                errors['empty_id'] = "Fill in concepts inputs by clicking on autocomplete prompt"
                is_valid = False
        
    if len(set(concept_keys)) != len(concept_keys):
        errors['repeated_id'] = "The concepts should not repeat!"
        is_valid = False"""
    
    return is_valid, errors


#---------------------------------------------------------------------------
def getHistory_ConceptCodeAttribute(concept_id, concept_history_date, code_attribute_header, expand_attrs_into_cols = False):
    ''' Get historic ConceptCodeAttributes attached to a concept that were effective from a point in time '''

    my_params = {
        'concept_id': concept_id,
        'concept_history_date': concept_history_date
    }
    
    cols = ''
    if not expand_attrs_into_cols:
        cols = '''
            , hc.id,
            hc.created,
            hc.modified,
            hc.history_id,
            hc.history_date,
            hc.history_change_reason,
            hc.history_type,
            hc.concept_id,
            hc.created_by_id,
            hc.history_user_id
        '''

    with connection.cursor() as cursor:
        cursor.execute('''
        -- Select all the data from the ConceptCodeAttributes historical record for all
        -- the entries that are contained in the JOIN which produces a list of
        -- the latest history IDs for all ConceptCodeAttributes that don't have a
        -- delete event by the specified date.
        SELECT 
            hc.code,
            hc.attributes
           '''
            + cols +
            '''
        FROM clinicalcode_historicalconceptcodeattribute AS hc
        INNER JOIN (
            SELECT a.id, a.history_id
            FROM (
                -- Get the list of all the ConceptCodeAttributes for this concept and
                -- before the timestamp and return the latest history ID.
                SELECT id, MAX(history_id) AS history_id
                FROM   clinicalcode_historicalconceptcodeattribute
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz)
                GROUP BY id
            ) AS a
            LEFT JOIN (
                -- Get the list of all the ConceptCodeAttributes that have been deleted
                -- for this concept.
                SELECT DISTINCT id
                FROM   clinicalcode_historicalconceptcodeattribute
                WHERE  (concept_id = %(concept_id)s AND 
                        history_date <= %(concept_history_date)s::timestamptz AND
                        history_type = '-')
            ) AS b
            -- Join only those from the first group that are not in the deleted
            -- group.
            ON a.id = b.id
            WHERE b.id IS NULL
        ) AS d
        ON hc.history_id = d.history_id
        ORDER BY hc.id
        ''' , my_params)

        if not expand_attrs_into_cols:
            columns = [col[0] for col in cursor.description]
     
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        else:
            columns = ['code'] + [str(a) for a in code_attribute_header]
            return [
                dict(zip(columns, tuple([str(row[0])] + [str(a) for a in row[1]])  ))
                for row in cursor.fetchall()
            ]
        
        
    
        
#---------------------------------------------------------------------------
def getConceptCodes_withAttributes_HISTORICAL(concept_id, concept_history_date, allCodes, code_attribute_header):
    if not code_attribute_header:
        return allCodes
    

    code_attributes = []
    if code_attribute_header:
        code_attributes = getHistory_ConceptCodeAttribute(concept_id, concept_history_date, code_attribute_header, expand_attrs_into_cols = True)
        
    if not code_attributes:
        return allCodes
    
    allCodes_df = pd.DataFrame.from_dict(allCodes)
    code_attributes_df = pd.DataFrame.from_dict(code_attributes)
    
    # left_join_df
    codes_with_attr_df = pd.merge(allCodes_df,
                                  code_attributes_df,
                                  on="code",
                                  how="left",
                                  indicator=True)
        
     
    codes_with_attr_df = codes_with_attr_df.sort_values(by=['code'])
    codes_with_attr_df = codes_with_attr_df.replace(np.nan, '', regex=True)
    codes_with_attr_df = codes_with_attr_df.replace(['None'], '', regex=True)
        
    return  codes_with_attr_df.to_dict('records')

        
        

        