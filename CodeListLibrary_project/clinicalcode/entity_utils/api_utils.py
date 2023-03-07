from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from copy import deepcopy
import json

from ..models.GenericEntity import GenericEntity
from . import model_utils
from . import template_utils
from . import permission_utils
from . import search_utils
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

def exists_entity(entity_prefix, entity_id):
  '''
  
  '''
  entity = model_utils.try_get_instance(
    GenericEntity, entity_prefix=entity_prefix, entity_id=entity_id
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

def exists_historical_entity(entity_prefix, entity_id, user_authed, historical_id=None):
  '''
  
  '''
  if not historical_id:
    historical_id = model_utils.get_latest_entity_historical_id(
      entity_prefix, entity_id, user_authed
    )

  historical_entity = model_utils.try_get_instance(
    GenericEntity, 
    entity_prefix=entity_prefix, 
    entity_id=entity_id
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

def get_entity_version_history(request, entity_prefix, entity_id):
  '''
  
  '''
  result = []

  historical_versions = GenericEntity.objects.get(
    entity_prefix=entity_prefix, entity_id=entity_id
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
  
  return layout

def get_verbose_metadata_field(entity, field):
  '''
  
  '''
  if template_utils.try_get_content(constants.metadata[field], 'source'):
    result = template_utils.get_metadata_value_from_source(entity, field, default=None)
  else:
    result = template_utils.get_entity_field(entity, field)

  return Response(
    data=result or {},
    content_type='json',
    status=status.HTTP_200_OK
  )

def get_verbose_template_field(entity, layout, field):
  '''
  
  '''

  result = template_utils.get_template_data_values(entity, layout, field, default=None)
  if not result:
    result = template_utils.get_entity_field(entity, field)

  return Response(
    data=result,
    content_type='json',
    status=status.HTTP_200_OK
  )

def export_field(entity, field, user_authed):
  '''
  
  '''
  layout_response = get_layout_from_entity(entity)
  if isinstance(layout_response, Response):
    return layout_response
  layout = layout_response

  base_fields = constants.metadata
  if field in base_fields:
    is_active = template_utils.try_get_content(base_fields[field], 'active')
    authed_only = template_utils.try_get_content(base_fields[field], 'requires_auth') and not user_authed
    
    if not is_active or authed_only:
      return Response(
        data={
          'message': 'You are not authorised to access this field'
        }, 
        content_type='json',
        status=status.HTTP_401_UNAUTHORIZED
      )
    
    return get_verbose_metadata_field(entity, field)
  elif template_utils.get_layout_field(layout, field):
    return get_verbose_template_field(entity, layout, field)
  
  return Response(
    data={
      'message': 'Entity does not contain field: %s' % field
    }, 
    content_type='json',
    status=status.HTTP_404_NOT_FOUND
  )

def transform_field_data(layout, data, user_authed):
  '''
  
  '''
  result = deepcopy(data)
  for key, body in layout.items():
    is_active = template_utils.try_get_content(body, 'active')
    authed_only = template_utils.try_get_content(body, 'requires_auth') and not user_authed
    should_hide = template_utils.try_get_content(body, 'hide_if_empty') and template_utils.try_get_content(result, key) is None

    key_exists = key in result
    if (not is_active or authed_only or should_hide) and key_exists:
      del result[key]
  
  return result

def get_entity_json_detail(request, entity_id, entity, user_authed):
  '''

  '''  
  layout_response = get_layout_from_entity(entity)
  if isinstance(layout_response, Response):
    return layout_response
  layout = layout_response

  if user_authed:
    created_by = model_utils.try_get_instance(User, id=entity.created_by_id)
    created_by = created_by and created_by.username

    updated_by = model_utils.try_get_instance(User, id=entity.updated_by_id)
    updated_by = updated_by and updated_by.username
  
  base_data = {
    'name': entity.name,
    'author': entity.author,
    'tags': entity.tags,
    'collections': entity.collections,
    'created': entity.created,
    'updated': entity.updated,
    'created_by': created_by,
    'updated_by': updated_by,
    'definition': entity.definition,
    'implementation': entity.implementation,
    'validation': entity.validation,
    'publications': entity.publications,
    'citation_requirements': entity.citation_requirements
  }

  result = {
    'id': entity_id,
    'version_id': entity.history_id,
    'data': transform_field_data(constants.metadata, base_data, user_authed)
  }

  result['data'] = result['data'] | transform_field_data(
    layout.definition['fields'], entity.template_data, user_authed
  )

  return Response(
    data=result,
    content_type='json',
    status=status.HTTP_200_OK
  )

def build_query_from_template(request, user_authed, template=None):
  is_dynamic = True
  if not template:
    template = constants.metadata
    is_dynamic = False

  terms = {}
  for key, value in template.items():
    is_active = template_utils.try_get_content(value, 'active')
    requires_auth = template_utils.try_get_content(value, 'requires_auth')
    can_search = template_utils.try_get_content(value, 'api_search')

    if is_active and can_search and (not requires_auth or (requires_auth and user_authed)):
      param = request.query_params.get(key, None)
      if param:
        search_utils.apply_param_to_query(
          terms, template, key, param, is_dynamic=is_dynamic, force_term=True
        )

  return terms or None
