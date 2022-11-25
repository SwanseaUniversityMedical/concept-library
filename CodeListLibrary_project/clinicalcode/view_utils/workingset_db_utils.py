import datetime
import re
from collections import OrderedDict as ordr

# from dateutil.parser import parse
from django.db import connection  # , transaction
from psycopg2.errorcodes import INVALID_PARAMETER_VALUE

from clinicalcode.db_utils import standardiseChangeReason, get_can_edit_subquery, get_brand_collection_ids, \
    getGroupOfCodesByConceptId_HISTORICAL, getConceptCodes_withAttributes_HISTORICAL, modify_Entity_ChangeReason
from clinicalcode.models import PhenotypeWorkingset
from .. import utils
from ..constants import *
from ..models import *
from ..permissions import *


def deletePhenotypeWorkingset(pk, user):
    ''' Delete a phenotypeworkingset based on a workingset id '''
    # get selected workingset
    workingset = PhenotypeWorkingset.objects.get(pk=pk)
    workingset.is_deleted = True
    workingset.deleted = datetime.datetime.now()
    workingset.deleted_by = user
    workingset.changeReason = standardiseChangeReason("Deleted")
    workingset.save()


def restorePhenotypeWorkingset(pk, user):
    ''' Restore a phenotypeworkingset '''
    # get selected workingset
    workingset = PhenotypeWorkingset.objects.get(pk=pk)
    workingset.is_deleted = False
    workingset.deleted = None
    workingset.deleted_by = None
    workingset.updated_by = user
    workingset.changeReason = standardiseChangeReason("restored")
    workingset.save()


def validate_workingset_table(workingset_table):
    errors = {}
    is_valid = True
    attribute_names = {}
    decoded_concepts = json.loads(workingset_table)
    for concept in decoded_concepts:
        attribute_names[concept['concept_id']] = []
        for attribute in concept['Attributes']:
            if (attribute['name'] == "" and attribute['value']== ""):
                continue

            if attribute['name'].strip() == "":
                errors['header'] = "Specify names of all attributes"
                is_valid = False

            if not attribute['name'] in attribute_names[concept['concept_id']]:
                attribute_names[concept['concept_id']].append(attribute['name'])
            else:
                errors['attributes'] = "Attributes name must not repeat - now is (" + attribute['name'] + ")"
                is_valid = False

            # verify that the attribute name starts with a character
            if not re.match("^[A-Za-z]", attribute['name']):
                errors['attributes_start'] = "Attribute name must start with a character - now is (" + attribute['name'] + ")"
                is_valid = False

            # verify that the attribute name contains only letters, numbers and underscores
            if not re.match("^([a-zA-Z])([a-zA0-Z9_])*$", attribute['name']):
                errors['attributes_name'] = "Attribute name must contain only alphabet/numbers and underscores (" + attribute['name'] + ")"
                is_valid = False

            if attribute['type'] == "INT":  # INT
                if attribute['value'] != "":  # allows empty values
                    try:
                        int( attribute['value'])
                    except ValueError:
                        errors['type'] = "The values of attribute(" + attribute['name'] + ") should be integer"
                        is_valid = False
            elif  attribute['type'] == "FLOAT":  # FLOAT
                if  attribute['value'] != "":  # allows empty values
                    try:
                        float( attribute['value'])
                    except ValueError:
                        errors['type'] = "The values of attribute(" + attribute['name'] + ") should be float"
                        is_valid = False
            elif attribute['type'].lower() == "TYPE":  # check type is selected
                errors['type'] = "Choose a type of the attribute"
                is_valid = False

    return is_valid, errors

