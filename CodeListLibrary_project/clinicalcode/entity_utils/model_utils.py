from django.db.models import Q, ForeignKey, Subquery, OuterRef
from django.forms.models import model_to_dict
from django.contrib.auth.models import User, Group

import re
import json

from . import gen_utils
from ..models.GenericEntity import GenericEntity
from ..models.PublishedGenericEntity import PublishedGenericEntity
from ..models.Tag import Tag
from ..models.CodingSystem import CodingSystem
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from ..models.Component import Component
from ..models.CodeList import CodeList
from ..models.ConceptCodeAttribute import ConceptCodeAttribute
from ..models.Code import Code
from .constants import (USERDATA_MODELS, STRIPPED_FIELDS, APPROVAL_STATUS,
                        GROUP_PERMISSIONS, TAG_TYPE, HISTORICAL_CONCEPT_HIDDEN_FIELDS,
                        CLINICAL_RULE_TYPE, CLINICAL_CODE_SOURCE)

def try_get_instance(model, **kwargs):
  '''
    
  '''
  try:
    instance = model.objects.get(**kwargs)
  except:
    return None
  else:
    return instance
  
def try_get_entity_history(entity, history_id):
  '''
    
  '''
  try:
    instance = entity.history.get(history_id=history_id)
  except:
    return None
  else:
    return instance

def get_entity_id(primary_key):
  '''
    
  '''
  entity_id = re.split('(\d.*)', primary_key)
  if len(entity_id) >= 2 and entity_id[0].isalpha() and entity_id[1].isdigit():
    return entity_id[:2]
  else:
    return False

def get_latest_entity_published(entity_id):
  '''
    
  '''
  latest_published_entity = PublishedGenericEntity.objects.filter(
    entity_id=entity_id, approval_status=2
  ).order_by('-entity_history_id')
  
  if latest_published_entity.exists():
    return latest_published_entity.first()

  return None

def get_entity_approval_status(entity_id, historical_id):
  '''
    
  '''
  entity = try_get_instance(
    PublishedGenericEntity,
    entity_id=entity_id, 
    entity_history_id=historical_id
  )

  if entity:
    return entity.approval_status
  
  return None

def get_latest_entity_historical_id(entity_id, user):
  '''

  '''
  entity = try_get_instance(GenericEntity, id=entity_id)
      
  if entity:
    if user.is_superuser:
      return int(entity.history.latest().history_id)
    
    if user:
      history = entity.history.filter(
        Q(owner=user.id) | 
        Q(
          group_id__in=user.groups.all(),
          group_access__in=[GROUP_PERMISSIONS.VIEW, GROUP_PERMISSIONS.EDIT]
        )
      )
      
      if history.exists():
        return history.history_id
  
    published = get_latest_entity_published(entity)
    if published:
      return published.history.latest().history_id

  return None

def get_concept_data(concept_id, concept_history_id):
  '''
  
  '''
  concept = try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return None
  
  concept = try_get_entity_history(concept, concept_history_id)
  if not concept:
    return None
  
  return {
    'concept_id': concept_id,
    'concept_verion_id': concept_history_id,
    'coding_system': concept.coding_system.name,
    'data': {}
  }

def jsonify_object(obj, remove_userdata=True, strip_fields=True, strippable_fields=None, dump=True):
  '''
    JSONifies instance of a model
      - removes userdata related data for safe usage within template
      - removes specific fields that are unrelated to templates e.g. SearchVectorField
  '''
  instance = model_to_dict(obj)
  
  if remove_userdata or strip_fields:
    for field in obj._meta.fields:
      if strip_fields and field.get_internal_type() in STRIPPED_FIELDS:
        instance.pop(field.name, None)
        continue

      if strip_fields and strippable_fields is not None:
        if field.name in strippable_fields:
          instance.pop(field.name, None)
          continue

      if not remove_userdata:
        continue
      
      if not isinstance(field, ForeignKey):
        continue
      
      model = str(field.target_field.model)
      if model not in USERDATA_MODELS:
        continue
      instance.pop(field.name, None)

  if dump:
    return json.dumps(instance, cls=gen_utils.ModelEncoder)
  return instance

def get_tag_attribute(tag_id, tag_type):
  '''
    Returns a dict that describes a tag given its id and type
  '''
  tag = Tag.objects.filter(id=tag_id, tag_type=tag_type)
  if tag.exists():
    tag = tag.first()
    return {
      'name': tag.description,
      'value': tag.id,
      'type': tag.tag_type
    }
  
  return None

def get_coding_system_details(coding_system):
  '''
    Returns a dict that describes a coding system given that
    the coding_system parameter passed is either an obj or an int
    that references a coding_system by its codingsystem_id
  '''
  if isinstance(coding_system, int):
    coding_system = CodingSystem.objects.filter(codingsystem_id=coding_system)
    if not coding_system.exists():
      return None
    coding_system = coding_system.first()
  
  if not isinstance(coding_system, CodingSystem):
    return None
  
  return {
    'id': coding_system.codingsystem_id,
    'name': coding_system.name,
    'description': coding_system.description,
  }

def get_userdata_details(model, **kwargs):
  '''
    Attempts to return a dict that describes a userdata field e.g. a user, or a group
    in a human readable format
  '''
  instance = try_get_instance(model, **kwargs)
  if not instance:
    return None
  
  details = {'id': instance.pk}
  if isinstance(instance, Group):
    return details | {'name': instance.name}
  elif isinstance(instance, User):
    return details | {'username': instance.username}
  
  return details

