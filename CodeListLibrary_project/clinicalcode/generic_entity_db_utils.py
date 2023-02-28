''' 
    --------------------------------------------------------------------------
    DB Utilities

    --------------------------------------------------------------------------
'''
import ast
import datetime
import json
import re
from collections import OrderedDict
from collections import OrderedDict as ordr
from itertools import *

import numpy as np
import pandas as pd
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist  # , PermissionDenied
from django.core.validators import URLValidator
#from dateutil.parser import parse
from django.db import connection, connections  # , transaction
from django.db.models import Q
from django.utils.timezone import now
from psycopg2.errorcodes import INVALID_PARAMETER_VALUE
from simple_history.utils import update_change_reason
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.db.models.functions import Lower
from string import ascii_letters

from . import utils, tasks
from .models import *
from .permissions import *
from .constants import *
from clinicalcode.models import Template
from clinicalcode import db_utils

#--------- Order queries ---------------
def get_order_from_parameter(parameter):
    if parameter in concept_order_queries:
        return concept_order_queries[parameter]
    return concept_order_default


#------------ API data validation-------

parse_ident = lambda x: int(str(x).strip(ascii_letters))

def validate_api_entry(item, data, expected_type=str):
    """ Attempts to parse the item in data as the expected type
    
        Returns:
            1. any[true, false, none]
                -> True if successful
                -> False if unable to parse
                -> None if item[data] is not indexable
            2. result
                -> returns parsed value if successful
                -> returns a description of the error if failure occurs
    """
    if item in data:
        try:
            datapoint = data[item]
            datapoint = expected_type(datapoint)
            return True, datapoint
        except Exception as e:
            return False, f"Item '{item}' with value '{data[item]}' could not be parsed as type {expected_type}"
    return None, f"Item '{item}' was null"

def apply_entry_if_valid(element, key, data, item, expected_type=str, predicate=None, errors_dict=None):
    """ If the data[item] is a valid type, will set the attribute of the object
        If a predicate is given as a parameter, the data[item] must also pass the defined clause
        If an error_dict is passed, the ValueError will be added to the dict

        Returns:
            1. boolean
                -> describes the success state of the method
            2. any[value, ValueError]
                -> returns the value if successful
                -> returns a descriptive value error on failure
    """
    success, res = validate_api_entry(item, data, expected_type)
    if success is True:
        if predicate is None or predicate(res):
            setattr(element, key, data[item])
            return True, res
        else:
            issue = ValueError(f"Item '{item}' with value '{data[item]}' failed predicate clause")
            if errors_dict is not None:
                errors_dict[key] = str(issue)
            return False, issue
    elif success is False:
        if errors_dict is not None:
            errors_dict[key] = res
        return False, ValueError(res)
    else:
        if errors_dict is not None:
            errors_dict[key] = res
        return False, ValueError(res)

#---------------------------------------

