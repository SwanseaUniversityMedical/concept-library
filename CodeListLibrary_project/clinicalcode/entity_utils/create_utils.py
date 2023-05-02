from django.apps import apps
from django.db.models import Q, F
from django.utils.timezone import make_aware
from datetime import datetime

from ..models.EntityClass import EntityClass
from ..models.Template import Template
from ..models.GenericEntity import GenericEntity
from ..models.CodingSystem import CodingSystem
from ..models.Concept import Concept
from ..models.Component import Component
from ..models.CodeList import CodeList
from ..models.Code import Code
from ..models.PublishedGenericEntity import PublishedGenericEntity
from . import gen_utils
from . import model_utils
from . import permission_utils
from . import template_utils
from . import constants

def try_validate_entity(request, entity_id, entity_history_id):
    '''
      Validates existence of an entity and whether the user has permissions to modify it
    '''
    if not permission_utils.can_user_edit_entity(request, entity_id, entity_history_id):
        return False
    
    return GenericEntity.history.get(id=entity_id, history_id=entity_history_id)

def get_createable_entities(request):
    '''
        Used to retrieve information relating to the entities that can
        be created and their associated templates
    '''
    entities = EntityClass.objects.all().values('id', 'name', 'description', 'entity_prefix')
    templates = Template.objects.filter(
        entity_class__id__in=entities.values_list('id', flat=True)
    ) \
    .values('id', 'template_version', 'entity_class__id', 'name', 'description')
    
    return {
        'entities': list(entities),
        'templates': list(templates)
    }

def get_template_creation_data(entity, layout, field, default=[]):
    '''
        Used to retrieve assoc. data values for specific keys, e.g.
        concepts, in its expanded format for use with create/update pages
    '''
    data = template_utils.get_entity_field(entity, field)
    info = template_utils.get_layout_field(layout, field)
    if not info or not data:
        return default
    
    if info.get('is_base_field'):
        info = template_utils.try_get_content(constants.metadata, field)

    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default
    
    if field_type == 'concept':
        values = []
        for item in data:
            value = model_utils.get_clinical_concept_data(
                item['concept_id'],
                item['concept_version_id'],
                aggregate_component_codes=True
            )

            if value:
                values.append(value)
        
        return values
    
    if template_utils.is_metadata(entity, field):
        return template_utils.get_metadata_value_from_source(entity, field, default=default)
    
    return template_utils.get_template_data_values(entity, layout, field, default=default)

def try_add_computed_fields(field, form_data, form_template, data):
    '''
        Checks to see if any of our fields have any computed data
        that we need to collect from a child or related field
    '''
    field_data = template_utils.get_layout_field(form_template, field)
    if field_data is None:
        return
    
    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        return
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type == 'concept':
        # Derive the coding systems of each child Concept
        output = [ ]
        for concept in form_data[field]:
            details = concept.get('details')
            if details is None:
                continue
            
            coding_system = details.get('coding_system')
            if coding_system is None:
                continue
            output.append(coding_system)
        data['coding_system'] = output

def try_validate_sourced_value(template, data, default=None):
    '''
        Validates the query param based on its field type as defined by the template or metadata
        by examining its source and its current datatype
    '''
    validation = template_utils.try_get_content(template, 'validation')
    if validation:
        if 'source' in validation:
            try:
                source_info = validation.get('source')
                model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))

                if isinstance(data, list):
                    query = {
                        'pk__in': data
                    }
                else:
                    query = {
                        'pk': data
                    }

                if 'filter' in source_info:
                    query = query | source_info['filter']
                
                queryset = model.objects.filter(Q(**query))
                queryset = list(queryset.values_list('id', flat=True))

                if isinstance(data, list):
                    return queryset if len(queryset) > 0 else default
                else:
                    return queryset[0] if len(queryset) > 0 else default
            except:
                return default
        elif 'options' in validation:
            options = validation['options']

            if isinstance(data, list):
                cleaned = [ ]
                for item in data:
                    value = str(item)
                    if value in options:
                        cleaned.append(value)
                return cleaned if len(cleaned) > 0 else default
            else:
                data = str(data)
                if data in options:
                    return data
    
    return default

def validate_form_method(form_method, errors=[], default=None):
    '''
        Validates the form method when updating or creating an object
    '''
    form_method = gen_utils.parse_int(form_method, None)
    if form_method is None:
        errors.append('No form method enum was provided.')
        return default

    if form_method not in constants.FORM_METHODS:
        errors.append('No matching form method found.')
        return default
    
    return form_method

