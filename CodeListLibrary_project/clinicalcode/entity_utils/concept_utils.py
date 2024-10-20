from django.db import connection
from django.db.models import ForeignKey
from django.http.request import HttpRequest
from rest_framework.request import Request as RESTRequest

import json

from ..models.GenericEntity import GenericEntity
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from ..models.ConceptReviewStatus import ConceptReviewStatus

from . import gen_utils, model_utils, permission_utils
from .constants import (
    USERDATA_MODELS, TAG_TYPE, HISTORICAL_HIDDEN_FIELDS,
    CLINICAL_RULE_TYPE, CLINICAL_CODE_SOURCE, APPROVAL_STATUS
)

def is_concept_published(concept_id, version_id):
    """
    Checks whether a Concept is published

    Will return true if:
        1. The Concept is currently published directly via a legacy system
        2. The Concept is currently owned by a Published Phenotype that's published
        3. The Concept is included in a historic Published Phenotype

    Args:
        concept_id (int): the Concept's id
        version_id (int): the Concept's history_id

    Returns:
        bool: Reflects published status

    """
    concept_id = gen_utils.parse_int(concept_id, None)
    version_id = gen_utils.parse_int(version_id, None)
    if concept_id is None or version_id is None:
        return False

    historical_concept = Concept.history.filter(id=concept_id, history_id=version_id)
    if not historical_concept.exists():
        return False

    directly_published = PublishedConcept.objects.filter(concept_id=concept_id, concept_history_id=version_id)
    if directly_published.exists():
        return True
    
    historical_concept = historical_concept.first()
    phenotype = historical_concept.instance.phenotype_owner
    if phenotype is not None and phenotype.publish_status == APPROVAL_STATUS.APPROVED:
        template_data = phenotype.template_data
        concept_information = template_data.get('concept_information') if isinstance(template_data, dict) else None
        if concept_information:
            for item in concept_information:
                cid = item.get('concept_id')
                cvd = item.get('concept_version_id')
                if cid == concept_id and cvd == version_id:
                    return True

    with connection.cursor() as cursor:
        sql = f'''
        select id,
               concepts
          from (
            select id,
                   concepts
              from public.clinicalcode_historicalgenericentity as entity,
                   json_array_elements(entity.template_data::json->'concept_information') as concepts
             where entity.publish_status = {APPROVAL_STATUS.APPROVED.value}
          ) results
         where cast(concepts->>'concept_id' as integer) = %(concept_id)s and cast(concepts->>'concept_version_id' as integer) = %(version_id)s;
        '''
        cursor.execute(sql, params={
            'concept_id': concept_id,
            'version_id': version_id,
        })

        row = cursor.fetchone()
        if row is not None:
            return True
    
    return False

def was_concept_ever_published(concept_id, version_id=None):
    """
    Checks whether a Concept has ever been published

    Will return true if:
        1. The Concept was published directly via a legacy system
        2. The Concept is currently owned by a Published Phenotype
        3. The Concept was ever included in historic Published Phenotype

    Args:
        concept_id (int): the Concept's id
        version_id (int|null): the Concept's history_id

    Returns:
        bool: Reflects all-time published status

    """
    concept_id = gen_utils.parse_int(concept_id, None)
    if concept_id is None:
        return False

    concept = Concept.objects.filter(id=concept_id)
    if not concept.exists():
        return False

    directly_published = PublishedConcept.objects.filter(concept_id=concept_id)
    if version_id is not None:
        directly_published = directly_published.filter(concept_history_id=version_id)

    if directly_published.exists():
        return True
    
    concept = concept.first()
    phenotype = concept.phenotype_owner
    if phenotype is not None and phenotype.publish_status == APPROVAL_STATUS.APPROVED:
        return True

    with connection.cursor() as cursor:
        sql = f'''
        select id,
               concepts
          from (
            select id,
                   concepts
              from public.clinicalcode_historicalgenericentity as entity,
                   json_array_elements(entity.template_data::json->'concept_information') as concepts
             where entity.publish_status = {APPROVAL_STATUS.APPROVED.value}
          ) results
         where cast(concepts->>'concept_id' as integer) = %(concept_id)s;
        '''
        cursor.execute(sql, params={
            'concept_id': concept_id,
        })

        row = cursor.fetchone()
        if row is not None:
            return True
    
    return False