def get_can_edit_subquery(request):
    # check can_edit in SQl - faster way

    can_edit_subquery = ""
    if not request.user.is_authenticated:
        can_edit_subquery = " ( FALSE ) can_edit , "  #    2= published only
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

                            ''' % (str(request.user.id), group_access_cond)
    return can_edit_subquery



def get_list_of_visible_entity_ids(data, return_id_or_history_id="both"):
    ''' return list of visible concept/(or phenotypes) ids/versions 
    - data: list of dic is the output of get_visible_live_or_published_concept_versions()
                                    or get_visible_live_or_published_phenotype_versions()
    '''

    if return_id_or_history_id.lower().strip() == "id":
        return list(set([c['id'] for c in data]))
    elif return_id_or_history_id.lower().strip() == "history_id":
        return list(set([c['history_id'] for c in data]))
    else:  #    both
        return [(c['id'], c['history_id']) for c in data]


def getConceptBrands(request, concept_list):
    '''
        return concept brands 
    '''
    conceptBrands = {}
    concepts = Concept.objects.filter(id__in=concept_list).values('id', 'name', 'group')

    for c in concepts:
        conceptBrands[c['id']] = []  
        if c['group'] != None:
            g = Group.objects.get(pk=c['group'])
            for item in request.BRAND_GROUPS:
                for brand, groups in item.items():
                    if g.name in groups:
                        #conceptBrands[c['id']].append('<img src="{% static "img/brands/' + brand + '/logo.png %}" height="10px" title="' + brand + '" alt="' + brand + '" />')
                        conceptBrands[c['id']].append(brand)

    return conceptBrands



#=============================================================================
 # TO BE CONVERTED TO THE GENERIC ENTITY  .......
def get_visible_live_or_published_generic_entity_versions(request,
                                                    get_live_and_or_published_ver = 3,  # 1= live only, 2= published only, 3= live+published
                                                    search = "",
                                                    author = "",
                                                    entity_id_to_exclude = 0,
                                                    approved_status = None,
                                                    exclude_deleted = True,
                                                    filter_cond = "",
                                                    show_top_version_only = False,
                                                    force_brand = None,
                                                    force_get_live_and_or_published_ver = None,  # used only with no login
                                                    search_name_only = True,
                                                    highlight_result = False,
                                                    do_not_use_FTS = False,
                                                    order_by = None,
                                                    date_range_cond = ""                                           
                                                    ):
    ''' Get all visible live or published entity versions 
    - return all columns
    '''

    search = re.sub(' +', ' ', search.strip()) 

    sql_params = []

    user_cond = ""
    if not request.user.is_authenticated:
        get_live_and_or_published_ver = 2  #    2= published only
        if force_get_live_and_or_published_ver is not None:
            get_live_and_or_published_ver = force_get_live_and_or_published_ver
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
                    ''' % (str(request.user.id), group_access_cond)

        #sql_params.append(user_cond)
    can_edit_subquery = get_can_edit_subquery(request)


    highlight_columns = ""
    if highlight_result:
        # for highlighting
        if search != '':
            sql_params += [str(search)] * 2
            highlight_columns += """ ts_headline('english', coalesce(name, '')
                                            , websearch_to_tsquery('english', %s)
                                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as name_highlighted,  
                
                                    ts_headline('english', coalesce(author, '')
                                            , websearch_to_tsquery('english', %s)
                                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as author_highlighted,                                              
                                """ 
        else:
            highlight_columns += """ name as name_highlighted,              
                                    author as author_highlighted,                                              
                                """ 
                                
                                
                                
    rank_select = " "
    if search != '':               
        if search_name_only:
            # search name field only
            sql_params += [str(search)]
            rank_select += """ 
                        ts_rank(to_tsvector(coalesce(name, '')), websearch_to_tsquery('english', %s)) AS rank_name,
                        """
        else:
            # search all related fields
            sql_params += [str(search)] * 3
            rank_select += """  
                        ts_rank(to_tsvector('english', coalesce(name, '')), websearch_to_tsquery('english', %s)) AS rank_name,            
                        ts_rank(to_tsvector('english', coalesce(author, '')), websearch_to_tsquery('english', %s)) AS rank_author,
                        ts_rank(to_tsvector('english', coalesce(name, '') 
                                            || ' ' || coalesce(author, '') 
                                            || ' ' || coalesce(description, '') 
                                            || ' ' || coalesce(implementation, '') 
                                            || ' ' || coalesce(array_to_string(publications, ','), '') 
                                            )
                                     , websearch_to_tsquery('english', %s)
                                     ) AS rank_all,
                            """



    where_clause = " WHERE 1=1 "

    if entity_id_to_exclude > 0:
        sql_params.append(str(entity_id_to_exclude))
        where_clause += " AND id NOT IN (%s) "

    if search != '':
        if do_not_use_FTS:  # normal search   
            #note: we use iLike here for case-insensitive
            if search_name_only: 
                sql_params.append("%" + str(search) + "%")
                where_clause += " AND name ILIKE %s "
            else:
                sql_params += ["%" + str(search) + "%"] * 5
                where_clause += """ AND (name ILIKE %s OR 
                                        author ILIKE %s OR 
                                        description ILIKE %s OR 
                                        implementation ILIKE %s OR
                                        array_to_string(publications , ',') ILIKE %s                                 
                                        )  
                                """
            
        else:       # Full-Text-Search (FTS)
            if search_name_only:
                # search name field only
                sql_params += [str(search)] 
                where_clause += """ AND (to_tsvector('english',
                                                    coalesce(name, '') 
                                                   ) @@ websearch_to_tsquery('english', %s)                              
                                        )  
                                """                            
            else:
                # search all related fields
                sql_params += [str(search)] 
                where_clause += """ AND (to_tsvector('english', coalesce(name, '') 
                                                    || ' ' || coalesce(author, '') 
                                                    || ' ' || coalesce(description, '') 
                                                    || ' ' || coalesce(implementation, '') 
                                                    || ' ' || coalesce(array_to_string(publications, ','), '') 
                                                   ) @@ websearch_to_tsquery('english', %s)                              
                                        )  
                                """


    if author != '':
        sql_params.append("%" + str(author) + "%")
        where_clause += " AND upper(author) like upper(%s) "

    if exclude_deleted:
        where_clause += " AND COALESCE(is_deleted, FALSE) IS NOT TRUE "

    if filter_cond.strip() != "":
        where_clause += " AND " + filter_cond




    # --- second where clause  ---
    if get_live_and_or_published_ver == 1:  # 1= live only
        where_clause_2 = " AND  (rn=1 " + user_cond + " ) "
    elif get_live_and_or_published_ver == 2:  # 2= published only
        where_clause_2 = " AND (is_published=1) "
    elif get_live_and_or_published_ver == 3:  # 3= live+published
        where_clause_2 = " AND (is_published=1 OR  (rn=1 " + user_cond + " )) "
    else:
        raise INVALID_PARAMETER_VALUE


    # --- third where clause  ---
    where_clause_3 = " WHERE 1=1 "
    if show_top_version_only:
        where_clause_3 += " AND rn_res = 1 "
    if date_range_cond.strip() != "":
        where_clause_3 += date_range_cond


    # --- where clause (publish approval)  ---
    approval_where_clause = " "
    if approved_status:
        approval_where_clause = " AND (approval_status IN(" + ', '.join(map(str, approved_status)) + ")) "  
        


    # --- when in a brand, show only this brand's data
    brand_filter_cond = " "
    brand = request.CURRENT_BRAND
    if force_brand is not None:
        brand = force_brand

    if brand != "":
        brand_collection_ids = get_brand_collection_ids(brand)
        brand_collection_ids = [str(i) for i in brand_collection_ids]

        if brand_collection_ids:
            brand_filter_cond = " WHERE collections && '{" + ','.join(brand_collection_ids) + "}' "


    # order by clause
    order_by = " ORDER BY REPLACE(id, 'PH', '')::INTEGER, history_id desc " if order_by is None else order_by
    if search != '':
        if search_name_only:
            # search name field only
            order_by =  """ 
                            ORDER BY rank_name DESC
                                    , """ + order_by.replace(' ORDER BY ', '')
        else:
            # search all related fields
            if order_by != concept_order_default.replace(" id,", " REPLACE(id, 'PH', '')::INTEGER,"):
                order_by =  """
                                ORDER BY """ + order_by.replace(' ORDER BY ', '') + """, rank_name DESC, rank_author DESC, rank_all DESC 
                            """
            else:
                order_by =  """
                                ORDER BY rank_name DESC, rank_author DESC , rank_all DESC
                            """                            
        
    with connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                """ + highlight_columns + """ 
                """ + rank_select + """                        
                *
                FROM
                (
                    SELECT 
                        """ + can_edit_subquery + """
                        *
                        , ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn_res
                        , (CASE WHEN is_published=1 THEN 'published' ELSE 'not published' END) published
                        , (SELECT username FROM auth_user WHERE id=r.owner_id ) owner_name
                        , (SELECT username FROM auth_user WHERE id=r.created_by_id ) created_by_username
                        , (SELECT username FROM auth_user WHERE id=r.updated_by_id ) modified_by_username
                        , (SELECT username FROM auth_user WHERE id=r.deleted_by_id ) deleted_by_username
                        , (SELECT name FROM auth_group WHERE id=r.group_id ) group_name
                        , (SELECT created FROM clinicalcode_publishedgenericentity WHERE entity_id=r.id and entity_history_id=r.history_id  and approval_status = 2 ) publish_date
                    FROM
                    (SELECT 
                       ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn,
                       (SELECT count(*) 
                           FROM clinicalcode_publishedgenericentity 
                           WHERE entity_id=t.id and entity_history_id=t.history_id and approval_status = 2
                       ) is_published,
                        (SELECT approval_status 
                           FROM clinicalcode_publishedgenericentity 
                           WHERE entity_id=t.id and entity_history_id=t.history_id 
                       ) approval_status,
                       
                       *
                    FROM clinicalcode_historicalgenericentity t
                        """ + brand_filter_cond + """
                    ) r
                    """ + where_clause + [where_clause_2 , approval_where_clause][approval_where_clause.strip() !=""] + """
                ) rr
                """ + where_clause_3 + """
                """ + order_by
                , sql_params)
        
        col_names = [col[0] for col in cursor.description]

        return [dict(list(zip(col_names, row))) for row in cursor.fetchall()]



def get_entity_full_template_data(entity_record, template_id):
    """
    return the entity full data based on the template,
    Add a 'data' key which has all data based on the template ordered
    """
    template = Template.objects.get(pk=template_id)
    definition = json.loads(template.definition)
    
    fields_data = {}
    
    field_definitions = definition['fields']
    for (field_name, field_definition) in field_definitions.items():
        is_base_field = False
        if 'is_base_field' in field_definition:
            if field_definition['is_base_field'] == True:
                is_base_field = True
        
        if is_base_field:
            fields_data[field_name] = field_definition | {'value': entity_record[field_name]}
        else: # custom field
            fields_data[field_name] = field_definition | {'value': entity_record['template_data'][field_name]}
    
        if 'permitted_values' in field_definition:
            fields_data[field_name]['value'] = field_definition['permitted_values'][str(fields_data[field_name]['value'])]

        # html_id, to be used in HTml
        fields_data[field_name]['html_id'] = field_name.replace(' ', '')
        
        # adjust for system_defined types
        # data sources
        if field_definition['field_type'] == 'data_sources':
            data_sources = DataSource.objects.filter(pk=-1)
            entity_data_sources = fields_data[field_name]['value']
            if entity_data_sources:
                data_sources = DataSource.objects.filter(pk__in=entity_data_sources)
                fields_data[field_name]['value'] = data_sources
        
        # tags
        if field_definition['field_type'] == 'tags':
            tags = Tag.objects.filter(pk=-1)
            entity_tags = fields_data[field_name]['value']
            if entity_tags:
                tags = Tag.objects.filter(pk__in=entity_tags, tag_type=1)
                fields_data[field_name]['value'] = tags
        
        # collections
        if field_definition['field_type'] == 'collections':
            collections = Tag.objects.filter(pk=-1)
            entity_collections = fields_data[field_name]['value']
            if entity_collections:
                collections = Tag.objects.filter(pk__in=entity_collections, tag_type=2)
                fields_data[field_name]['value'] = collections
        
        # coding systems
        if field_definition['field_type'] == 'coding_systems': 
            coding_systems = CodingSystem.objects.filter(pk=-1)
            CodingSystem_ids = fields_data[field_name]['value']
            if CodingSystem_ids:
                coding_systems = CodingSystem.objects.filter(pk__in=CodingSystem_ids)
                fields_data[field_name]['value'] = coding_systems    



    # merge base & custom dict
    # entity_record['data'] = base_fields_data | custom_fields_data

    # update base fields for highlighting
    fields_data['name']['value_highlighted'] = entity_record['name_highlighted']
    fields_data['author']['value_highlighted'] = entity_record['author_highlighted'] 
    fields_data['definition']['value_highlighted'] = entity_record['definition_highlighted']
    fields_data['implementation']['value_highlighted'] = entity_record['implementation_highlighted']
    fields_data['publications']['value_highlighted'] = entity_record['publications_highlighted']
    fields_data['validation']['value_highlighted'] = entity_record['validation_highlighted']
        
    entity_record['data'] = fields_data
    
    # now all data/template def is in entity_record['data']
    # so, delete unused items
    #del entity_record['name'] # we need this
    del entity_record['name_highlighted']
    del entity_record['author'] 
    del entity_record['author_highlighted'] 
    del entity_record['definition']
    del entity_record['definition_highlighted']
    del entity_record['implementation']
    del entity_record['implementation_highlighted']
    del entity_record['publications']
    del entity_record['publications_highlighted']
    del entity_record['validation']
    del entity_record['validation_highlighted']
         
    return entity_record

    
    
def get_historical_entity(history_id, highlight_result=False, q_highlight=None, include_template_data=True):
   
    ''' Get historical generic entity based on a history id '''

    sql_params = []

    highlight_columns = ""
    if include_template_data:
        if highlight_result and q_highlight is not None:
            # for highlighting
            if str(q_highlight).strip() != '':
                sql_params += [str(q_highlight)] * 6
                highlight_columns += """ 
                    ts_headline('english', coalesce(hge.name, '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as name_highlighted,  
    
                    ts_headline('english', coalesce(hge.author, '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as author_highlighted,                                              
                   
                    ts_headline('english', coalesce(hge.definition, '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as definition_highlighted,                                              
                                   
                    ts_headline('english', coalesce(hge.implementation, '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as implementation_highlighted,                                              
                                                                  
                    ts_headline('english', coalesce(array_to_string(hge.publications, '^$^'), '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as publications_highlighted,    
                            
                    ts_headline('english', coalesce(hge.validation, '')
                            , websearch_to_tsquery('english', %s)
                            , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as validation_highlighted,                                                                     
                 """
                     
    sql_params.append(history_id)
                                      
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT 
        """ + highlight_columns + """
        hge.id,
        hge.serial_id,
        hge.name,
        hge.author,
        hge.layout,
        hge.status,
        hge.tags,
        hge.collections,
        hge.definition,
        hge.implementation,
        hge.validation,
        hge.publications,        
        hge.citation_requirements,
        hge.internal_comments,  

        hge.template_id,
        hge.template_data::json,
        
        hge.created,
        hge.created_by_id,
        hge.updated,
        hge.updated_by_id,
        hge.is_deleted,
        hge.deleted,
        hge.deleted_by_id,      
        
        hge.owner_id,       
        hge.owner_access,
        hge.group_id,       
        hge.group_access,
        hge.world_access,
        
        hge.history_id,
        hge.history_date,
        hge.history_change_reason,
        hge.history_type,
        hge.history_user_id,

        ucb.username as created_by_username,
        umb.username as modified_by_username,
        uhu.username as history_user
        
        FROM clinicalcode_historicalgenericentity AS hge
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hge.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hge.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hge.history_user_id
        WHERE (hge.history_id = %s)
        """, sql_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(zip(col_names, row))

        if highlight_columns != '':
            row_dict['publications_highlighted'] = row_dict['publications_highlighted'].split('^$^')
        else:
            row_dict['name_highlighted'] = row_dict['name']
            row_dict['author_highlighted'] = row_dict['author']
            row_dict['definition_highlighted'] = row_dict['definition']
            row_dict['implementation_highlighted'] = row_dict['implementation']
            row_dict['publications_highlighted'] = row_dict['publications']
            row_dict['validation_highlighted'] = row_dict['validation']
            
        # Add a 'data' key which has all data based on the template ordered
        if include_template_data:
            full_template_data = get_entity_full_template_data(row_dict, row_dict['template_id'])
            return full_template_data
        else:
            return row_dict

def get_entity_layout(generic_entity_hitory):
    """
    return the entity layout title
    """
    
    entity_layout = [t[1] for t in ENTITY_LAYOUT if t[0]==generic_entity_hitory['layout']][0]
    return entity_layout
    
def get_entity_layout_category(generic_entity_hitory):
    """
    return the category of the entity layout i.e. phenotype, working set, ...
    """
    
    entity_layout = [t[1] for t in ENTITY_LAYOUT if t[0]==generic_entity_hitory['layout']][0]
    entity_layout_category = 'unkwon'
    if entity_layout in [1, 4, 5]:
        entity_layout_category = 'phenotype'
    elif entity_layout in [3]:
        entity_layout_category = 'working set'
    elif entity_layout in [2]:
        entity_layout_category = 'concept'
    
    return entity_layout_category



def apply_filter_condition(query, selected=None, conditions='', data=None, is_authenticated_user=True):

    if query not in filter_queries:
        return None, conditions
    
    qcase = filter_queries[query]
    if qcase == 0:
        # Tags, Collections, Datasource, Clin. Terms (CodingSystem for Pheno)
        if query not in filter_query_model:
            return None, conditions

        sanitised_list = utils.expect_integer_list(selected)
        search_list = [str(i) for i in sanitised_list]
        items = filter_query_model[query].objects.filter(id__in=search_list)
        search_list = list(items.values_list('id', flat=True))
        search_list = [str(i) for i in search_list]

        if len(search_list) > 0:
            conditions += " AND " + query + " && '{" + ','.join(search_list) + "}' "
        return items, conditions
    elif qcase == 1:
        # CodingSystem
        if query not in filter_query_model:
            return None, conditions

        sanitised_list = utils.expect_integer_list(selected)
        search_list = [str(i) for i in sanitised_list]
        items = filter_query_model[query].objects.filter(id__in=search_list)
        search_list = list(items.values_list('id', flat=True))
        search_list = [str(i) for i in search_list]

        if len(search_list) > 0:
            conditions += " AND " + query + " in (" + ','.join(search_list) + ") "
        return items, conditions
    elif qcase == 2:
        # Phenotype type (string field?)
        if data is None:
            return [], conditions

        selected_list = [str(t) for t in selected.split(',')]
        selected_list = list(set(data).intersection(set(selected_list)))
        if len(selected_list) > 0:
            conditions += " AND lower(type) IN('" + "', '".join(selected_list) + "') "
        return selected_list, conditions
    elif qcase == 3:
        # Workingset type (enum, as int field?)
        if data is None:
            return [], conditions
        
        selected_list = utils.expect_integer_list(selected)
        selected_list = [str(i) for i, v in enumerate(data) if v in selected_list]
        if len(selected_list) > 0:
            conditions += " AND type in (" + ','.join(selected_list) + ") "
        return selected_list, conditions
    elif qcase == 4:
        # Daterange
        if isinstance(selected['start'][0], datetime.datetime) and isinstance(selected['end'][0], datetime.datetime):
            if is_authenticated_user:
                date_field = "modified"
            else:  
                date_field = "publish_date"

            conditions += " AND (" + date_field + " >= '" + selected['start'][1] + "' AND " + date_field + " <= '" + selected['end'][1] + "') "
        return selected, conditions
    
    return None, conditions


#-------------------- Pheno types reference data ------------------------#
def get_brand_associated_phenotype_types(request, brand=None):
    """
        Return all phenotype types assoc. with each brand from the filter statistics model
    """
    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    source = 'all_data' if request.user.is_authenticated else 'published_data'
    stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact='phenotype_filters')).stat['phenotype_types']
    stats = [entry for entry in stats if entry['data_scope'] == source][0]['types']

    available_types = Phenotype.history.annotate(type_lower=Lower('type')).values('type_lower').distinct().order_by('type_lower')    
    phenotype_types = [entry[0] for entry in stats]
    phenotype_types = [x for x in phenotype_types if available_types.filter(type_lower=x).exists()]
    sorted_order = {str(entry[0]): entry[1] for entry in stats}

    return phenotype_types, sorted_order

#---------------------------------------------------------------------------

#-------------------- Data sources reference data ------------------------#
def get_data_source_reference(request, brand=None):
    """
        Return all data sources assoc. with each brand from the filter statistics model
    """
    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    source = 'all_data' if request.user.is_authenticated else 'published_data'
    stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact='phenotype_filters')).stat['data_sources']
    stats = [entry for entry in stats if entry['data_scope'] == source][0]['data_source_ids']
    data_source_ids = [entry[0] for entry in stats]

    data_sources = [DataSource.objects.get(id=x) for x in data_source_ids if DataSource.objects.filter(id=x).exists()]
    sorted_order = {str(entry[0]): entry[1] for entry in stats}
    
    return data_sources, sorted_order

#-------------------- Coding system reference data ------------------------#
def get_coding_system_reference(request, brand=None, concept_or_phenotype="concept"):
    """
        Return all coding systems assoc. with each brand from the filter statistics model
    """
    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    source = 'all_data' if request.user.is_authenticated else 'published_data'
    stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact=f"{concept_or_phenotype}_filters")).stat['coding_systems']
    stats = [entry for entry in stats if entry['data_scope'] == source]

    stats = stats[0]['coding_system_ids']
    coding = [entry[0] for entry in stats]
    coding = [CodingSystem.objects.get(id=x) for x in coding if CodingSystem.objects.filter(id=x).exists()]
    sorted_order = {str(entry[0]): entry[1] for entry in stats}
    
    return coding, sorted_order

#----------------------------- Tag reference ------------------------------#
def get_brand_associated_tags(request, excluded_tags=None, brand=None, concept_or_phenotype="concept"):
    """
        Return all tags assoc. with each brand, and exclude those in our list
    """
    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    source = 'all_data' if request.user.is_authenticated else 'published_data'
    stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact=f"{concept_or_phenotype}_filters")).stat['tags']
    stats = [entry for entry in stats if entry['data_scope'] == source][0]['tag_ids']
    tags = [entry[0] for entry in stats]
    
    if tags is not None and excluded_tags is not None:
        tags = [x for x in tags if x not in excluded_tags]
    
    descriptors = [Tag.objects.get(id=x) for x in tags if Tag.objects.filter(id=x).exists()]
    sorted_order = {str(entry[0]): entry[1] for entry in stats}
    
    if descriptors is not None:
        result = {}
        for tag in descriptors:
            result[tag.description] = tag.id

        return result, sorted_order
    
    return {}, sorted_order

#---------------------------------------------------------------------------

def get_brand_collection_ids(brand_name):
    """
        returns list of collections (tags) ids associated with the brand
    """

    if Brand.objects.all().filter(name__iexact=brand_name).exists():
        brand = Brand.objects.get(name__iexact=brand_name)
        brand_collection_ids = list(Tag.objects.filter(collection_brand=brand.id).values_list('id', flat=True))

        return brand_collection_ids
    else:
        return [-1]


def get_brand_associated_collections(request, concept_or_phenotype="concept", brand=None, excluded_collections=None):
    """
        If user is authenticated show all collection IDs, including those that are deleted, as filters.
        If not, show only non-deleted/published entities related collection IDs.
    """
    if brand is None:
        brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'
    
    source = 'all_data' if request.user.is_authenticated else 'published_data'
    stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact=f"{concept_or_phenotype}_filters")).stat['collections']
    stats = [entry for entry in stats if entry['data_scope'] == source][0]['collection_ids']
    collections = [entry[0] for entry in stats]
    
    if collections is not None and excluded_collections is not None:
        collections = [x for x in collections if x not in excluded_collections]
    
    collections = [Tag.objects.get(id=x) for x in collections if Tag.objects.filter(id=x).exists()]
    sorted_order = {str(entry[0]): entry[1] for entry in stats}
    
    return collections, sorted_order



def get_q_highlight(request, q):
    # highlight detail page if only referred from the search page
    
    if is_referred_from_search_page(request):
        return q
    else:
        return ''
    
def is_referred_from_search_page(request):   
    # check if the page is referred from the search page
    
    HTTP_REFERER = request.META.get('HTTP_REFERER')
    if HTTP_REFERER is None:
        return False
    
    url = HTTP_REFERER.split('?')[0]
    url = url.lower()
    if url.endswith('/search/') or url.endswith('/phenotypes/') or url.endswith('/concepts/') or url.endswith('/phenotypeworkingsets/'):
        return True
    else:
        return False
    
    
# getGroupOfConceptsByPhenotypeId_historical
def get_concept_ids_versions_of_historical_phenotype(phenotype_id, phenotype_history_id):
    '''
        get concept_informations of the specified phenotype 
        - from a specific version

    '''
    concept_id_version = []
    concept_informations = GenericEntity.history.get(id=phenotype_id, history_id=phenotype_history_id).template_data['concept_informations']
    if concept_informations:
        for c in concept_informations:
            concept_id_version.append((c['concept_id'], c['concept_version_id']))

    return concept_id_version


def chk_valid_id(request, set_class, pk, chk_permission=False):
    """
        check for valid id of Concepts / Phenotypes / working sets
        (accepts both integers and with prefixes 'C/PH/WS')
    """
    pk = str(pk)
    int_pk = -1
    
    is_valid_id = True
    err = ""
    ret_id = -1

    if str(pk).strip()=='':
        is_valid_id = False
        err = 'ID must be a valid id.'
        
    if not utils.isInt(pk):
        if set_class == Concept and pk[0].upper() == 'C' and utils.isInt(pk[1:]):
            int_pk = int(pk[1:])
        elif set_class == Phenotype and pk[0:2].upper() == 'PH' and utils.isInt(pk[2:]):
            int_pk = int(pk[2:])        
        elif set_class == WorkingSet and pk[0:2].upper() == 'WS' and utils.isInt(pk[2:]):
            int_pk = int(pk[2:])
        elif set_class == PhenotypeWorkingset and pk[0:2].upper() == 'WS' and utils.isInt(pk[2:]):
            int_pk = int(pk[2:])
        else:
            is_valid_id = False
            err = 'ID must be a valid id.'
    else:
        int_pk = int(pk)

    actual_pk = str(pk).upper() if (set_class == PhenotypeWorkingset or set_class == Phenotype) else int_pk
    if set_class.objects.filter(pk=actual_pk).count() == 0:
        is_valid_id = False
        err = 'ID not found.'

    if chk_permission:
        if not allowed_to_edit(request, set_class, actual_pk):
            is_valid_id = False
            err = 'ID must be of a valid accessible entity.'


    if is_valid_id:
        ret_id = set_class.objects.get(pk=actual_pk).id

    return is_valid_id, err, ret_id


# get_phenotype_conceptcodesByVersion
def get_phenotype_concept_codes_by_version(request,
                                        pk,
                                        phenotype_history_id,
                                        target_concept_id=None,
                                        target_concept_history_id=None):
    '''
        Get the codes of the phenotype concepts
        for a specific version
        Parameters:     request    The request.
                        pk         The phenotype id.
                        phenotype_history_id  The version id
                        target_concept_id if you need only one concept's code
                        target_concept_history_id if you need only one concept's code
        Returns:        list of Dict with the codes. 
    '''

    # here, check live version
    current_ph = GenericEntity.objects.get(pk=pk)

    if current_ph.is_deleted == True:
        raise PermissionDenied
    #--------------------------------------------------

    current_ph_version = GenericEntity.history.get(id=pk, history_id=phenotype_history_id)

    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = get_concept_ids_versions_of_historical_phenotype(pk, phenotype_history_id)

    titles = ([
        'code', 'description', 'code_attributes', 'coding_system',
        'concept_id', 'concept_version_id', 'concept_name', 'phenotype_id',
        'phenotype_version_id', 'phenotype_name'
    ])

    codes = []

    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        
        if (target_concept_id is not None and target_concept_history_id is not None):
            if target_concept_id != str(concept_id) and target_concept_history_id != str(concept_version_id):
                continue
        
        concept_ver_name = Concept.history.get(id=concept_id, history_id=concept_version_id).name
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name

        rows_no = 0
        concept_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)
        if concept_codes:
            #---------
            code_attribute_header = Concept.history.get(id=concept_id, history_id=concept_version_id).code_attribute_header
            concept_history_date = Concept.history.get(id=concept_id, history_id=concept_version_id).history_date
            codes_with_attributes = []
            if code_attribute_header:
                codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=concept_id,
                                                                                concept_history_date=concept_history_date,
                                                                                allCodes=concept_codes,
                                                                                code_attribute_header=code_attribute_header
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

                codes.append(
                    ordr(
                        list(
                            zip(titles, [cc['code']
                                       , cc['description'].encode('ascii', 'ignore').decode('ascii')
                                       ] + [attributes_dict] + [
                                        concept_coding_system 
                                        , 'C' + str(concept_id)
                                        , concept_version_id
                                        , concept_ver_name
                                        , current_ph_version.id
                                        , current_ph_version.history_id
                                        , current_ph_version.name
                            ]))))

            if rows_no == 0:
                codes.append(
                    ordr(
                        list(
                            zip(titles, ['', ''] + [attributes_dict] + [
                                concept_coding_system
                                , 'C' + str(concept_id)
                                , concept_version_id
                                , concept_ver_name
                                , current_ph_version.id
                                , current_ph_version.history_id
                                , current_ph_version.name
                            ]))))

    return codes