def validate_form_template(form_template, errors=[], default=None):
    '''
        Validates the template id and version given by a form
    '''
    if form_template is None:
        errors.append('No template parameter was provided.')
        return default

    template_id = gen_utils.parse_int(form_template.get('id'), None)
    template_version = gen_utils.parse_int(form_template.get('version'), None)
    if not template_id or not template_version:
        errors.append('Form template is invalid, unable to find either the ID or the template version')
        return default
    
    template = Template.history.filter(
      id=template_id,
      template_version=template_version
    )

    if not template.exists():
        errors.append(f'Unable to find form template with an ID of {template_id} and a version of {template_version}')
        return default
    
    return template.first()

def validate_form_data_type(form_data, errors=[], default=None):
    '''
        Validates the datatype of the form data
    '''
    if form_data is None:
        errors.append('No form data was provided.')
        return default
    
    if not isinstance(form_data, dict):
        errors.append(f'Expected dict as form data, got "{type(form_data)}"')
        return default
    
    return form_data
    
def validate_form_entity(form_entity, form_method, errors=[], default=None):
    '''
        Validates the form's entity, assuming an update form method was called
    '''
    if form_method is None:
        return
    
    if form_method == constants.FORM_METHODS.CREATE:
        return default

    if form_entity is None:
        errors.append('No entity parameter was provided when submitting an update form.')
        return default
    
    if not isinstance(form_entity, dict):
        errors.append(f'Expected a dict for the form entity, got "{type(form_entity)}"')
        return default

    entity_id = form_entity.get('id')
    history_id = gen_utils.parse_int(form_entity.get('history_id'), None)
    if not entity_id or not history_id:
        errors.append('Form entity is invalid, unable to find either the ID or the entity history ID')
        return default
    
    entity = GenericEntity.history.filter(
        id=entity_id,
        history_id=history_id
    )

    if not entity.exists():
        errors.append(f'Unable to find an entity with an ID of {entity_id} and a version of {history_id}')
        return default
    
    return entity.first()

def validate_template_field(template, field):
    '''
        Validates whether this field applies to our current template
    '''
    fields = template_utils.get_layout_fields(template)
    if fields is None:
        return False
    
    return field in fields

def validate_computed_field(request, field, field_data, value, errors=[]):
    '''
        Computed fields, e.g. Groups, that can be computed based on RequestContext
    '''
    user = request.user
    if user is None:
        errors.append('RequestContext invalid')
        return None

    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        return value
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return value
    
    field_info = GenericEntity._meta.get_field(field)
    if not field_info:
        return
    
    field_type = field_info.get_internal_type()
    if field_type != 'ForeignKey':
        return
    
    model = field_info.target_field.model
    if model is not None:
        field_value = gen_utils.try_value_as_type(value, field_type, validation)
        if field_value is None:
            return None
        
        instance = model_utils.try_get_instance(model, pk=field_value)
        if instance is None:
            errors.append(f'"{field}" is invalid')
            return None
        
        if field == 'group':
            is_member = user.is_superuser or user.groups.filter(name__iexact=instance.name).exists()
            if not is_member:
                errors.append(f'Tried to set {field} without being a member of that group.')
                return None
        
        return instance
    
    return value