def get_latest_published_concept(concept_id, default=None):
    """
    Gets the latest published concept given a concept id

    Will return true if:
        1. The Concept was published directly via a legacy system
        2. The Concept is currently owned by a Published Phenotype
        3. The Concept was ever included in historic Published Phenotype

    Args:
        concept_id (int): the Concept's id
        default (any, optional): the default return value if this method fails

    Returns:
        object|null: The latest, published (concept) for that user and the concept id,
            otherwise returns (None)

    """
    concepts = Concept.history.none()
    with connection.cursor() as cursor:
        sql = '''
        select *
         from (
           select distinct on (id)
                  cast(concepts->>'concept_id' as integer) as concept_id,
                  cast(concepts->>'concept_version_id' as integer) as concept_version_id
             from public.clinicalcode_historicalgenericentity as entity,
                  json_array_elements(entity.template_data::json->'concept_information') as concepts
            where 
              (
                cast(concepts->>'concept_id' as integer) = %s
              )
              and not exists (
                select *
                  from public.clinicalcode_genericentity as ge
                 where ge.is_deleted = true and ge.id = entity.id
              )
              and entity.publish_status = %s
          ) results
         order by concept_version_id desc
         limit 1;
        '''
        cursor.execute(
            sql,
            params=[concept_id, APPROVAL_STATUS.APPROVED.value]
        )

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        concepts = Concept.history.filter(
            id__in=[x.get('concept_id') for x in results],
            history_id__in=[x.get('concept_version_id') for x in results],
        )
    
    if concepts.exists():
        return concepts.first()
    return default

def get_latest_accessible_concept(request, concept_id, default=None):
    """
    Gets the latest accessible concept, as described by the user's
        permissions and the given concept id

    Will return true if:
        1. The Concept was published directly via a legacy system
        2. The Concept is currently owned by a Published Phenotype
        3. The Concept was ever included in historic Published Phenotype

    Args:
        concept_id (RequestContext): the HTTPRequest
        concept_id (int): the concept's ID
        default (any, optional): the default return value if this method fails

    Returns:
        object|null: The latest, accessible (concept) for that user and the concept id,
            otherwise returns (None)

    """
    historical_versions = Concept.history.filter(id=concept_id).all().order_by('-history_id')
    if not historical_versions.exists():
        return default
    
    for version in historical_versions:
        if permission_utils.can_user_view_concept(request, version):
            return version
    
    return default

def get_concept_headers(concept_information, default=None):
    """
    Attempts to compute a JSON struct detailing the minimum amount of data
    required to describe a Phenotype's child concepts defined by its
    `concept_information` field

    [!] Note: This method ignores permissions - it should only be called from a
    a method that has previously considered accessibility

    Args:
        concept_information (list[object]): 

    Returns:
        list[object] detailing the header for each child

    """
    if not isinstance(concept_information, list):
        return default

    results = []
    with connection.cursor() as cursor:
        sql = '''
        with
            concept_information (doc) as (
                values 
                (%(concept_information)s::json)
            )
        select
            concept.name,
            cast(obj->>'concept_id' as integer) as concept_id,
            cast(obj->>'concept_version_id' as integer) as concept_version_id,
            case
                when exists(
                    select 1
                      from (
                        select
                              id,
                              cdata
                          from public.clinicalcode_historicalgenericentity as entity,
                             json_array_elements(entity.template_data::json->'concept_information') as cdata
                         where entity.publish_status = 2
                      ) results
                     where cast(cdata->>'concept_id' as integer) = cast(obj->>'concept_id' as integer) and cast(cdata->>'concept_version_id' as integer) = cast(obj->>'concept_version_id' as integer)
                     limit 1
                ) then true
                else false
            end as is_published,
            concept.phenotype_owner_id,
            codingsystem.id as coding_system_id,
            codingsystem.name as coding_system_name
        from concept_information as info,
             json_array_elements(info.doc) as obj
        join public.clinicalcode_concept as concept
          on cast(obj->>'concept_id' as integer) = concept.id
        join public.clinicalcode_codingsystem as codingsystem
          on concept.coding_system_id = codingsystem.id;
        '''

        cursor.execute(
            sql,
            params={
                'concept_information': json.dumps(concept_information)
            }
        )

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if len(results) < 0:
        return default

    return results