def validate_phenotype_workingset_attribute(attribute):
    """ Attempts to parse the given attribute's value as it's given datatype

        Returns:
            1. boolean
                -> describes success state
            2. any[value, string]
                -> returns value as the proposed datatype if successful
                -> returns a description of the error if failure occurs
    """
    from clinicalcode.constants import PWS_ATTRIBUTE_TYPE_DATATYPE

    proposed_type = attribute['type']
    proposed_value = attribute['value']

    if proposed_type in PWS_ATTRIBUTE_TYPE_DATATYPE:
        expected_type = PWS_ATTRIBUTE_TYPE_DATATYPE[proposed_type]
        try:
            value = expected_type(proposed_value)
            return True, value
        except:
            return False, f"Attribute error: '{proposed_value}' could not be parsed as type '{proposed_type}', expected {expected_type}"

    is_case_issue = proposed_type.upper() in PWS_ATTRIBUTE_TYPE_DATATYPE
    issue = f"Attribute error: Unknown type '{proposed_type}'"
    if is_case_issue:
        issue += f". Did you mean '{proposed_type.upper()}'?"

    return False, issue


# ------------------------------------------------------------------------------#

# -------------------- Working set types reference data ------------------------#
def get_brand_associated_workingset_types(request, brand=None):
    """
        Return all workingset types assoc. with each brand from the filter statistics model
    """
    from clinicalcode.constants import Type_status
    ph_workingset_types_list_ids = list(
        PhenotypeWorkingset.history.values('type').distinct().order_by('type').values_list('type', flat=True))
    ph_workingset_types_list = [t[1] for t in Type_status if t[0] in ph_workingset_types_list_ids]

    return ph_workingset_types_list_ids, ph_workingset_types_list

    """ Once we finalise field type of types for both pheno and concept & incl. statistics """
    # if brand is None:
    #     brand = request.CURRENT_BRAND if request.CURRENT_BRAND is not None and request.CURRENT_BRAND != '' else 'ALL'

    # source = 'all_data' if request.user.is_authenticated else 'published_data'
    # stats = Statistics.objects.get(Q(org__iexact=brand) & Q(type__iexact='phenotype_filters')).stat['workingset_types']
    # stats = [entry for entry in stats if entry['data_scope'] == source][0]['types']

    # available_types = PhenotypeWorkingset.history.annotate(type_lower=Lower('type')).values('type_lower').distinct().order_by('type_lower')
    # workingset_types = [entry[0] for entry in stats]
    # workingset_types = [x for x in workingset_types if available_types.filter(type_lower=x).exists()]
    # sorted_order = {str(entry[0]): entry[1] for entry in stats}

    # return workingset_types, sorted_order