def validate_concept_form(form, errors):
    '''
        Validates a concept form
    '''
    is_new_concept = form.get('is_new')
    is_dirty_concept = form.get('is_dirty')
    concept_id = gen_utils.parse_int(form.get('concept_id'), None)
    concept_history_id = gen_utils.parse_int(form.get('concept_history_id'), None)

    field_value = {
        'concept': { },
        'components': [ ],
    }

    if not is_new_concept and concept_id is not None and concept_history_id is not None:
        concept = model_utils.try_get_instance(Concept, id=concept_id)
        concept = model_utils.try_get_entity_history(concept, history_id=concept_history_id)
        if concept is None:
            errors.append(f'Child Concept entity with ID {concept_id} and history ID {concept_history_id} does not exist.')
            return None
        field_value['concept']['id'] = concept_id
        field_value['concept']['history_id'] = concept_history_id
    else:
        is_new_concept = True
    
    concept_details = form.get('details')
    if concept_details is None or not isinstance(concept_details, dict):
        errors.append(f'Invalid concept with ID {concept_id} - details is a non-nullable dict field.')
        return None

    concept_name = gen_utils.try_value_as_type(concept_details.get('name'), 'string')
    if concept_name is None:
        errors.append(f'Invalid concept with ID {concept_id} - name is non-nullable, string field.')
        return None
    
    concept_coding = gen_utils.parse_int(concept_details.get('coding_system'), None)
    concept_coding = model_utils.try_get_instance(CodingSystem, pk=concept_coding)
    if concept_coding is None:
        errors.append(f'Invalid concept with ID {concept_id} - coding_system is non-nullable int field.')
        return None

    concept_components = form.get('components')
    if concept_components is None or not isinstance(concept_components, list):
        errors.append(f'Invalid concept with ID {concept_id} - components is a non-nullable list field.')
        return None
    
    components = [ ]
    for concept_component in concept_components:
        component = { }

        is_new_component = concept_component.get('is_new')
        component_id = gen_utils.parse_int(concept_component.get('id'), None)
        if not is_new_component and component_id is not None:
            historical_component = Component.history.filter(id=component_id)
            if not historical_component.exists():
                errors.append(f'Invalid concept with ID {concept_id} - component is not valid')
                return None
            component['id'] = component_id
        else:
            is_new_component = True
        
        component_name = gen_utils.try_value_as_type(concept_component.get('name'), 'string')
        if component_name is None:
            errors.append(f'Invalid concept with ID {concept_id} - Component names are non-nullable, string fields.')
            return None
        
        component_logical_type = concept_component.get('logical_type')
        if component_logical_type is None or component_logical_type not in constants.CLINICAL_RULE_TYPE:
            errors.append(f'Invalid concept with ID {concept_id} - Component logical types are non-nullable, string fields.')
            return None
        component_logical_type = constants.CLINICAL_RULE_TYPE.from_name(component_logical_type)
        
        component_source_type = concept_component.get('source_type')
        if component_source_type is None or component_source_type not in constants.CLINICAL_CODE_SOURCE:
            errors.append(f'Invalid concept with ID {concept_id} - Component source types are non-nullable, string fields.')
            return None
        component_source_type = constants.CLINICAL_CODE_SOURCE.from_name(component_source_type)
        
        component_source = concept_component.get('source')
        if component_source_type == constants.CLINICAL_CODE_SOURCE.SEARCH_TERM and (component_source is None or gen_utils.is_empty_string(component_source)):
            errors.append(f'Invalid concept with ID {concept_id} - Component sources are non-nullable, string fields for search terms.')
            return None

        component_codes = concept_component.get('codes')
        if not isinstance(component_codes, list) or len(component_codes) < 1:
            errors.append(f'Invalid concept with ID {concept_id} - Component codes is a non-nullable, list field')
            return None
        
        codes = [ ]
        for component_code in component_codes:
            code = { }
            if not isinstance(component_code, dict):
                errors.append(f'Invalid concept with ID {concept_id} - Component code items are non-nullable, dict field')
                return None
            
            is_new_code = component_code.get('is_new')
            code_id = gen_utils.parse_int(component_code.get('id'), None)
            if not is_new_code and code_id is not None:
                historical_code = Code.history.filter(id=code_id)
                if not historical_code.exists():
                    errors.append(f'Invalid concept with ID {concept_id} - Code is not valid')
                    return None
                code['id'] = code_id
            else:
                is_new_code = True
            
            code_name = gen_utils.try_value_as_type(component_code.get('code'), 'string')
            if gen_utils.is_empty_string(code_name):
                errors.append(f'Invalid concept with ID {concept_id} - A code\'s code is a non-nullable, string field')
                return None

            code_desc = gen_utils.try_value_as_type(component_code.get('description'), 'string')
            if gen_utils.is_empty_string(code_desc):
                errors.append(f'Invalid concept with ID {concept_id} - A code\'s description is a non-nullable, string field')
                return None
            
            code['is_new'] = is_new_code
            code['code'] = code_name
            code['description'] = code_desc
            codes.append(code)

        component['is_new'] = is_new_component
        component['name'] = component_name
        component['logical_type'] = component_logical_type
        component['component_type'] = component_source_type
        component['source'] = component_source
        component['codes'] = codes
        components.append(component)

    field_value['concept']['is_new'] = is_new_concept
    field_value['concept']['is_dirty'] = is_dirty_concept
    field_value['concept']['name'] = concept_name
    field_value['concept']['coding_system'] = concept_coding
    field_value['components'] = components

    return field_value