def get_concept_dataset(packet, field_name='concept_information', default=None):
    """
    Attempts to collate a packet that contains data relating to the concepts
    defined in the list

    [!] Note: This method ignores permissions - it should only be called from a
    a method that has previously considered accessibility

    Will return true if:
        1. The Concept was published directly via a legacy system
        2. The Concept is currently owned by a Published Phenotype
        3. The Concept was ever included in historic Published Phenotype

    Args:
        packet (list[object]): A list of objects that contain a {concept_id: [int], concept_version_id: [int]}
        field_name (string): The name of the template field from which this packet was derived
        default (any, optional): the default return value if this method fails

    Returns:
        list[object]|null: An (array[object]) that contains information relating to the concept: Name & ID + Version ID; or (default|None) if the children have no child codes

    """
    if not isinstance(packet, list):
        return default

    concept_ids = [x.get('concept_id') for x in packet if x.get('concept_id') is not None and x.get('concept_version_id') is not None]
    concept_versions = [x.get('concept_version_id') for x in packet if x.get('concept_id') is not None and x.get('concept_version_id') is not None]

    if min(len(concept_ids), len(concept_versions)) < 1:
        return default

    results = []
    with connection.cursor() as cursor:
        sql = '''
        select concept.id as id,
               concept.history_id as history_id,
               concept.name as name,
               codingsystem.id as coding_system,
               codingsystem.name as coding_system_name,
               'C' as prefix,
               'concept' as type,
               'concept_information' as field
          from public.clinicalcode_historicalconcept as concept
          join public.clinicalcode_codingsystem as codingsystem
            on codingsystem.id = concept.coding_system_id
          join public.clinicalcode_historicalcomponent as component
            on component.concept_id = concept.id
           and component.history_date <= concept.history_date
           and component.logical_type = %s
           and component.history_type != '-'
          join public.clinicalcode_historicalcodelist as codelist
            on codelist.component_id = component.id
           and codelist.history_date <= concept.history_date
           and codelist.history_type != '-'
          join public.clinicalcode_historicalcode as code
            on code.code_list_id = codelist.id
           and code.history_date <= concept.history_date
           and code.history_type != '-'
         where concept.id in %s and concept.history_id in %s
         group by concept.id, concept.history_id, concept.name, codingsystem.id, codingsystem.name
         order by concept.id asc, concept.history_id desc
        '''
        cursor.execute(
            sql,
            params=[
                CLINICAL_RULE_TYPE.INCLUDE.value,
                tuple(concept_ids),
                tuple(concept_versions),
            ]
        )

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if len(results) < 0:
        return default

    return results

