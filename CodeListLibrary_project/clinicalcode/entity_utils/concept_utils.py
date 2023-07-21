from django.db.models import ForeignKey, Subquery, OuterRef
from django.http.request import HttpRequest

from ..models.Concept import Concept
from ..models.ConceptReviewStatus import ConceptReviewStatus
from ..models.Component import Component
from ..models.CodeList import CodeList
from ..models.ConceptCodeAttribute import ConceptCodeAttribute
from ..models.Code import Code

from . import model_utils, permission_utils
from .constants import (
    USERDATA_MODELS, TAG_TYPE, HISTORICAL_HIDDEN_FIELDS,
    CLINICAL_RULE_TYPE, CLINICAL_CODE_SOURCE,
)

def get_concept_dataset(packet, field_name='concept_information', default=None):
    '''
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      @desc Attempts to collate a packet that contains data relating to the concepts
            defined in the list

      Args:
        packet {array[object]}: A list of objects that contain a {concept_id: [int], concept_version_id: [int]}
        field_name {string}: The name of the template field from which this packet was derived
        default {any}: A default param to return if we are unable to perform the task

      Returns:
        An {array[object]} that contains information relating to the concept:
          - Name
          - ID + Version ID
    '''
    if not isinstance(packet, list):
        return default

    concept_ids = [x.get('concept_id') for x in packet if x.get('concept_id') is not None]
    concept_version_ids = [
        x.get('concept_version_id') for x in packet
        if x.get('concept_version_id') is not None
    ]

    concepts = Concept.history.filter(
        id__in=concept_ids,
        history_id__in=concept_version_ids,
    )

    concept_data = concepts.values('name', 'id', 'history_id')
    coding_systems = concepts.values('coding_system__id')

    concept_data = list(concept_data)
    concept_data = [
        {
            'prefix': 'C',
            'type': 'Concept',
            'field': field_name,
            'coding_system': coding_systems[i].get('coding_system__id') if coding_systems[i] else -1
        } | concept
        for i, concept in enumerate(concept_data)
    ]

    return concept_data

def get_concept_component_details(concept_id, concept_history_id, aggregate_codes=False,
                                  include_codes=True, attribute_headers=None,
                                  include_source_data=False):
    '''
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Attempts to get all component, codelist and code data assoc.
      with a historical concept

      Args:
        concept_id {number}: The concept ID of interest
        concept_history_id {number}: The concept's historical id of interest

        aggregate_codes {boolean}: If true, will return a 'codelist' key-value pair in the result dict that
                                    describes the distinct, aggregated codes across all components

        include_codes {boolean}: If true, will return a 'codes' key-value pair within each component
                                  that describes each code included in a component

        attribute_headers {list}: If a non-null list is passed, the method will attempt to find the attributes
                                  associated with each code within every component (and codelist)
        
        include_source_data {boolean}: Flag to det. whether we should incl. source data e.g. wildcard, desc search etc

      Returns:
        A dict that describes the components and their details associated with this historical concept,
        and if aggregate_codes was passed, will return the distinct codelist across components
    '''

    # Try to get the Concept and its historical counterpart
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )
    if not concept:
        return None

    historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
    if not historical_concept:
        return None

    # Find the associated components (or now, rulesets) given the concept and its historical date
    components = Component.history.filter(
        concept__id=historical_concept.id,
        history_date__lte=historical_concept.history_date
    ) \
    .annotate(
        was_deleted=Subquery(
            Component.history.filter(
                id=OuterRef('id'),
                concept__id=historical_concept.id,
                history_date__lte=historical_concept.history_date,
                history_type='-'
            )
            .order_by('id', '-history_id')
            .distinct('id')
            .values('id')
        )
    ) \
    .exclude(was_deleted__isnull=False) \
    .order_by('id', '-history_id') \
    .distinct('id')

    if not components.exists():
        return None

    components_data = []
    codelist_data = []
    seen_codes = set()
    for component in components:
        component_data = {
            'id': component.id,
            'name': component.name,
            'logical_type': CLINICAL_RULE_TYPE(component.logical_type).name,
            'source_type': CLINICAL_CODE_SOURCE(component.component_type).name,
            'source': component.source,
        }

        if include_source_data:
            component_data |= {
                'used_description': component.used_description,
                'used_wildcard': component.used_wildcard,
                'was_wildcard_sensitive': component.was_wildcard_sensitive,
            }

        # Find the codelist associated with this component
        codelist = CodeList.history.exclude(history_type='-') \
        .filter(
            component__id=component.id,
            history_date__lte=historical_concept.history_date
        ) \
        .order_by('-history_date', '-history_id')

        if not codelist.exists():
            continue
        codelist = codelist.first()

        # Find the codes associated with this codelist
        codes = Code.history.filter(
            code_list__id=codelist.id,
            history_date__lte=historical_concept.history_date
        ) \
        .annotate(
            was_deleted=Subquery(
                Code.history.filter(
                    id=OuterRef('id'),
                    code_list__id=codelist.id,
                    history_date__lte=historical_concept.history_date,
                    history_type='-'
                )
                .order_by('code', '-history_id')
                .distinct('code')
                .values('id')
            )
        ) \
        .exclude(was_deleted__isnull=False) \
        .order_by('id', '-history_id') \
        .distinct('id')

        component_data['code_count'] = codes.count()

        if attribute_headers is None:
            # Add each code
            codes = codes.values('id', 'code', 'description')
        else:
            # Annotate each code with its list of attribute values based on the code_attribute_headers
            codes = codes.annotate(
                attributes=Subquery(
                    ConceptCodeAttribute.history.filter(
                        concept__id=historical_concept.id,
                        history_date__lte=historical_concept.history_date,
                        code=OuterRef('code')
                    )
                    .annotate(
                        was_deleted=Subquery(
                            ConceptCodeAttribute.history.filter(
                                concept__id=historical_concept.id,
                                history_date__lte=historical_concept.history_date,
                                code=OuterRef('code'),
                                history_type='-'
                            )
                            .order_by('code', '-history_id')
                            .distinct('code')
                            .values('id')
                        )
                    )
                    .exclude(was_deleted__isnull=False)
                    .order_by('id', '-history_id')
                    .distinct('id')
                    .values('attributes')
                )
            ) \
            .values('id', 'code', 'description', 'attributes')

        codes = list(codes)

        # Append codes to component if required
        if include_codes:
            component_data['codes'] = codes

        # Append aggregated codes if required
        if aggregate_codes:
            codes = [
                seen_codes.add(obj.get('code')) or obj
                for obj in codes
                if obj.get('code') not in seen_codes
            ]
            codelist_data += codes

        components_data.append(component_data)

    if aggregate_codes:
        return {
            'codelist': codelist_data,
            'components': components_data,
        }

    return {
        'components': components_data
    }