def validate_related_entities(field, field_data, value, errors):
    '''
        Validates related entities, e.g. Concepts
    '''    
    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        # Exit without error since we haven't included any validation
        return value
    
    field_required = template_utils.try_get_content(validation, 'mandatory')
    if field_required and value is None:
        errors.append(f'"{field}" is a non-nullable, required field')
        return None
    
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type == 'concept':
        if not field_required and (value is None or (not isinstance(value, list) or len(value) < 1)):
            return list()
        
        if not isinstance(value, list) or len(value) < 1:
            errors.append(f'Expected {field} as list, got {type(value)}')
            return None
        
        valid = True
        cleaned = [ ]
        for item in value:
            concept = validate_concept_form(item, errors)
            if concept is None:
                valid = False
                continue
            cleaned.append(concept)
        
        if not valid:
            return None
        return cleaned
    
    return value

def validate_metadata_value(request, field, value, errors=[]):
    '''
        Validates the form's field value against the metadata fields
    '''
    field_data = template_utils.try_get_content(constants.metadata, field)
    if field_data is None:
        errors.append(f'"{field}" is a non-existent field for this template')
        return value, False
    
    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        # Exit without error since we haven't included any validation
        return value, False
    
    field_required = template_utils.try_get_content(validation, 'mandatory')
    if field_required and value is None:
        errors.append(f'"{field}" is a non-nullable, required field')
        return value, False
    
    if 'source' in validation or 'options' in validation:
        field_value = try_validate_sourced_value(field_data, value)
        if field_value is None and field_required:
            errors.append(f'"{field}" is invalid')
            return field_value, False
        return field_value, True
    
    field_computed = template_utils.try_get_content(validation, 'computed')
    if field_computed is not None:
        field_value = validate_computed_field(request, field, field_data, value, errors)
        if field_value is None and field_required:
            errors.append(f'"{field}" is invalid.')
            return field_value, False
        return field_value, True
    
    field_type = template_utils.try_get_content(validation, 'type')
    field_value = gen_utils.try_value_as_type(value, field_type, validation)
    if field_type is not None and field_value is None:
        errors.append(f'"{field}" is invalid')
        return field_value, False
    
    return field_value, True

def validate_template_value(request, field, form_template, value, errors=[]):
    '''
        Validates the form's field value against the entity template
    '''
    field_data = template_utils.get_layout_field(form_template, field)
    if field_data is None:
        errors.append(f'"{field}" is a non-existent field for this template')
        return value, False
    
    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        # Exit without error since we haven't included any validation
        return value, False
    
    field_required = template_utils.try_get_content(validation, 'mandatory')
    if field_required and value is None:
        errors.append(f'"{field}" is a non-nullable, required field')
        return value, False
    
    if 'source' in validation or 'options' in validation:
        field_value = try_validate_sourced_value(field_data, value)
        if field_value is None and field_required:
            errors.append(f'"{field}" is invalid')
            return field_value, False
        return field_value, True
    
    field_computed = template_utils.try_get_content(validation, 'computed')
    if field_computed is not None:
        field_value = validate_computed_field(request, field, field_data, value, errors)
        if field_value is None and field_required:
            errors.append(f'"{field}" is invalid.')
            return field_value, False
        return field_value, True

    field_children = template_utils.try_get_content(validation, 'has_children')
    if field_children is not None:
        field_value = validate_related_entities(field, field_data, value, errors)
        if field_value is None and field_required:
            errors.append(f'"{field}" is invalid.')
            return field_value, False
        return field_value, True
    
    field_type = template_utils.try_get_content(validation, 'type')
    field_value = gen_utils.try_value_as_type(value, field_type, validation)
    if field_type is not None and field_value is None:
        errors.append(f'"{field}" is invalid')
        return field_value, False

    return field_value, True

def validate_entity_form(request, content, errors=[], method=None):
    '''
        Validates & Cleans the entity create/update form

        Args:
            request {RequestContext}: the request context of the form
            content {dict}: a dict containing the form data submitted via POST
            errors {list|null}: a list that is passed by reference to append error data
        
        Returns:
            {dict|null} - null value is returned if validation is not successful
    '''

    # Early exit if any of the base form data is invalid
    if method is None:
        form_method = content.get('method')
        form_method = validate_form_method(form_method, errors)
    else:
        form_method = validate_form_method(method, errors)
    
    form_template = content.get('template')
    form_template = validate_form_template(form_template, errors)

    form_data = content.get('data')
    form_data = validate_form_data_type(form_data, errors)
    
    form_entity = content.get('entity')
    form_entity = validate_form_entity(form_entity, form_method, errors)

    if len(errors) > 0:
        return
    
    # Validate & Clean the form data
    top_level_data = { }
    template_data = { }
    for field, value in form_data.items():
        if template_utils.is_metadata(GenericEntity, field):
            field_value, validated = validate_metadata_value(request, field, value, errors)
            top_level_data[field] = field_value
            continue

        if validate_template_field(form_template, field):
            field_value, validated = validate_template_value(request, field, form_template, value, errors)
            template_data[field] = field_value
        
            if not validated:
                continue
            try_add_computed_fields(field, form_data, form_template, template_data)

    if len(errors) > 0:
        return
    
    return {
        'method': constants.FORM_METHODS(form_method),
        'entity': form_entity,
        'template': form_template,
        'data': {
            'metadata': top_level_data,
            'template': template_data,
        }
    }

