from django.contrib.auth.models import User
from rest_framework.response import Response
from django.db.models import ForeignKey
from rest_framework import status
from copy import deepcopy

from ..models.GenericEntity import GenericEntity
from ..models.Template import Template
from ..models.Concept import Concept
from . import model_utils
from . import template_utils
from . import permission_utils
from . import search_utils
from . import create_utils
from . import gen_utils
from . import constants

''' Parameter validation '''

def is_malformed_entity_id(primary_key):
  '''
  
  '''
  entity_id_split = model_utils.get_entity_id(primary_key)
  if not entity_id_split:
    return Response(
      data={
        'message': 'Malformed entity id'
      }, 
      content_type='json',
      status=status.HTTP_406_NOT_ACCEPTABLE
    )
  
  return entity_id_split

def exists_entity(entity_id):
  '''
  
  '''
  entity = model_utils.try_get_instance(
    GenericEntity, id=entity_id
  )

  if not entity:
    return Response(
      data={
        'message': 'Entity does not exist'
      }, 
      content_type='json',
      status=status.HTTP_404_NOT_FOUND
    )
  
  return entity

def exists_historical_entity(entity_id, user, historical_id=None):
  '''
  
  '''
  if not historical_id:
    historical_id = model_utils.get_latest_entity_historical_id(
      entity_id, user
    )

  historical_entity = model_utils.try_get_instance(
    GenericEntity, 
    id=entity_id
  ).history.filter(history_id=historical_id)

  if not historical_entity.exists():
    return Response(
      data={
        'message': 'Historical entity version does not exist'
      }, 
      content_type='json',
      status=status.HTTP_404_NOT_FOUND
    )
  
  return historical_entity.first()

''' General helpers '''

def get_entity_version_history(request, entity_id):
  '''
  
  '''
  result = []

  historical_versions = GenericEntity.objects.get(
    id=entity_id
  ).history.all().order_by('-history_id')

  latest = historical_versions.first()
  for version in historical_versions:
    is_published = permission_utils.is_publish_status(
      version, [permission_utils.APPROVAL_STATUS.APPROVED]
    )

    if permission_utils.has_entity_view_permissions(request, version):
      result.append({
        'version_id': version.history_id,
        'version_name': version.name.encode('ascii', 'ignore').decode('ascii'),
        'version_date': version.history_date,
        'is_published': is_published,
        'is_latest': latest.history_id == version.history_id
      })

  return result

''' Formatting helpers '''

def get_layout_from_entity(entity):
  '''

  '''
  layout = entity.template
  if not layout:
    return Response(
      data={
        'message': 'Entity template is missing'
      }, 
      content_type='json',
      status=status.HTTP_404_NOT_FOUND
    )
  
  if not template_utils.is_layout_safe(layout):
    return Response(
      data={
        'message': 'Entity layout is empty'
      }, 
      content_type='json',
      status=status.HTTP_204_NO_CONTENT
    )
  
  version = template_utils.try_get_content(entity.template_data, 'version')
  if not version:
    version = getattr(entity, 'template_version')

  if version:
    template_version = Template.history.get(
      id=entity.template.id,
      template_version=version
    )

    if template_version:
      return template_version
  
  return Response(
    data={
      'message': 'Entity template version does not exist'
    }, 
    content_type='json',
    status=status.HTTP_404_NOT_FOUND
  )

def build_query_from_template(request, user_authed, template=None):
  '''

  '''
  is_dynamic = True

  terms = {}
  where = []
  for key, value in template.items():
    is_active = template_utils.try_get_content(value, 'active')
    requires_auth = template_utils.try_get_content(value, 'requires_auth')

    can_search = template_utils.try_get_content(value, 'search')
    if can_search:
      can_search = template_utils.try_get_content(value['search'], 'api')

    if is_active and can_search and (not requires_auth or (requires_auth and user_authed)):
      param = request.query_params.get(key, None)
      if param:
        if template_utils.try_get_content(value, 'is_base_field'):
          is_dynamic=False

        search_utils.apply_param_to_query(
          terms, where, template, key, param, is_dynamic=is_dynamic, force_term=True, is_api=True
        )

  return terms, where

def get_entity_detail_from_layout(
    entity, fields, user_authed, fields_to_ignore=[], target_field=None
  ):
  '''

  '''
  result = {}
  for field, field_definition in fields.items():
    if target_field is not None and target_field.lower() != field.lower():
      continue

    if field.lower() in fields_to_ignore:
      continue

    is_active = template_utils.try_get_content(field_definition, 'active')
    if is_active == False:
      continue

    requires_auth = template_utils.try_get_content(field_definition, 'requires_auth')
    if requires_auth and not user_authed:
      continue

    if template_utils.is_metadata(entity, field):
      validation = template_utils.get_field_item(
        constants.metadata, field, 'validation', { }
      )
      is_source = validation.get('source')
      
      if is_source:
        result[field] = template_utils.get_metadata_value_from_source(
          entity, field, default=None
        )
      continue
    
    result[field] = template_utils.get_template_data_values(
      entity, fields, field, default=None, hide_user_details=True
    )
  
  return result