def get_concept_codelist(concept_id, concept_history_id, incl_logical_types=None, incl_attributes=False):
    '''
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Builds the distinct, aggregated codelist from every component associated
      with a concept, given its ID and historical id

      Args:
        concept_id {number}: The concept ID of interest
        concept_history_id {number}: The concept's historical id of interest

        incl_logical_types {int[]}: Whether to include only codes that stem from Components
                                    with that logical type

        incl_attributes {bool}: Whether to include code attributes

      Returns:
        A list of distinct codes associated with a concept across each of its components

    '''

    # Try to find the associated concept and its historical counterpart
    concept = model_utils.try_get_instance(
        Concept, pk=concept_id
    )
    if not concept:
        return None

    historical_concept = model_utils.try_get_entity_history(concept, concept_history_id)
    if not historical_concept:
        return None

    attribute_header = historical_concept.code_attribute_header
    if not incl_attributes or not isinstance(attribute_header, list) or len(attribute_header) < 1:
        attribute_header = None

    # Find the components associated with this concept
    components = Component.history.exclude(history_type='-') \
    .filter(
        concept__id=historical_concept.id,
        history_date__lte=historical_concept.history_date
    ) \
    .annotate(
        was_deleted=Subquery(
            Component.history.filter(
                id=OuterRef('id'),
                concept__id=historical_concept.id,
                history_date__lte=historical_concept.history_date,
                history_type='-'
            )
            .order_by('id', '-history_id')
            .distinct('id')
            .values('id')
        )
    ) \
    .exclude(was_deleted__isnull=False) \
    .order_by('id', '-history_id') \
    .distinct('id')

    if not components.exists():
        return []

    # This needs changing in future, it's a naive implementation for a hotfix
    result_set = []
    final_codelist = set([])
    excluded_codes = set([])
    for component in components:
        # Find the codelist associated with this component
        codelist = CodeList.history.exclude(history_type='-') \
        .filter(
            component__id=component.id,
            history_date__lte=historical_concept.history_date
        ) \
        .order_by('-history_date', '-history_id')

        if not codelist.exists():
            continue
        codelist = codelist.first()

        # Find the codes associated with this codelist
        codes = Code.history.filter(
            code_list__id=codelist.id,
            history_date__lte=historical_concept.history_date
        ) \
        .annotate(
            was_deleted=Subquery(
                Code.history.filter(
                    id=OuterRef('id'),
                    code_list__id=codelist.id,
                    history_date__lte=historical_concept.history_date,
                    history_type='-'
                )
                .order_by('code', '-history_id')
                .distinct('code')
                .values('id')
            )
        ) \
        .exclude(was_deleted__isnull=False) \
        .order_by('id', '-history_id') \
        .distinct('id')

        results = None
        if attribute_header:
            codes = codes.annotate(
                attributes=Subquery(
                    ConceptCodeAttribute.history.filter(
                        concept__id=historical_concept.id,
                        history_date__lte=historical_concept.history_date,
                        code=OuterRef('code')
                    )
                    .annotate(
                        was_deleted=Subquery(
                            ConceptCodeAttribute.history.filter(
                                concept__id=historical_concept.id,
                                history_date__lte=historical_concept.history_date,
                                code=OuterRef('code'),
                                history_type='-'
                            )
                            .order_by('code', '-history_id')
                            .distinct('code')
                            .values('id')
                        )
                    )
                    .exclude(was_deleted__isnull=False)
                    .order_by('code', '-history_id')
                    .distinct('code')
                    .values('attributes')
                )
            )

            results = list(codes.values('id', 'code', 'description', 'attributes'))
        else:
            results = list(codes.values('id', 'code', 'description'))

        result_set += results
        if isinstance(incl_logical_types, list) and component.logical_type not in incl_logical_types:
            excluded_codes.update([x.get('code') for x in results])
        else:
            final_codelist.update([x.get('code') for x in results])

    output = list(final_codelist - excluded_codes)
    output = [
        next(obj for obj in result_set if obj.get('code') == x)
        for x in output
    ]

    return output