def get_concept_component_details(concept_id, concept_history_id, aggregate_codes=False,
                                  include_codes=True, attribute_headers=None,
                                  include_source_data=False, format_for_api=False):
    """
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Attempts to get all component, codelist and code data assoc.
      with a historical concept

      Args:
        concept_id (number): The concept ID of interest
        concept_history_id (number): The concept's historical id of interest
        aggregate_codes (boolean): If true, will return a 'codelist' key-value pair in the result dict that
                                    describes the distinct, aggregated codes across all components
        include_codes (boolean): If true, will return a 'codes' key-value pair within each component
                                  that describes each code included in a component
        attribute_headers (list): If a non-null list is passed, the method will attempt to find the attributes
                                  associated with each code within every component (and codelist)
        include_source_data (boolean): Flag to det. whether we should incl. source data e.g. wildcard, desc search etc
        format_for_api (boolean): Flag to format against legacy API
        
      Returns:
        dict: A dict that describes the components and their details associated with this historical concept,
        and if aggregate_codes was passed, will return the distinct codelist across components
    """

    # Try to get the Concept and its historical counterpart
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )
    if not concept:
        return None

    historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
    if not historical_concept:
        return None

    seen_codes = set([])
    components_data = []
    with connection.cursor() as cursor:
        sql = '''
            with components as (
                select c0.id,
                       max(c0.history_id) as history_id
                  from public.clinicalcode_historicalcomponent as c0
                  left join public.clinicalcode_historicalcomponent as c1
                    on c1.id = c0.id
                   and c1.concept_id = %(hc_id)s
                   and c1.history_date <= %(hc_date)s::timestamptz
                   and c1.history_type = '-'
                 where c0.concept_id = %(hc_id)s
                   and c0.history_date <= %(hc_date)s::timestamptz
                   and c0.history_type <> '-'
                   and c1.id is null
                 group by c0.id
                 order by c0.id asc
            )

            select c1.*
              from components as c0
              left join public.clinicalcode_historicalcomponent as c1
                on c0.id = c1.id
               and c0.history_id = c1.history_id
        '''

        cursor.execute(
            sql,
            params={ 'hc_id': historical_concept.id, 'hc_date': historical_concept.history_date }
        )

        columns = [col[0] for col in cursor.description]
        components = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for component in components:
            component_data = {
                'id': component.get('id'),
                'name': component.get('name'),
                'logical_type': CLINICAL_RULE_TYPE(component.get('logical_type')).name,
                'source_type': CLINICAL_CODE_SOURCE(component.get('component_type')).name,
                'source': component.get('source'),
            }

            if include_source_data:
                component_data |= {
                    'used_description': component.get('used_description'),
                    'used_wildcard': component.get('used_wildcard'),
                    'was_wildcard_sensitive': component.get('was_wildcard_sensitive'),
                }

            if not include_codes and not aggregate_codes:
                components_data.append(component_data)
                continue

            codes = []
            if attribute_headers is None:
                sql = '''
                    select code.id,
                           code.code,
                           code.description
                      from public.clinicalcode_historicalcodelist as codelist
                      join public.clinicalcode_historicalcode as code
                        on code.code_list_id = codelist.id
                       and code.history_date <= %(hc_date)s::timestamptz
                      left join public.clinicalcode_historicalcode as deletedcode
                        on deletedcode.id = code.id
                       and deletedcode.code_list_id = codelist.id
                       and deletedcode.history_date <= %(hc_date)s::timestamptz
                       and deletedcode.history_type = '-'
                     where codelist.component_id = %(hc_c_id)s
                       and codelist.history_date <= %(hc_date)s::timestamptz
                       and codelist.history_type <> '-'
                       and code.history_type <> '-'
                       and deletedcode.id is null
                '''

                cursor.execute(
                    sql,
                    params={ 'hc_c_id': component.get('id'), 'hc_date': historical_concept.history_date }
                )

                columns = [col[0] for col in cursor.description]
                codes = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                sql = '''
                    select code.id,
                           code.code,
                           code.description,
                           attributes.attributes
                      from public.clinicalcode_historicalcodelist as codelist
                      join public.clinicalcode_historicalcode as code
                        on code.code_list_id = codelist.id
                       and code.history_date <= %(hc_date)s::timestamptz
                      left join public.clinicalcode_historicalcode as deleted_code
                        on deleted_code.id = code.id
                       and deleted_code.code_list_id = codelist.id
                       and deleted_code.history_date <= %(hc_date)s::timestamptz
                       and deleted_code.history_type = '-'
                      left join (
                        select attr.*
                          from public.clinicalcode_historicalconceptcodeattribute as attr
                          left join public.clinicalcode_historicalconceptcodeattribute as deleted_attr
                            on deleted_attr.id = attr.id
                           and deleted_attr.history_type = '-'
                           and deleted_attr.history_date <= %(hc_date)s::timestamptz
                         where attr.concept_id = %(hc_id)s
                           and attr.history_date <= %(hc_date)s::timestamptz
                           and attr.history_type <> '-'
                           and deleted_attr.id is null
                      ) as attributes
                        on attributes.concept_id = %(hc_id)s
                       and attributes.history_date <= %(hc_date)s::timestamptz
                       and attributes.code = code.code
                     where codelist.component_id = %(hc_c_id)s
                       and codelist.history_date <= %(hc_date)s::timestamptz
                       and codelist.history_type <> '-'
                       and code.history_type <> '-'
                       and deleted_code.id is null
                '''

                cursor.execute(
                    sql,
                    params={ 'hc_c_id': component.get('id'), 'hc_id': historical_concept.id, 'hc_date': historical_concept.history_date }
                )

                columns = [col[0] for col in cursor.description]
                codes = [dict(zip(columns, row)) for row in cursor.fetchall()]

                if format_for_api:
                    for code in codes:
                        attributes = code.get('attributes')
                        headers = historical_concept.code_attribute_header
                        if attributes is not None and headers is not None:
                            code['attributes'] = dict(zip(
                                headers, attributes
                            ))

            if include_codes:
                component_data['codes'] = codes

            if aggregate_codes:
                map(lambda obj: seen_codes.add(obj.get('code')) if obj.get('code') else None, codes)

            components_data.append(component_data)

    result = { 'components': components_data }

    if aggregate_codes:
        result.update({ 'codelist': list(seen_codes) })

    return result