def get_entity_detail_from_meta(entity, data, fields_to_ignore=[], target_field=None):
  '''

  '''
  result = {}
  for field in entity._meta.fields:
    field_name = field.name
    if target_field is not None and target_field.lower() != field_name.lower():
      continue

    if field_name.lower() in data or field_name.lower() in fields_to_ignore:
      continue

    field_type = field.get_internal_type()
    if field_type and field_type in constants.STRIPPED_FIELDS:
      continue

    if field_name in constants.API_HIDDEN_FIELDS:
      continue

    field_value = template_utils.get_entity_field(entity, field_name)
    if field_value is None:
      result[field_name] = None
      continue
    
    if isinstance(field, ForeignKey):
      model = field.target_field.model
      model_type = str(model)
      if model_type in constants.USERDATA_MODELS:
        if model_type == str(User):
          result[field_name] = template_utils.get_one_of_field(field_value, ['username', 'name'])
        else:
          result[field_name] = {
            'id': field_value.id,
            'name': template_utils.get_one_of_field(field_value, ['username', 'name'])
          }
        continue
    
    result[field_name] = field_value
  
  return result

def get_ordered_entity_detail(fields, layout, layout_version, entity_versions, data):
  '''
  
  '''
  ordered_keys = list(fields.keys())
  ordered_keys.extend(key for key in data.keys() if key not in ordered_keys)
  ordered_result = { }
  for key in ordered_keys:
    if key in data:
      ordered_result[key] = data[key]
    
  ordered_result = ordered_result | {
    'template': {
      'id': layout.id,
      'name': layout.name,
      'description': layout.description,
      'version': layout_version
    },
    'versions': entity_versions
  }

  return ordered_result

def get_entity_detail(
    request, 
    entity_id, 
    entity, 
    user_authed, 
    fields_to_ignore=[], 
    target_field=None, 
    return_data=False
  ):
  '''

  '''
  layout_response = get_layout_from_entity(entity)
  if isinstance(layout_response, Response):
    return layout_response
  
  layout = layout_response
  layout_definition = template_utils.get_ordered_definition(layout.definition)
  layout_version = layout.template_version

  fields = template_utils.try_get_content(layout_definition, 'fields')
  if fields is None:
    return None
    
  result = get_entity_detail_from_layout(
    entity, fields, user_authed, fields_to_ignore=fields_to_ignore, target_field=target_field
  )

  result = result | get_entity_detail_from_meta(
    entity, result, fields_to_ignore=fields_to_ignore, target_field=target_field
  )

  entity_versions = get_entity_version_history(request, entity_id)
  if target_field is None:
    result = get_ordered_entity_detail(fields, layout, layout_version, entity_versions, result)

  if return_data:
    return result
  
  return Response(
    data=result,
    status=status.HTTP_200_OK
  )

def build_final_codelist_from_concepts(entity, concept_information):
  '''
  
  '''
  result = []
  for concept in concept_information:
    concept_id = concept['concept_id']
    concept_version = concept['concept_version_id']

    # Get concept entity for additional data, skip if we're not able to find it
    concept_entity = Concept.history.get(
      id=concept_id, history_id=concept_version
    )
    if not concept_entity:
      continue
    
    concept_data = {
      'concept_id': concept_id,
      'concept_version_id': concept_version,
      'concept_name': concept_entity.name,
      'coding_system': concept_entity.coding_system,
      'entity_id': entity.id,
      'entity_version_id': entity.history_id,
      'entity_name': entity.name
    }

    # Get codes
    concept_codes = model_utils.get_concept_codelist(concept_id, concept_version, incl_logical_types=[constants.CLINICAL_RULE_TYPE.INCLUDE.value], incl_attributes=False)
    concept_codes = [data | concept_data for data in concept_codes]

    result += concept_codes
  
  return result

def get_codelist_from_entity(entity):
  '''
  
  '''
  layout_response = get_layout_from_entity(entity)
  if isinstance(layout_response, Response):
    return layout_response
  layout = layout_response
  fields = template_utils.try_get_content(layout.definition, 'fields')

  concept_field = None
  for field, definition in fields.items():
    validation = template_utils.try_get_content(definition, 'validation')
    if validation is None:
      continue

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None or field_type != 'concept':
      continue

    concept_field = field
    break
  
  if not concept_field:
    return Response(
      data={
        'message': 'Entity template does not contain a codelist'
      },
      content_type='json',
      status=status.HTTP_400_BAD_REQUEST
    )
  
  concept_information = template_utils.try_get_content(
    entity.template_data, 'concept_information'
  )
  if not concept_information:
    return Response(
      data={
        'message': 'Entity does not contain a codelist'
      },
      content_type='json',
      status=status.HTTP_404_NOT_FOUND
    )
  
  codes = build_final_codelist_from_concepts(entity, concept_information)
  
  return Response(
    data=codes,
    status=status.HTTP_200_OK
  )

def validate_api_create_update_form(request, method):
  form_errors = []
  form = gen_utils.get_request_body(request)
  form = create_utils.validate_entity_form(
    request, form, form_errors, method=method
  )

  if form is None:
    return Response(
      data={
        'message': 'Invalid form',
        'errors': form_errors
      }, 
      content_type='json',
      status=status.HTTP_400_BAD_REQUEST
    )
  
  return form

def create_update_from_api_form(request, form):
  form_errors = []
  entity = create_utils.create_or_update_entity_from_form(request, form, form_errors)
  if entity is None:
      return Response(
        data={
          'message': 'Data submission is invalid',
          'errors': form_errors
        }, 
        content_type='json',
        status=status.HTTP_400_BAD_REQUEST
      )
  
  return entity