# =============================================================================
def get_visible_live_or_published_phenotype_workingset_versions(request,
                                                                get_live_and_or_published_ver=3,
                                                                # 1= live only, 2= published only, 3= live+published
                                                                search="",
                                                                author="",
                                                                workingset_id_to_exclude=0,
                                                                approved_status=None,
                                                                exclude_deleted=True,
                                                                filter_cond="",
                                                                show_top_version_only=False,
                                                                force_brand=None,
                                                                force_get_live_and_or_published_ver=None,
                                                                # used only with no login
                                                                search_name_only=True,
                                                                highlight_result=False,
                                                                do_not_use_FTS=False,
                                                                order_by=None
                                                                ):
    ''' Get all visible live or published workingset versions
    - return all columns
    '''

    search = re.sub(' +', ' ', search.strip())

    sql_params = []

    user_cond = ""
    if not request.user.is_authenticated:
        get_live_and_or_published_ver = 2  # 2= published only
        if force_get_live_and_or_published_ver is not None:
            get_live_and_or_published_ver = force_get_live_and_or_published_ver
    else:
        if request.user.is_superuser:
            user_cond = ""
        else:
            user_groups = list(request.user.groups.all().values_list('id', flat=True))
            group_access_cond = ""
            if user_groups:
                group_access_cond = " OR (group_id IN(" + ', '.join(
                    map(str, user_groups)) + ") AND group_access IN(2,3)) "

            # since all params here are derived from user object, no need for parameterising here.
            user_cond = ''' AND (
                                    owner_id=%s 
                                    OR world_access IN(2,3)
                                    %s
                                )
                    ''' % (str(request.user.id), group_access_cond)

        # sql_params.append(user_cond)
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
                                            || ' ' || coalesce(array_to_string(publications, ','), '') 
                                            )
                                     , websearch_to_tsquery('english', %s)
                                     ) AS rank_all,
                            """

    where_clause = " WHERE 1=1 "

    if workingset_id_to_exclude > 0:
        sql_params.append(str(workingset_id_to_exclude))
        where_clause += " AND id NOT IN (%s) "

    if search != '':
        if do_not_use_FTS:  # normal search
            # note: we use iLike here for case-insensitive
            if search_name_only:
                sql_params.append("%" + str(search) + "%")
                where_clause += " AND name ILIKE %s "
            else:
                sql_params += ["%" + str(search) + "%"] * 5
                where_clause += """ AND (name ILIKE %s OR 
                                        author ILIKE %s OR 
                                        description ILIKE %s OR 
                                        array_to_string(publications , ',') ILIKE %s                                 
                                        )  
                                """

        else:  # Full-Text-Search (FTS)
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
    order_by = " ORDER BY REPLACE(id, 'WS', '')::INTEGER, history_id DESC " if order_by is None else order_by
    if search != '':
        if search_name_only:
            # search name field only
            order_by = """ 
                            ORDER BY rank_name DESC
                                    , """ + order_by.replace(' ORDER BY ', '')
        else:
            # search all related fields
            if order_by != concept_order_default.replace(" id,", " REPLACE(id, 'WS', '')::INTEGER,"):
                order_by = """
                                ORDER BY """ + order_by.replace(' ORDER BY ', '') + """ , rank_name DESC, rank_author DESC , rank_all DESC
                            """
            else:
                order_by = """
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
                                , (SELECT created FROM clinicalcode_publishedworkingset WHERE workingset_id=r.id and workingset_history_id=r.history_id  and approval_status = 2 ) publish_date
                            FROM
                            (SELECT 
                               ROW_NUMBER () OVER (PARTITION BY id ORDER BY history_id desc) rn,
                               (SELECT count(*) 
                                   FROM clinicalcode_publishedworkingset 
                                   WHERE workingset_id=t.id and workingset_history_id=t.history_id and approval_status = 2
                               ) is_published,
                                (SELECT approval_status 
                                   FROM clinicalcode_publishedworkingset 
                                   WHERE workingset_id=t.id and workingset_history_id=t.history_id 
                               ) approval_status,

                               id, name, type, tags, collections, publications, author, citation_requirements, description, 
                               data_sources, phenotypes_concepts_data::json, 
                               is_deleted, deleted, owner_access, group_access, world_access, 
                               created, modified, 
                               history_id, history_date, history_change_reason, history_type, 
                               created_by_id, deleted_by_id, group_id, history_user_id, owner_id, updated_by_id

                            FROM clinicalcode_historicalphenotypeworkingset t
                                """ + brand_filter_cond + """
                            ) r
                            """ + where_clause + [where_clause_2, approval_where_clause][
                approval_where_clause.strip() != ""] + """
                        ) rr
                        """ + where_clause_3 + """
                        """ + order_by
            , sql_params)

        col_names = [col[0] for col in cursor.description]

        return [dict(list(zip(col_names, row))) for row in cursor.fetchall()]


def getHistoryPhenotypeWorkingset(workingset_history_id, highlight_result=False, q_highlight=None):
    ''' Get historic phenotypeworkingset based on a workingset history id '''

    sql_params = []
    highlight_columns = ""
    if highlight_result and q_highlight is not None:
        # for highlighting
        if str(q_highlight).strip() != '':
            sql_params += [str(q_highlight)] * 4
            highlight_columns += """ 
                ts_headline('english', coalesce(hw.name, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as name_highlighted,  

                ts_headline('english', coalesce(hw.author, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as author_highlighted,                                              

                ts_headline('english', coalesce(hw.description, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as description_highlighted,                                                                                            

                ts_headline('english', coalesce(array_to_string(hw.publications, '^$^'), '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as publications_highlighted,                                              
             """

    sql_params.append(workingset_history_id)

    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT 
        """ + highlight_columns + """
        hw.created,
        hw.modified,
        hw.id,
        hw.name,
        hw.description,
        hw.author,
        hw.publications,
        hw.citation_requirements,
        hw.owner_id,
        hw.group_id,
        hw.tags,
        hw.type,
        hw.data_sources,
        hw.collections,
        hw.owner_access,
        hw.group_access,
        hw.world_access,
        hw.phenotypes_concepts_data::json,
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
        FROM clinicalcode_historicalphenotypeworkingset AS hw
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hw.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hw.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hw.history_user_id
        WHERE (hw.history_id = %s)""", sql_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(zip(col_names, row))

        if highlight_columns != '':
            row_dict['publications_highlighted'] = row_dict['publications_highlighted'].split('^$^')
        else:
            row_dict['name_highlighted'] = row_dict['name']
            row_dict['author_highlighted'] = row_dict['author']
            row_dict['description_highlighted'] = row_dict['description']
            row_dict['publications_highlighted'] = row_dict['publications']

        return row_dict


def get_working_set_codes_by_version(request,
                                     pk,
                                     workingset_history_id,
                                     target_concept_id=None,
                                     target_concept_history_id=None):
    '''
        Get the codes of the phenotype working set concepts
        for a specific version
        Parameters:     request    The request.
                        pk         The working set id.
                        workingset_history_id  The version id
                        target_concept_id if you need only one concept's code
                        target_concept_history_id if you need only one concept's code
        Returns:        list of Dict with the codes.
    '''

    # here, check live version is not deleted
    if PhenotypeWorkingset.objects.get(pk=pk).is_deleted == True:
        raise PermissionDenied
    # --------------------------------------------------

    current_ws_version = PhenotypeWorkingset.history.get(id=pk, history_id=workingset_history_id)

    phenotypes_concepts_data = current_ws_version.phenotypes_concepts_data

    attributes_titles = []
    if phenotypes_concepts_data:
        attr_sample = phenotypes_concepts_data[0]["Attributes"]
        attributes_titles = [x["name"] for x in attr_sample]

    titles = (['code', 'description', 'code_attributes', 'coding_system']
              + ['concept_id', 'concept_version_id', 'concept_name']
              + ['phenotype_id', 'phenotype_version_id', 'phenotype_name']
              + ['workingset_id', 'workingset_version_id', 'workingset_name']
              + attributes_titles
              )

    codes = []
    for concept in phenotypes_concepts_data:
        concept_id = int(concept["concept_id"].replace("C", ""))
        concept_version_id = concept["concept_version_id"]

        if (target_concept_id is not None and target_concept_history_id is not None):
            if target_concept_id != str(concept_id) and target_concept_history_id != str(concept_version_id):
                continue

        concept_name = Concept.history.get(id=concept_id, history_id=concept_version_id).name
        concept_coding_system = Concept.history.get(id=concept_id, history_id=concept_version_id).coding_system.name

        phenotype_id = concept["phenotype_id"]
        phenotype_version_id = concept["phenotype_version_id"]
        phenotype_name = Phenotype.history.get(id=phenotype_id, history_id=phenotype_version_id).name

        attributes_values = []
        if attributes_titles:
            attributes_values = [x["value"] for x in concept["Attributes"]]

        rows_no = 0
        concept_codes = getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)
        if concept_codes:
            # ---------
            code_attribute_header = Concept.history.get(id=concept_id,
                                                        history_id=concept_version_id).code_attribute_header
            concept_history_date = Concept.history.get(id=concept_id, history_id=concept_version_id).history_date
            codes_with_attributes = []
            if code_attribute_header:
                codes_with_attributes = getConceptCodes_withAttributes_HISTORICAL(concept_id=concept_id,
                                                                                  concept_history_date=concept_history_date,
                                                                                  allCodes=concept_codes,
                                                                                  code_attribute_header=code_attribute_header
                                                                                  )


                concept_codes = codes_with_attributes
            # ---------

        for cc in concept_codes:
            rows_no += 1
            code_attributes_dict = {}
            if code_attribute_header:
                for attr in code_attribute_header:
                    if request.GET.get('format', '').lower() == 'xml':
                        # clean attr names/ remove space, etc
                        attr2 = utils.clean_str_as_db_col_name(attr)
                    else:
                        attr2 = attr
                    code_attributes_dict[attr2] = cc[attr]

            codes.append(
                ordr(
                    list(
                        zip(titles, [cc['code']
                            , cc['description'].encode('ascii', 'ignore').decode('ascii')
                                     ] + [code_attributes_dict] + [
                                concept_coding_system
                                , 'C' + str(concept_id)
                                , concept_version_id
                                , concept_name
                                , phenotype_id
                                , phenotype_version_id
                                , phenotype_name
                                , current_ws_version.id
                                , current_ws_version.history_id
                                , current_ws_version.name
                            ]
                            + attributes_values
                            )
                    )
                )
            )

        if rows_no == 0:
            codes.append(
                ordr(
                    list(
                        zip(titles, [''
                            , ''] + [code_attributes_dict] + [
                                concept_coding_system
                                , 'C' + str(concept_id)
                                , concept_version_id
                                , concept_name
                                , phenotype_id
                                , phenotype_version_id
                                , phenotype_name
                                , current_ws_version.id
                                , current_ws_version.history_id
                                , current_ws_version.name
                            ]
                            + attributes_values
                            )
                    )
                )
            )

    return codes


def getGroupOfConceptsByPhenotypeWorkingsetId_historical(workingset_id, workingset_history_id=None):
    '''
        get phenotypes_concepts_data of the specified phenotype working set
        - from a specific version (or live version if workingset_history_id is None)
    '''
    if workingset_history_id is None:
        workingset_history_id = PhenotypeWorkingset.objects.get(pk=workingset_id).history.latest('history_id').history_id

    concepts = []
    concept_informations = PhenotypeWorkingset.history.get(id=workingset_id, history_id=workingset_history_id).phenotypes_concepts_data
    for concept in concept_informations:
        concepts.append((concept['concept_id'], concept['concept_version_id']))

    return concepts


def getHistoryPhenotypeWorkingset(workingset_history_id, highlight_result=False, q_highlight=None):
    ''' Get historic phenotypeworkingset based on a workingset history id '''

    sql_params = []
    highlight_columns = ""
    if highlight_result and q_highlight is not None:
        # for highlighting
        if str(q_highlight).strip() != '':
            sql_params += [str(q_highlight)] * 4
            highlight_columns += """ 
                ts_headline('english', coalesce(hw.name, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as name_highlighted,  

                ts_headline('english', coalesce(hw.author, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as author_highlighted,                                              

                ts_headline('english', coalesce(hw.description, '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=hightlight-txt > ", StopSel="</b>"') as description_highlighted,                                                                                            

                ts_headline('english', coalesce(array_to_string(hw.publications, '^$^'), '')
                        , websearch_to_tsquery('english', %s)
                        , 'HighlightAll=TRUE, StartSel="<b class=''hightlight-txt''>", StopSel="</b>"') as publications_highlighted,                                              
             """

    sql_params.append(workingset_history_id)

    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT 
        """ + highlight_columns + """
        hw.created,
        hw.modified,
        hw.id,
        hw.name,
        hw.description,
        hw.author,
        hw.publications,
        hw.citation_requirements,
        hw.owner_id,
        hw.group_id,
        hw.tags,
        hw.type,
        hw.data_sources,
        hw.collections,
        hw.owner_access,
        hw.group_access,
        hw.world_access,
        hw.phenotypes_concepts_data::json,
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
        FROM clinicalcode_historicalphenotypeworkingset AS hw
        LEFT OUTER JOIN auth_user AS ucb on ucb.id = hw.created_by_id
        LEFT OUTER JOIN auth_user AS umb on umb.id = hw.updated_by_id
        LEFT OUTER JOIN auth_user AS uhu on uhu.id = hw.history_user_id
        WHERE (hw.history_id = %s)""", sql_params)

        col_names = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        row_dict = dict(zip(col_names, row))

        if highlight_columns != '':
            row_dict['publications_highlighted'] = row_dict['publications_highlighted'].split('^$^')
        else:
            row_dict['name_highlighted'] = row_dict['name']
            row_dict['author_highlighted'] = row_dict['author']
            row_dict['description_highlighted'] = row_dict['description']
            row_dict['publications_highlighted'] = row_dict['publications']

        return row_dict