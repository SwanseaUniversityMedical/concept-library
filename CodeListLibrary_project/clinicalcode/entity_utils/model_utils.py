from django.apps import apps
from django.db.models import ForeignKey
from django.forms.models import model_to_dict
from django.contrib.auth.models import User, Group

import re
import json
import simple_history

from . import gen_utils
from ..models.GenericEntity import GenericEntity
from ..models.Tag import Tag
from ..models.CodingSystem import CodingSystem
from ..models import Brand
from ..models import Tag
from .constants import (USERDATA_MODELS, STRIPPED_FIELDS, APPROVAL_STATUS,
                        GROUP_PERMISSIONS, WORLD_ACCESS_PERMISSIONS)

def try_get_instance(model, **kwargs):
    """
      Safely attempts to get an instance
    """
    try:
        instance = model.objects.get(**kwargs)
    except:
        return None
    else:
        return instance

def try_get_entity_history(entity, history_id):
    """
      Safely attempts to get an entity's historical record given an entity
      and a history id
    """
    if not entity:
        return None

    try:
        instance = entity.history.get(history_id=history_id)
    except:
        return None
    else:
        return instance

def try_get_brand(request, default=None):
    """
      Safely get the Brand instance from the RequestContext
    """
    current_brand = request.CURRENT_BRAND
    if gen_utils.is_empty_string(current_brand):
        return default
    return try_get_instance(Brand, name=current_brand)

def get_entity_id(primary_key):
    """
      Splits an entity's varchar primary key into its numerical component
    """
    entity_id = re.split('(\d.*)', primary_key)
    if len(entity_id) >= 2 and entity_id[0].isalpha() and entity_id[1].isdigit():
        entity_id[0] = entity_id[0].upper()
        return entity_id[:2]
    return False

def get_brand_collection_ids(brand_name):
    """
      Returns list of collections (tags) ids associated with the brand
    """
    if Brand.objects.all().filter(name__iexact=brand_name).exists():
        brand = Brand.objects.get(name__iexact=brand_name)
        brand_collection_ids = list(Tag.objects.filter(collection_brand=brand.id).values_list('id', flat=True))
        return brand_collection_ids
    return [-1]

def get_entity_approval_status(entity_id, historical_id):
    """
      Gets the entity's approval status, given an entity id and historical id
    """
    entity = GenericEntity.history.filter(id=entity_id, history_id=historical_id)
    if entity.exists():
        return entity.first().publish_status

def is_legacy_entity(entity_id, entity_history_id):
    """
      Checks whether this entity_id and entity_history_id match the latest record
      to determine whether a historical entity is legacy or not
    """
    latest_entity = GenericEntity.history.filter(id=entity_id)
    if not latest_entity.exists():
        return False

    latest_entity = latest_entity.latest()
    return latest_entity.history_id != entity_history_id

def jsonify_object(obj, remove_userdata=True, strip_fields=True, strippable_fields=None, dump=True):
    """
      JSONifies/Dictifies instance of a model
        - removes userdata related data for safe usage within template
        - removes specific fields that are unrelated to templates e.g. SearchVectorField
        - able to strip fields from a model, given a list of field names to strip
        - able to dump to json if requested
    """
    instance = model_to_dict(obj)

    if remove_userdata or strip_fields:
        for field in obj._meta.fields:
            field_type = field.get_internal_type()
            if strip_fields and field_type and field.get_internal_type() in STRIPPED_FIELDS:
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
    """
      Returns a dict that describes a tag given its id and type
    """
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
    """
      Returns a dict that describes a coding system given that
      the coding_system parameter passed is either an obj or an int
      that references a coding_system by its codingsystem_id
    """
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
    """
      Attempts to return a dict that describes a userdata field e.g. a user, or a group
      in a human readable format
    """
    hide_user_id = False
    if kwargs.get('hide_user_details'):
        hide_user_id = kwargs.pop('hide_user_details')

    instance = try_get_instance(model, **kwargs)
    if not instance:
        return None

    if isinstance(instance, Group):
        return {'id': instance.pk, 'name': instance.name}
    elif isinstance(instance, User):
        if hide_user_id:
            details = {}
        else:
            details = {'id': instance.pk}

        return details | {'username': instance.username}

    return details

def append_coding_system_data(systems):
    """
      Appends the number of available codes within a Coding System's
      codelist as well as whether it is searchable
        - This is used primarily for the create/update page to determine
          whether a search rule is applicable

      Args:
        systems (list of dicts) A list of dicts that contains the coding systems of interest
            e.g. {name: (str), value: (int)} where value is the pk

      Returns:
        A list of dicts that has the number of codes/searchable status appended,
        as defined by their code reference tables
    """
    for i, system in enumerate(systems):
        try:
            coding_system = CodingSystem.objects.get(codingsystem_id=system.get('value'))
            table = coding_system.table_name.replace('clinicalcode_', '')
            codes = apps.get_model(app_label='clinicalcode', model_name=table)
            count = codes.objects.count() > 0
            systems[i]['code_count'] = count
            systems[i]['can_search'] = count
        except:
            continue

    return systems

def modify_entity_change_reason(entity, reason):
    """
      Modify an entity's HistoricalRecord to reflect the change reason on update
    """
    if entity is None:
        return

    reason = (reason[:98] + '..') if len(reason) > 98 else reason
    simple_history.utils.update_change_reason(entity, reason)