def try_update_concept(request, item):
    '''
        Updates a concept, given the item data validated from the Phentoype builder form

        Args:
            request {RequestContext}: the request context of the form
            item {dict}: the data computed from the concept validation method
        
        Returns:
            {Concept()} - the resulting, updated Concept entity
        
    '''
    user = request.user
    if user is None:
        return None
    
    concept_data = item.get('concept')
    components_data = item.get('components')
    if concept_data is None or components_data is None:
        return None

    concept_id = concept_data.get('id')
    if concept_id is None:
        return None
    
    concept = model_utils.try_get_instance(Concept, id=concept_id)
    if concept is None:
        return None
    
    if not permission_utils.user_has_concept_ownership(user, concept):
        return None

    # Update concept fields
    concept.name = concept_data.get('name')
    concept.coding_system = concept_data.get('coding_system')
    concept.modified = make_aware(datetime.now())
    concept.modified_by = request.user

    # Clear existing components
    for obj in concept.component_set.all():
        obj.delete()
    
    for obj in concept.conceptcodeattribute_set.all():
        obj.delete()
    
    # Create new components, codelists and associated codes
    for obj in components_data:
        component = Component.objects.create(
            name=obj.get('name'),
            logical_type=obj.get('logical_type'),
            component_type=obj.get('component_type'),
            source=obj.get('source'),
            created_by=request.user,
            concept=concept
        )

        codelist = CodeList.objects.create(component=component, description='-')
        for code in obj.get('codes'):
            Code.objects.create(
                code_list=codelist,
                code=code.get('code'),
                description=code.get('description')
            )
    
    concept.save()
    return concept

def try_create_concept(request, item):
    '''
        Creates a concept, given the item data validated from the Phentoype builder form

        Args:
            request {RequestContext}: the request context of the form
            concept_id {integer}: the id of the concept
            item {dict}: the data computed from the concept validation method
        
        Returns:
            {Concept()} - the resulting, created Concept entity
    '''
    user = request.user
    if user is None:
        return None
    
    concept_data = item.get('concept')
    components_data = item.get('components')
    if concept_data is None or components_data is None:
        return None

    # Create the new concept
    concept = Concept()
    concept.name = concept_data.get('name')
    concept.coding_system = concept_data.get('coding_system')
    concept.created_by = user
    concept.entry_date = make_aware(datetime.now())
    concept.owner_access = constants.OWNER_PERMISSIONS.EDIT
    concept.owner_id = user.id
    concept.save()
    
    concept = Concept.objects.get(pk=concept.pk)
    concept.history.latest().delete()

    # Create new components, codelists and associated codes
    for obj in components_data:
        component = Component.objects.create(
            name=obj.get('name'),
            logical_type=obj.get('logical_type'),
            component_type=obj.get('component_type'),
            source=obj.get('source'),
            created_by=request.user,
            concept=concept
        )

        codelist = CodeList.objects.create(component=component, description='-')
        for code in obj.get('codes'):
            Code.objects.create(
                code_list=codelist,
                code=code.get('code'),
                description=code.get('description')
            )

    concept.save()
    return concept