def get_concept_component_details(concept_id, concept_history_id, include_codes=True, attribute_headers=None):
  '''
    Attempts to get all component, codelist and code data assoc.
    with a historical concept

    [!] Note: This method ignores permissions - it should only be called from a
              a method that has previously considered accessibility
  '''

  # Try to get the Concept and its historical counterpart
  concept = try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return None
  
  historical_concept = try_get_entity_history(concept, concept_history_id)
  if not historical_concept:
    return None
  
  # Find the associated components (or now, rulesets) given the concept and its historical date
  components = Component.history.exclude(history_type='-') \
                                .filter(
                                  concept__id=historical_concept.id,
                                  history_date__lte=historical_concept.history_date
                                )
  
  if not components.exists():
    return None
  
  components_data = [ ]
  for component in components:
    component_data = {
      'name': component.name,
      'logical_type': CLINICAL_RULE_TYPE(component.logical_type).name,
      'source_type': CLINICAL_CODE_SOURCE(component.component_type).name,
      'source': component.source,
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
    codes = Code.history.exclude(history_type='-') \
                        .filter(
                          code_list__id=codelist.id,
                          history_date__lte=historical_concept.history_date
                        )

    component_data['code_count'] = codes.count()

    if include_codes:
      if attribute_headers is None:
        # Add each code
        component_data['codes'] = list(codes.values('code', 'description'))
      else:
        # Annotate each code with its list of attribute values based on the code_attribute_headers
        codes = codes.annotate(
          attributes=Subquery(
            ConceptCodeAttribute.history.exclude(history_type='-') \
                                        .filter(
                                          concept__id=historical_concept.id,
                                          history_date__lte=historical_concept.history_date,
                                          code=OuterRef('code')
                                        )
                                        .values('attributes')
          )
        )
        component_data['codes'] = list(codes.values('code', 'description', 'attributes'))
    
    components_data.append(component_data)
  
  return components_data

def get_final_concept_codelist(concept_id, concept_history_id):
  '''
    Builds the final codelist from every component associated
    with a concept, given its ID and historical id
  '''
  
  # Try to find the associated concept and its historical counterpart
  concept = try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return None
  
  historical_concept = try_get_entity_history(concept, concept_history_id)
  if not historical_concept:
    return None

  attribute_header = historical_concept.code_attribute_header
  if not isinstance(attribute_header, list) or len(attribute_header) < 1:
    attribute_header = None
  
  # Find the components associated with this concept
  components = Component.history.exclude(history_type='-') \
                                .filter(
                                  concept__id=historical_concept.id,
                                  history_date__lte=historical_concept.history_date
                                )
  
  if not components.exists():
    return [ ]
  
  final_codelist = []
  for component in components:
    # Ignore exclusion components
    if component.logical_type != CLINICAL_RULE_TYPE.INCLUDE.value:
      continue

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
    codes = Code.history.exclude(history_type='-') \
                        .filter(
                          code_list__id=codelist.id,
                          history_date__lte=historical_concept.history_date
                        )

    if attribute_header:
      codes = codes.annotate(
        attributes=Subquery(
          ConceptCodeAttribute.history.exclude(history_type='-') \
                                      .filter(
                                        concept__id=historical_concept.id,
                                        history_date__lte=historical_concept.history_date,
                                        code=OuterRef('code')
                                      )
                                      .values('attributes')
        )
      )
    
    final_codelist += list(codes.values('code', 'description', 'attributes'))
  
  seen_codes = set()
  final_codelist = [
    seen_codes.add(obj.get('code')) or obj
    for obj in final_codelist
    if obj.get('code') not in seen_codes
  ]

  return final_codelist

def get_clinical_concept_data(request, concept_id, concept_history_id, include_final_codes=False, include_codes=True, strippable_fields=None, remove_userdata=False):
  '''
    Retrieves all data associated with a HistoricConcept,
    incl. a list of codes assoc. with each component, or the
    final codelist, if requested
  '''

  # Try to find the associated concept and its historical counterpart
  concept = try_get_instance(
    Concept, pk=concept_id
  )
  if not concept:
    return None
  
  historical_concept = try_get_entity_history(concept, concept_history_id)
  if not historical_concept:
    return None
  
  # Dictify our concept
  if not strippable_fields:
    strippable_fields = [ ]
  strippable_fields += HISTORICAL_CONCEPT_HIDDEN_FIELDS

  concept_data = jsonify_object(
    historical_concept,
    remove_userdata=remove_userdata,
    strippable_fields=strippable_fields,
    dump=False
  )
  
  # Retrieve human readable data for our tags, collections & coding systems
  concept_data['tags'] = [
    get_tag_attribute(tag, tag_type=TAG_TYPE.TAG)
    for tag in concept_data['tags']
  ]

  concept_data['collections'] = [
    get_tag_attribute(collection, tag_type=TAG_TYPE.COLLECTION)
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

      concept_data[field.name] = get_userdata_details(model, pk=concept_data[field.name])
  
  # Clean data if required
  if not concept_data.get('is_deleted'):
    concept_data.pop('is_deleted')
    concept_data.pop('deleted_by')
    concept_data.pop('deleted')

  # Build codelist and components from concept  
  attribute_headers = concept_data.pop('code_attribute_header', None)
  attribute_headers = attribute_headers if isinstance(attribute_headers, list) and len(attribute_headers) > 0 else None
  components_data = get_concept_component_details(
    concept_id,
    concept_history_id,
    include_codes=include_codes,
    attribute_headers=attribute_headers
  )

  # Only append header attribute if not null
  if attribute_headers is not None:
    concept_data['code_attribute_headers'] = attribute_headers
  
  result = {
    'concept_id': concept_id,
    'concept_verion_id': concept_history_id,
    'coding_system': get_coding_system_details(historical_concept.coding_system),
    'data': concept_data,
    'components': components_data
  }

  # Only append final codelist if required
  if include_final_codes:
    result['codelist'] = get_final_concept_codelist(concept_id, concept_history_id)
    
  return result