def get_concept_codelist(concept_id, concept_history_id, incl_attributes=False):
    """
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Builds the distinct, aggregated codelist from every component associated
      with a concept, given its ID and historical id

      Args:
        concept_id (number): The concept ID of interest

        concept_history_id (number): The concept's historical id of interest

        incl_attributes (bool): Whether to include code attributes

      Returns:
        A list of distinct codes associated with a concept across each of its components

    """

    output = []
    with connection.cursor() as cursor:
        sql = '''
        with 
        concept as (
            select id,
                   history_id,
                   history_date
              from public.clinicalcode_historicalconcept
             where id = %(concept_id)s
               and history_id = %(concept_history_id)s
             group by id, history_id, history_date
             order by history_id desc
             limit 1
        ),
        component as (
        	select concept.id as concept_id,
                   concept.history_id as concept_history_id,
		           concept.history_date as concept_history_date,
		           component.id as component_id,
		           max(component.history_id) as component_history_id,
	               component.logical_type as logical_type,
	               codelist.id as codelist_id,
	               max(codelist.history_id) as codelist_history_id,
                   codes.id as id,
	               codes.code,
		           codes.description
              from concept as concept
              join public.clinicalcode_historicalcomponent as component
                on component.concept_id = concept.id
               and component.history_date <= concept.history_date
               and component.history_type <> '-'
              left join public.clinicalcode_historicalcomponent as deletedcomponent
                on deletedcomponent.concept_id = concept.id
               and deletedcomponent.id = component.id
               and deletedcomponent.history_date <= concept.history_date
               and deletedcomponent.history_type = '-'
              join public.clinicalcode_historicalcodelist as codelist
                on codelist.component_id = component.id
               and codelist.history_date <= concept.history_date
               and codelist.history_type <> '-'
              join public.clinicalcode_historicalcode as codes
                on codes.code_list_id = codelist.id
               and codes.history_date <= concept.history_date
               and codes.history_type <> '-'
             where deletedcomponent.id is null
             group by concept.id,
                      concept.history_id,
                      concept.history_date, 
                      component.id, 
                      component.logical_type, 
                      codelist.id,
                      codes.id,
                      codes.code,
                      codes.description
        )
        '''

        if incl_attributes:
            sql += '''
            select included_codes.*,
                   attributes.attributes
              from component as included_codes
              left join component as excluded_codes
                on excluded_codes.code = included_codes.code
               and excluded_codes.logical_type = 2
              left join (
                  select attr.*
                    from concept as concept
                    join public.clinicalcode_historicalconceptcodeattribute as attr
                      on attr.concept_id = concept.id
                     and attr.history_date <= concept.history_date
                    left join public.clinicalcode_historicalconceptcodeattribute as deleted_attr
                      on deleted_attr.id = attr.id
                     and deleted_attr.history_type = '-'
                     and deleted_attr.history_date <= concept.history_date
                   where attr.history_type <> '-'
                     and deleted_attr.id is null
              ) as attributes
                on attributes.concept_id = included_codes.concept_id
               and attributes.history_date <= included_codes.concept_history_date
               and attributes.code = included_codes.code
             where included_codes.logical_type = 1
               and excluded_codes.code is null;
            '''
        else:
            sql += '''
            select included_codes.id,
                   included_codes.code,
                   included_codes.description
              from component as included_codes
              left join component as excluded_codes
                on excluded_codes.code = included_codes.code
               and excluded_codes.logical_type = 2
             where included_codes.logical_type = 1
               and excluded_codes.code is null;
            '''

        cursor.execute(
            sql,
            {
                'concept_id': concept_id,
                'concept_history_id': concept_history_id
            }
        )

        columns = [col[0] for col in cursor.description]
        output = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return output

def get_associated_concept_codes(concept_id, concept_history_id, code_ids, incl_attributes=False):
    """
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Retrieves the concept codes associated with the code_ids list

      Args:
        concept_id (number): The concept ID of interest
        concept_history_id (number): The concept's historical id of interest
        code_ids (list): The code ids filter
        incl_attributes (bool): Whether to include code attributes

      Returns:
        The codes that are present in the code ids list

    """
    codelist = get_concept_codelist(concept_id, concept_history_id, incl_attributes=incl_attributes)
    codelist = [code for code in codelist if code.get('id', -1) in code_ids]
    return codelist