def get_associated_concept_codes(concept_id, concept_history_id, code_ids, incl_attributes=False):
    '''
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Retrieves the concept codes associated with the code_ids list

      Args:
        concept_id {number}: The concept ID of interest
        concept_history_id {number}: The concept's historical id of interest
        code_ids {list}: The code ids filter
        incl_attributes {bool}: Whether to include code attributes

      Returns:
        The codes that are present in the code ids list

    '''
    codelist = get_concept_codelist(concept_id, concept_history_id, incl_attributes=incl_attributes)
    codelist = [code for code in codelist if code.get('id', -1) in code_ids]
    return codelist

def get_reviewable_concept(concept_id, concept_history_id, hide_user_details=False, incl_attributes=False):
    '''
      Intended to get the reviewed / reviewable codes for a Concept
    '''
    return

def get_review_concept(concept_id, concept_history_id):
    '''
      [!] Note: This method ignores permissions - it should only be called from a
                a method that has previously considered accessibility

      Retrieves the ConceptReviewStatus instance assoc. with a Concept
      given its id and historical id

      Args:
        concept_id {number}: The concept ID of interest
        concept_history_id {number}: The concept's historical id of interest

      Returns:
        The associated ConceptReviewStatus instance

    '''
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
    '''
        Gets the minimum concept related details
        required for the API view to support legacy
        requests & formatting
    
        Args:
            concept {Concept()} - the Concept model instance

        Returns:
            An {object} containing the associated data
    '''
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
    concept_data.pop('coding_system')

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
        concept_data.pop('is_deleted')
        concept_data.pop('deleted_by')
        concept_data.pop('deleted')

    return {
        'concept_id': concept.id,
        'concept_version_id': concept.history_id,
        'coding_system': model_utils.get_coding_system_details(concept.coding_system)
    } | concept_data

def get_clinical_concept_data(concept_id, concept_history_id, include_reviewed_codes=False,
                              aggregate_component_codes=False, include_component_codes=True,
                              include_attributes=False, strippable_fields=None,
                              remove_userdata=False, hide_user_details=False,
                              derive_access_from=None, format_for_api=False,
                              include_source_data=False):
    '''
      [!] Note: This method ignores permissions to derive data - it should only be called from a
                a method that has previously considered accessibility

      Retrieves all data associated with a HistoricConcept,
      incl. a list of codes assoc. with each component, or the
      final codelist, if requested

      Args:
        concept_id {number}: The concept ID of interest

        concept_history_id {number}: The concept's historical id of interest

        include_reviewed_codes {boolean}: When building the data, should we pull the finalised reviewed codes?

        aggregate_component_codes {boolean}: When building the codelist, should we aggregate across components?

        include_component_codes {boolean}: When building the components, should we incl. a codelist for each component?

        include_attributes {boolean}: Should we include attributes?

        strippable_fields {list}: Whether to strip any fields from the Concept model when
                                  building the concept's data result

        remove_userdata {boolean}: Whether to remove userdata related fields from the result (assoc. with each Concept)

        derive_access_from {RequestContext}: Using the RequestContext, determine whether a user can edit a Concept

        format_for_api {boolean}: Flag to format against legacy API

        include_source_data {boolean}: Flag to det. whether we should incl. source data e.g. wildcard, desc search etc

      Returns:
        A dictionary that describes the concept, its components, and associated codes; constrained
        by the method parameters

        If a RequestContext was provided, per the derive_access_from param, it will return a permission context

    '''

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
    concept_data.pop('coding_system')

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
        concept_data.pop('is_deleted')
        concept_data.pop('deleted_by')
        concept_data.pop('deleted')

    # Build codelist and components from concept (modified by params)
    attribute_headers = concept_data.pop('code_attribute_header', None) if include_attributes else None
    attribute_headers = attribute_headers if isinstance(attribute_headers, list) and len(attribute_headers) > 0 else None
    components_data = get_concept_component_details(
        concept_id,
        concept_history_id,
        aggregate_codes=aggregate_component_codes,
        include_codes=include_component_codes,
        attribute_headers=attribute_headers,
        include_source_data=include_source_data
    )

    # Only append header attribute if not null
    if attribute_headers is not None:
        concept_data['code_attribute_headers'] = attribute_headers

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
            incl_logical_types=[CLINICAL_RULE_TYPE.INCLUDE.value],
            incl_attributes=include_attributes
        )

    return result