def build_related_entities(request, field_data, packet, override_dirty=False):
    '''
        Used to build related entities, e.g. concepts, for entities

        Args:
            request {RequestContext}: the request context of the form
            field {string}: name of the field
            field_data {dict}: the associated template layout field
            packet {*}: the field data value
            override_dirty {boolean}: overrides the is_dirty check for entity creation

        Returns:
            {list|null} - list of entity dicts (id, hid) created/updated, or null value is returned if this method fails
    '''
    validation = template_utils.try_get_content(field_data, 'validation')
    if validation is None:
        return None

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return None
    
    if field_type == 'concept':
        entities = [ ]
        for item in packet:
            concept = item.get('concept')
            if concept is None:
                continue

            concept_id = concept.get('id')
            if concept_id is not None:
                # If we're dirty, or we want to override, update the concept
                if override_dirty or concept.get('is_dirty'):
                    result = try_update_concept(request, item)
                    if result is not None:
                        entities.append(result.history.latest())
                        continue
                
                # If we're not dirty, append the current concept
                concept_history_id = concept.get('history_id')
                if concept_history_id is not None:
                    result = model_utils.try_get_instance(Concept, id=concept_id)
                    result = model_utils.try_get_entity_history(result, history_id=concept_history_id)
                    if result is not None:
                        entities.append(result)
                        continue            
            
            # Create new concept & components
            result = try_create_concept(request, item)
            if result is None:
                continue
            entities.append(result.history.latest())

        # Build { id, history_id } concept list
        return [
            {
                'concept_id': obj.id,
                'concept_version_id': obj.history_id
            }
            for obj in entities
        ]

    return None

def create_or_update_entity_from_form(request, form, errors=[], override_dirty=False):
    '''
        Used to create or update entities - this method assumes you have
        previously validated the content of the form using the validate_entity_form method

        Args:
            request {RequestContext}: the request context of the form
            form {dict}: a dict containing the validate_entity_form method result
            override_dirty {boolean}: overrides the is_dirty check for child entity creation
        
        Returns:
            {GenericEntity|null} - null value is returned if this method fails

    '''
    user = request.user
    if user is None:
        return

    form_method = form.get('method')
    form_template = form.get('template')
    form_data = form.get('data')

    # Confirm our form data is valid
    if form_template is None:
        errors.append('Form template is invalid because it does not exist')
        return
    
    template_instance = model_utils.try_get_instance(Template, id=form_template.id)
    if template_instance is None:
        errors.append('Form template parent was null')
        return
    
    template_fields = template_utils.get_layout_fields(template_instance, None)
    if template_fields is None:
        errors.append('Form template is invalid because it is not safe')
        return
    
    metadata = form_data.get('metadata')
    template = form_data.get('template')
    if metadata is None or template is None:
        errors.append('Missing form data')
        return
    
    # If we're attempting to update we should confirm we have the perms to do so
    form_entity = form.get('entity')
    if form_entity is not None:
        entity = GenericEntity.objects.get(id=form_entity.id)
        if entity is None or not permission_utils.can_user_edit_entity(request, entity_id=form_entity.id, entity_history_id=form_entity.history_id):
            errors.append('You do not have permissions to modify this entity')
            return
        form_entity = entity
    
    # Build any validated children
    template_data = { }
    for field, packet in template.items():
        field_data = template_utils.get_layout_field(form_template, field)
        if field_data is None:
            continue

        validation = template_utils.try_get_content(field_data, 'validation')
        if validation is None or not validation.get('has_children'):
            template_data[field] = packet
            continue
        
        field_value = build_related_entities(request, field_data, packet, override_dirty)
        if field_value is None:
            continue
        template_data[field] = field_value
    
    # Add any missing nullable fields from the template
    for field, packet in template_fields.items():
        if packet.get('is_base_field'):
            continue
        
        field_value = template_data.get(field)
        if field_value:
            continue
        template_data[field] = None

    # Create or update the entity
    entity = None
    template_data['version'] = form_template.template_version
    if form_method == constants.FORM_METHODS.CREATE:
        entity = GenericEntity(
            **metadata,
            template=template_instance,
            template_version=form_template.template_version,
            template_data=template_data,
            created_by=user
        )
        entity.save()
    elif form_method == constants.FORM_METHODS.UPDATE:
        entity = form_entity
        entity.name = metadata.get('name')
        entity.status = constants.ENTITY_STATUS.DRAFT
        entity.author = metadata.get('author')
        entity.definition = metadata.get('definition')
        entity.validation = metadata.get('validation')
        entity.implementation = metadata.get('implementation')
        entity.citation_requirements = metadata.get('citation_requirements')
        entity.tags = metadata.get('tags')
        entity.collections = metadata.get('collections')
        entity.publications = metadata.get('publications')
        entity.group = metadata.get('group')
        entity.group_access = metadata.get('group_access')
        entity.world_access = metadata.get('world_access')
        entity.template = template_instance
        entity.template_version = form_template.template_version
        entity.template_data = template_data
        entity.updated = make_aware(datetime.now())
        entity.updated_by = user
        entity.save()
    
    return entity.history.latest()