def get_reviewable_concept(concept_id, concept_history_id, hide_user_details=False, incl_attributes=False):
    '''
      Intended to get the reviewed / reviewable codes for a Concept
    '''
    return

def get_review_concept(concept_id, concept_history_id):
    """
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Retrieves the ConceptReviewStatus instance assoc. with a Concept
      given its id and historical id

      Args:
        concept_id (number): The concept ID of interest
        concept_history_id (number): The concept's historical id of interest

      Returns:
        The associated ConceptReviewStatus instance

    """
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )
    if not concept:
        return None

    historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
    if not historical_concept:
        return None

    return model_utils.try_get_instance(
        ConceptReviewStatus,
        concept_id=historical_concept.id,
        history_id=historical_concept.history_id
    )

def get_minimal_concept_data(concept):
    """
        Gets the minimum concept related details
        required for the API view to support legacy
        requests & formatting
    
        Args:
            concept (Concept()) - the Concept model instance

        Returns:
            An (object) containing the associated data
    """
    # Dictify our concept
    concept_data = model_utils.jsonify_object(
        concept,
        remove_userdata=False,
        strippable_fields=None,
        dump=False
    )

    # Retrieve human readable data for our tags, collections & coding systems
    if concept_data.get('tags'):
        concept_data['tags'] = [
            model_utils.get_tag_attribute(tag, tag_type=TAG_TYPE.TAG)
            for tag in concept_data['tags']
        ]

    if concept_data.get('collections'):
        concept_data['collections'] = [
            model_utils.get_tag_attribute(collection, tag_type=TAG_TYPE.COLLECTION)
            for collection in concept_data['collections']
        ]

    # Clean coding system for top level field use
    concept_data.pop('coding_system', None)

    # If userdata is requested, try to grab all related
    for field in concept._meta.fields:
        if field.name not in concept_data:
            continue

        if not isinstance(field, ForeignKey):
            continue

        model = field.target_field.model
        if str(model) not in USERDATA_MODELS:
            continue

        concept_data[field.name] = model_utils.get_userdata_details(
            model,
            pk=concept_data[field.name],
            hide_user_details=False
        )

    # Clean data if required
    if not concept_data.get('is_deleted'):
        concept_data.pop('is_deleted', None)
        concept_data.pop('deleted_by', None)
        concept_data.pop('deleted', None)

    return {
        'concept_id': concept.id,
        'concept_version_id': concept.history_id,
        'coding_system': model_utils.get_coding_system_details(concept.coding_system)
    } | concept_data

