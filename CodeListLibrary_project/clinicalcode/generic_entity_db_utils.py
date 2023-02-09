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
                       
                       id, created, modified, name, layout, phenotype_uuid, type, 
                       validation, valid_event_data_range,  
                       sex, author, status, hdr_created_date, hdr_modified_date, description, implementation,
                       concept_informations::json, publication_doi, publication_link, secondary_publication_links, 
                       source_reference, citation_requirements, is_deleted, deleted, 
                       owner_access, group_access, world_access, history_id, history_date, 
                       history_change_reason, history_type, created_by_id, deleted_by_id, 
                       group_id, history_user_id, owner_id, updated_by_id, validation_performed, 
                       phenoflowid, tags, collections, clinical_terminologies, publications, data_sources
                    FROM clinicalcode_genericentity t
                        """ + brand_filter_cond + """
                    ) r
                    """ + where_clause + [where_clause_2 , approval_where_clause][approval_where_clause.strip() !=""] + """
                ) rr
                """ + where_clause_3 + """
                """ + order_by
                , sql_params)
        
        col_names = [col[0] for col in cursor.description]

        return [dict(list(zip(col_names, row))) for row in cursor.fetchall()]



 # TO BE CONVERTED TO THE GENERIC ENTITY  .......
def getHistoryGenericEntity(phenotype_history_id, highlight_result=False, q_highlight=None):
   
    ''' Get historic phenotype based on a phenotype history id '''

    sql_params = []

    highlight_columns = ""
    if highlight_result and q_highlight is not None:
        # for highlighting
        if str(q_highlight).strip() != '':
            sql_params += [str(q_highlight)] * 6
            highlight_columns += """ 
                ts_headline('english', coalesce(hph.name, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as name_highlighted,  

                ts_headline('english', coalesce(hph.author, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as author_highlighted,                                              
               
                ts_headline('english', coalesce(hph.description, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as description_highlighted,                                              
                               
                ts_headline('english', coalesce(hph.implementation, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as implementation_highlighted,                                              
                                                              
                ts_headline('english', coalesce(array_to_string(hph.publications, '^$^'), '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as publications_highlighted,    
                        
                ts_headline('english', coalesce(hph.validation, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as validation_highlighted,                                                                     
             """
                     
    sql_params.append(phenotype_history_id)
                        
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT 
        """ + highlight_columns + """
        hph.id,
        hph.created,
        hph.modified,
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
        hph.concept_informations::json,
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
        hph.collections,
        hph.clinical_terminologies,
        hph.publications,
        hph.data_sources,
        ucb.username as created_by_username,
        umb.username as modified_by_username,
        uhu.username as history_user
        
        FROM clinicalcode_historicalphenotype AS hph
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hph.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hph.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hph.history_user_id
        WHERE (hph.history_id = %s)
        """, sql_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(zip(col_names, row))

        if highlight_columns != '':
            row_dict['publications_highlighted'] = row_dict['publications_highlighted'].split('^$^')
        else:
            row_dict['name_highlighted'] = row_dict['name']
            row_dict['author_highlighted'] = row_dict['author']
            row_dict['description_highlighted'] = row_dict['description']
            row_dict['implementation_highlighted'] = row_dict['implementation']
            row_dict['publications_highlighted'] = row_dict['publications']
            row_dict['validation_highlighted'] = row_dict['validation']
            
        return row_dict


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
    if url.endswith('/phenotypes/') or url.endswith('/concepts/') or url.endswith('/phenotypeworkingsets/'):
        return True
    else:
        return False
    
    