def get_clinical_concept_data(concept_id, concept_history_id, include_reviewed_codes=False,
                              aggregate_component_codes=False, include_component_codes=True,
                              include_attributes=False, strippable_fields=None,
                              remove_userdata=False, hide_user_details=False,
                              derive_access_from=None, requested_entity_id=None,
                              format_for_api=False, include_source_data=False):
    """
      [!] Note: This method ignores permissions to derive data - it should only be called from a
                a method that has previously considered accessibility

      Retrieves all data associated with a HistoricConcept,
      incl. a list of codes assoc. with each component, or the
      final codelist, if requested

      Args:
        concept_id (number): The concept ID of interest
        concept_history_id (number): The concept's historical id of interest
        include_reviewed_codes (boolean): When building the data, should we pull the finalised reviewed codes?
        aggregate_component_codes (boolean): When building the codelist, should we aggregate across components?
        include_component_codes (boolean): When building the components, should we incl. a codelist for each component?
        include_attributes (boolean): Should we include attributes?
        strippable_fields (list): Whether to strip any fields from the Concept model when
                                  building the concept's data result
        remove_userdata (boolean): Whether to remove userdata related fields from the result (assoc. with each Concept)
        derive_access_from (RequestContext): Using the RequestContext, determine whether a user can edit a Concept
        format_for_api (boolean): Flag to format against legacy API
        include_source_data (boolean): Flag to det. whether we should incl. source data e.g. wildcard, desc search etc

      Returns:
        A dictionary that describes the concept, its components, and associated codes; constrained
        by the method parameters

        If a RequestContext was provided, per the derive_access_from param, it will return a permission context
    """

    # Try to find the associated concept and its historical counterpart
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )
    if not concept:
        return None

    historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
    if not historical_concept:
        return None

    # Dictify our concept
    if not strippable_fields:
        strippable_fields = []
    strippable_fields += HISTORICAL_HIDDEN_FIELDS

    concept_data = model_utils.jsonify_object(
        historical_concept,
        remove_userdata=remove_userdata,
        strippable_fields=strippable_fields,
        dump=False
    )

    # Determine whether the concept is OOD
    if isinstance(derive_access_from, HttpRequest) or isinstance(derive_access_from, RESTRequest):
        latest_version = get_latest_accessible_concept(derive_access_from, concept_id)
        
        if not latest_version:
            latest_version = historical_concept

        concept_data['latest_version'] = {
            'id': latest_version.id,
            'history_id': latest_version.history_id,
            'is_out_of_date': historical_concept.history_id < latest_version.history_id,
        }

        concept_data['is_published'] = is_concept_published(concept_id, concept_history_id)

    # Retrieve human readable data for our tags, collections & coding systems
    if concept_data.get('tags'):
        concept_data['tags'] = [
            model_utils.get_tag_attribute(tag, tag_type=TAG_TYPE.TAG)
            for tag in concept_data['tags']
        ]

    if concept_data.get('collections'):
        concept_data['collections'] = [
            model_utils.get_tag_attribute(collection, tag_type=TAG_TYPE.COLLECTION)
            for collection in concept_data['collections']
        ]

    # Clean coding system for top level field use
    concept_data.pop('coding_system', None)

    # If userdata is requested, try to grab all related
    if not remove_userdata:
        for field in historical_concept._meta.fields:
            if field.name not in concept_data:
                continue

            if not isinstance(field, ForeignKey):
                continue

            model = field.target_field.model
            if str(model) not in USERDATA_MODELS:
                continue

            concept_data[field.name] = model_utils.get_userdata_details(
                model,
                pk=concept_data[field.name],
                hide_user_details=hide_user_details
            )

    # Derive access permissions if RequestContext provided
    if isinstance(derive_access_from, HttpRequest):
        concept_data['has_edit_access'] = permission_utils.user_can_edit_via_entity(derive_access_from, concept) \
                                        or permission_utils.user_has_concept_ownership(derive_access_from.user, concept)

    # Clean data if required
    if not concept_data.get('is_deleted'):
        concept_data.pop('is_deleted', None)
        concept_data.pop('deleted_by', None)
        concept_data.pop('deleted', None)

    # Build codelist and components from concept (modified by params)
    attribute_headers = concept_data.pop('code_attribute_header', None) if include_attributes else None
    attribute_headers = attribute_headers if isinstance(attribute_headers, list) and len(attribute_headers) > 0 else None
    components_data = get_concept_component_details(
        concept_id,
        concept_history_id,
        aggregate_codes=aggregate_component_codes,
        include_codes=include_component_codes,
        attribute_headers=attribute_headers,
        include_source_data=include_source_data,
        format_for_api=format_for_api
    )

    # Only append header attribute if not null
    if attribute_headers is not None:
        concept_data['code_attribute_header'] = attribute_headers
    
    # Set phenotype owner
    phenotype_owner = concept.phenotype_owner   
    if phenotype_owner:
        concept_data['phenotype_owner'] = phenotype_owner.id

        latest_version_id = permission_utils.get_latest_owner_version_from_concept(
            phenotype_id=phenotype_owner.id,
            concept_id=historical_concept.id,
            concept_version_id=historical_concept.history_id
        )

        if latest_version_id is not None:
            concept_data['phenotype_owner_history_id'] = latest_version_id
    
    # Set the requested entity id
    concept_data['requested_entity_id'] = requested_entity_id

    # Set base
    if not format_for_api:
        result = {
            'concept_id': concept_id,
            'concept_version_id': concept_history_id,
            'coding_system': model_utils.get_coding_system_details(historical_concept.coding_system),
            'details': concept_data,
            'components': components_data.get('components') if components_data is not None else [],
        }
    else:
        result = {
            'concept_id': concept_id,
            'concept_version_id': concept_history_id,
            'coding_system': model_utils.get_coding_system_details(historical_concept.coding_system)
        }
        result |= concept_data
        result['components'] = components_data.get('components') if components_data is not None else []

    # Apply aggregated codes if required
    if aggregate_component_codes:
        result['aggregated_component_codes'] = components_data.get('codelist') if components_data is not None else []

    # Build the final, reviewed codelist if required
    if include_reviewed_codes:
        result['codelist'] = get_concept_codelist(
            concept_id, concept_history_id,
            incl_attributes=include_attributes
        )

    return result
