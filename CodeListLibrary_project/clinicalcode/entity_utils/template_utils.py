from operator import and_
from functools import reduce
from django.apps import apps
from django.db.models import Q, ForeignKey

import copy
import logging

from . import concept_utils
from . import filter_utils
from . import constants


logger = logging.getLogger(__name__)


def try_get_content(body, key, default=None):
    """
        Attempts to get content within a dict by a key, if it fails to do so, returns the default value
    """
    try:
        if key in body:
            return body[key]
        return default
    except:
        return default


def is_metadata(entity, field):
    """
        Checks whether a field is accounted for in the metadata of an entity e.g. name, tags, collections
    """
    metadata_field = constants.metadata.get(field)
    if metadata_field is not None and metadata_field.get('is_base_field'):
        return True

    try:
        data = entity._meta.get_field(field)
        return True
    except:
        pass

    try:
        model = type(entity)
        data = model._meta.get_field(field)
        return True
    except:
        return False


def is_layout_safe(layout):
    """
        Determines whether the definition of a layout is null
    """
    if layout is None:
        return False

    definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout, 'definition')
    return isinstance(definition, dict)


def try_get_layout(template, default=None):
    """
        Tries to get the definition from a template
    """
    if not is_layout_safe(template):
        return default
    return try_get_content(template, 'definition') if isinstance(template, dict) else getattr(template, 'definition')


def is_data_safe(entity):
    """
        Determines whether the template data of an entity instance is null
    """
    if entity is not None:
        data = getattr(entity, 'template_data')
        return isinstance(data, dict)


def get_layout_fields(layout, default=None):
    """
        Safely gets the fields from a layout
    """
    if is_layout_safe(layout):
        definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout,
                                                                                                    'definition')
        return try_get_content(definition, 'fields')
    return default


def get_layout_field(layout, field, default=None):
    """
        Safely gets a field from a layout's field within its definition
    """
    if is_layout_safe(layout):
        definition = try_get_content(layout, 'definition') if isinstance(layout, dict) else getattr(layout,
                                                                                                    'definition')
        fields = try_get_content(definition, 'fields')
        if fields is not None:
            return try_get_content(fields, field, default)

    return try_get_content(layout, field, default)


def get_template_field_info(layout, field_name, copy_field=True):
    """"""
    fields = get_layout_fields(layout)
    if fields:
        field = fields.get(field_name)
        if isinstance(field, dict):
            result = { 'key': field_name, 'field': field, 'is_metadata': False }
            if not field.get('is_base_field'):
                return result

            merged = copy.deepcopy(constants.metadata.get(field_name)) if copy_field else {}
            merged = merged | field

            result |= {
                'field': merged,
                'shunt': field.get('shunt') if isinstance(fields.get('shunt'), str) else None,
                'is_metadata': True,
            }

            return result

    field = constants.metadata.get(field_name, None)
    return { 'key': field_name, 'field': field, 'is_metadata': True }


def get_merged_definition(template, default=None):
    """
        Used to merge the metadata into a template such that interfaces, e.g. API/create,
        can understand the origin of fields
    """
    definition = try_get_content(template, 'definition') if isinstance(template, dict) else getattr(template,
                                                                                                    'definition')
    if definition is None:
        return default

    fields = {field: packet for field, packet in constants.metadata.items() if not packet.get('ignore')}
    for k, v in definition.get('fields', {}).items():
        fields.update({ k: fields.get(k, {}) | v })

    fields = {
            field: packet
            for field, packet in fields.items()
            if isinstance(packet, dict) and (not isinstance(packet.get('active'), bool) or packet.get('active'))
    }

    definition.update({'fields': fields})
    return definition


def get_ordered_definition(definition, clean_fields=False):
    """
        Safely gets the 'layout_order' field from the definition and tries
        to reorder the JSONB result so that iteration over fields are in the correct
        order
    """
    layout_order = try_get_content(definition, 'layout_order')
    if layout_order is None:
        return definition

    fields = try_get_content(definition, 'fields')
    if fields is None:
        return definition

    ordered_fields = {}
    for field in layout_order:
        content = try_get_content(fields, field)
        if clean_fields:
            content.pop('order', None)

        ordered_fields[field] = content

    definition['fields'] = ordered_fields

    if clean_fields:
        definition.pop('layout_order', None)

    return definition


def get_one_of_field(entity, entity_fields, default=None):
    """
        Attempts to get a field member of an entity given the fields to check,
        will return whichever is found first

        Args:
            entity (Model): the entity to examine
            entity_fields (list): a list of fields to select from

        Returns:
            Either (a) the default value if none are found, or (b) the value of the field that was selected
    """
    for field in entity_fields:
        value = None
        try:
            value = getattr(entity, field)
        except:
            pass

        if value:
            return value

    return default


def get_entity_field(entity, field, default=None):
    """
        Safely gets a field from an entity, either at the toplevel (e.g. its name) or from its template data (e.g. some dynamic field)
    """
    if not is_data_safe(entity):
        return default

    try:
        data = getattr(entity, field)
        if data is not None:
            return data
    except:
        pass

    try:
        data = getattr(entity, 'template_data')
        return try_get_content(data, field, default)
    except:
        pass

    return default


def try_get_children_field_names(template=None, fields=None, default=None):
    """
        Attempts to get the names of fields containing children that
        are associated with a template's definition

        Args:
            template (Model<Template> | dict | None): optional kwarg that describes the template 

            fields (dict | None): an optional template's field dict, as defined by get_layout_fields()

            default (any): the default return value on failure

        Returns:
            Either (a) a str[] array containing the associated fields,
            or (b) the default value if none are found
            
    """
    if template is not None and is_layout_safe(template):
        fields = get_layout_fields(template)

    if not isinstance(fields, dict):
        return default

    child_fields = None
    for field, packet in fields.items():
        validation = packet.get('validation')
        if validation is None:
            continue

        has_children = validation.get('has_children')
        if not has_children:
            continue

        if child_fields is None:
            child_fields = set([])

        child_fields.add(field)

    return list(child_fields) if child_fields is not None else default


def try_get_children_field_details(template=None, fields=None, default=None):
    """
        Attempts to get the details of fields containing children that
        are associated with a template's definition

        Args:
            template (Model<Template> | dict | None): optional kwarg that describes the template 

            fields (dict | None): an optional template's field dict, as defined by get_layout_fields()

            default (any): the default return value on failure

        Returns:
            Either (a) a dict[] array containing the associated fields and its details,
            or (b) the default value if none are found

    """
    if template is not None and is_layout_safe(template):
        fields = get_layout_fields(template)

    if not isinstance(fields, dict):
        return default

    child_fields = None
    for field, packet in fields.items():
        validation = packet.get('validation')
        if validation is None:
            continue

        has_children = validation.get('has_children')
        if not has_children:
            continue

        if child_fields is None:
            child_fields = []

        child_fields.append({
                'field': field,
                'type': validation.get('type')
        })

    return list(child_fields) if child_fields is not None else default


def is_valid_field(entity, field):
    """
        Checks to see if a field is a valid member of a template
    """
    if is_metadata(entity, field):
        return True

    try:
        template = entity.template
    except:
        return False
    else:
        if template is None:
            return False

    if get_layout_field(template, field):
        return True

    return False


def get_field_item(layout, field, item, default=None):
    """
        Gets a field item from a layout's field lookup
    """
    field_data = try_get_content(layout, field)
    if field_data is None:
        return default

    return try_get_content(field_data, item, default)


def try_get_instance_field(instance, field, default=None):
    """
        Safely gets a top-level metadata field
    """
    try:
        data = getattr(instance, field)
    except:
        return default
    else:
        return data


def is_filterable(layout, field):
    """
        Checks if a field is filterable as defined by its layout
    """
    search = get_field_item(layout, field, 'search')
    if search is None:
        return False

    return try_get_content(search, 'filterable')


def get_metadata_field_value(entity, field_name, default=None):
    """
        Tries to get the metadata field value of an entity after cleaning
        it by removing the stripped fields, historical fields and userdata information
        so that it can be safely presented to the client
    """
    field = entity._meta.get_field(field_name)
    if not field:
        return default

    field_type = field.get_internal_type()
    if field_type in constants.STRIPPED_FIELDS or field_type in constants.HISTORICAL_HIDDEN_FIELDS:
        return default

    field_value = get_entity_field(entity, field_name)
    if field_value is None:
        return default

    if isinstance(field, ForeignKey):
        model = field.target_field.model
        model_type = str(model)
        if model_type in constants.USERDATA_MODELS:
            return {
                    'id': field_value.id,
                    'name': get_one_of_field(field_value, ['username', 'name'])
            }

    return field_value


def try_get_filter_query(field_name, source, request=None):
    """
        @desc cleans the filter query provided by a template / metadata
              and applies the ENTITY_FILTER_PARAMS filter generator if available
              otherwise it will remove this key from the query
        
        Args:
            field_name (string): the name of the field
            source (dict): the field filter provided by a template and/or metadata

            request (RequestContext): the current request context, if available
        
        Returns:
            The final filter query as a (list)
    """
    output = []
    for key, value in source.items():
        filter_packet = constants.ENTITY_FILTER_PARAMS.get(key)
        if not isinstance(filter_packet, dict):
            output.append(Q(**{key: value}))
            continue

        filter_name = filter_packet.get('filter')
        if not isinstance(filter_name, str) or request is None:
            continue

        # Apply any filter specific props provided by constants and append the RequestContext
        filter_props = filter_packet.get('properties')
        filter_props = filter_props if isinstance(filter_props, dict) else {}
        filter_props = filter_props | {'request': request}

        # Apply field specific props
        field_props = filter_packet.get('field_properties')
        if field_props and isinstance(field_props.get(field_name), dict):
            filter_props = filter_props | field_props.get(field_name)

        # Try to generate the filter and update the query if successful
        result = None
        try:
            result = filter_utils.DataTypeFilters.try_generate_filter(
                desired_filter=filter_name,
                expected_params=filter_packet.get('expected_params'),
                source_value=value,
                **filter_props
            )
        except Exception as e:
            logger.warning(f'Failed to build filter of field "{field_name}" with err:\n\n{e}')

        if isinstance(result, list):
            output = output + result

    return output


def get_metadata_value_from_source(entity, field, field_info=None, layout=None, default=None, request=None):
    """
        [!] Note: RequestContext is an optional parameter that can be provided to further filter
            the results based on the request's Brand    
    
        Tries to get the values from a top-level metadata field
            - This method assumes it is sourced i.e. has a foreign key (has different names and/or filters)
            to another table
    """
    try:
        info = None
        if field_info is not None:
            info = field_info
        elif layout is not None:
            info = get_template_field_info(layout, field)

        if info:
            if not info.get('is_metadata'):
                return default
            else:
                info = info.get('field')

        if info is None:
            info = constants.metadata.get(field)

        if info is not None:
            data = get_entity_field(entity, field)
            validation = info.get('validation')
            if not validation:
                return default

            source_info = validation.get('source')
            if not source_info:
                return default

            model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))

            column = 'id'
            if 'query' in source_info:
                column = source_info['query']

            if isinstance(data, model):
                data = getattr(data, column)

            query = { f'{column}__in': data } if isinstance(data, list) else { f'{column}': data }

            if 'filter' in source_info:
                filter_query = try_get_filter_query(field, source_info.get('filter'), request=request)
                if isinstance(filter_query, list):
                    query = [Q(**query), *filter_query]

            if isinstance(query, list):
                queryset = model.objects.filter(reduce(and_, query))
            else:
                queryset = model.objects.filter(**query)

            if queryset.exists():
                relative = 'name'
                if 'relative' in source_info:
                    relative = source_info['relative']

                output = [
                    { 'name': getattr(instance, relative), 'value': getattr(instance, column) }
                    for instance in queryset
                ]

                return output if len(output) > 0 else default
    except Exception as e:
        logger.warning(f'Failed to build metadata value of field "{field}" with err:\n\n{e}')
    return default


def get_template_sourced_values(template, field, default=None, request=None, struct=None):
    """
        [!] Note: RequestContext is an optional parameter that can be provided to further filter
            the results based on the request's Brand    
        
        Returns the complete option list of an enum or a sourced field
    """
    if struct is None:
        struct = get_layout_field(template, field)

    if struct is None:
        return default

    validation = try_get_content(struct, 'validation')
    if validation is None:
        return default

    if 'options' in validation:
        output = []
        for i, v in validation.get('options').items():
            if isinstance(v, dict):
                ref = i
                val = v
            else:
                ref = v
                val = i

            output.append({
                'name': ref,
                'value': val,
            })

        return output
    elif 'source' in validation:
        source_info = validation.get('source')
        if not source_info:
            return default

        model_name = source_info.get('table')
        tree_models = source_info.get('trees')

        if isinstance(tree_models, list):
            model_source = source_info.get('model')
            if isinstance(model_source, str):
                try:
                    model = apps.get_model(app_label='clinicalcode', model_name=model_source)
                    output = model.get_groups(tree_models, default=default)
                    if isinstance(output, list):
                        return output
                except Exception as e:
                    logger.warning(f'Failed to derive template sourced values of tree, from field "{field}" with err:\n\n{e}')
        elif isinstance(model_name, str):
            try:
                model = apps.get_model(app_label='clinicalcode', model_name=model_name)

                column = 'id'
                if 'query' in source_info:
                    column = source_info.get('query')

                query = { }
                if 'filter' in source_info:
                    filter_query = try_get_filter_query(field, source_info.get('filter'), request=request)
                    if isinstance(filter_query, list):
                        query = [Q(**query), *filter_query]

                if isinstance(query, list):
                    queryset = model.objects.filter(reduce(and_, query))
                else:
                    queryset = model.objects.filter(**query)

                if queryset.exists():
                    relative = 'name'
                    if 'relative' in source_info:
                        relative = source_info.get('relative')

                    include = source_info.get('include')
                    if isinstance(include, list):
                        include = [x.strip() for x in include if isinstance(x, str) and len(x.strip()) > 0 and not x.strip().isspace()]
                        include = include if len(include) > 0 else None
                    else:
                        include = None

                    output = []
                    for instance in queryset:
                        item = {
                            'name': getattr(instance, relative),
                            'value': getattr(instance, column),
                        }

                        if include is not None:
                            item.update({ k: getattr(instance, k) for k in include if hasattr(instance, k) })
                        output.append(item)

                    return output if len(output) > 0 else default
            except Exception as e:
                logger.warning(f'Failed to derive template sourced values of column, from field "{field}" with err:\n\n{e}')

    return default


def get_detailed_options_value(data, info, default=None):
    """
        Tries to get the detailed options parameter from a layout's field entry
    """
    validation = try_get_content(info, 'validation')
    if validation is None:
        return False

    key = str(data)
    if key in validation['options']:
        return {'name': validation['options'][key], 'value': data}
    return default


def get_options_value(data, info, default=None):
    """
        Tries to get the options parameter from a layout's field entry
    """
    validation = try_get_content(info, 'validation')
    if validation is None:
        return False

    key = str(data)
    if key in validation['options']:
        return validation['options'][key]
    return default


def get_detailed_sourced_value(data, info, default=None):
    """
        Tries to get the detailed sourced value of a dynamic field from its layout and/or 
          another model (if sourced)
    """
    validation = try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        relative = None
        if 'relative' in source_info:
            relative = source_info['relative']

        query = { source_info['query']: data } if 'query' in source_info else { 'pk': data }
        queryset = model.objects.filter(Q(**query))
        if queryset.exists():
            queryset = queryset.first()

            packet = {
                'name': try_get_instance_field(queryset, relative, default),
                'value': data
            }

            included_fields = source_info.get('include')
            if included_fields:
                for included_field in included_fields:
                    value = try_get_instance_field(queryset, included_field, default)
                    if value is None:
                        continue
                    packet[included_field] = value

            return packet

        return default
    except Exception as e:
        field = info.get('title', 'Unknown Field')
        logger.warning(f'Failed to build detailed source value of field "{field}" with err:\n\n{e}')
    return default


def get_sourced_value(data, info, default=None, filter_params=None):
    """
        Tries to get the sourced value of a dynamic field from its layout and/or another model (if sourced)
    """
    validation = try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        relative = None
        if 'relative' in source_info:
            relative = source_info['relative']

        query = { source_info['query']: data } if 'query' in source_info else { 'pk': data }

        if 'filter' in source_info and isinstance(filter_params, dict):
            filter_query = None
            try:
                if 'source_value' not in filter_params:
                    filter_params.update({ 'source_value': source_info.get('filter') })

                filter_query = filter_utils.DataTypeFilters.try_generate_filter(**filter_params)
                if isinstance(filter_query, list):
                    query = [Q(**query), *filter_query]

            except Exception as e:
                field = info.get('title', 'Unknown Field')
                logger.warning(f'Failed to build filter of field "{field}" with err:\n\n{e}')

        if isinstance(query, list):
            queryset = model.objects.filter(reduce(and_, query))
        else:
            queryset = model.objects.filter(**query)

        if queryset.exists():
            queryset = queryset.first()
            return try_get_instance_field(queryset, relative, default)

        return default
    except Exception as e:
        field = info.get('title', 'Unknown Field')
        logger.warning(f'Failed to build sourced value of field "{field}" with err:\n\n{e}')

    return default


def get_template_data_values(entity, layout, field, hide_user_details=False, request=None, default=None):
    """
        Retrieves the sourced values from an entity in an array
    """
    data = get_entity_field(entity, field)
    info = get_layout_field(layout, field)
    if not info or not data:
        return default

    validation = try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = try_get_content(validation, 'type')
    if field_type is None:
        return default

    if field_type == 'enum' or field_type == 'int':
        output = None
        if 'options' in validation and not validation.get('ugc', False):
            output = get_detailed_options_value(data, info)
        elif 'source' in validation:
            output = get_detailed_sourced_value(data, info)
        if output is not None:
            return [output]
    elif field_type == 'int_array':
        source_info = validation.get('source')
        options = validation.get('options')
        if source_info:
            model_name = source_info.get('table')
            tree_models = source_info.get('trees')

            if isinstance(tree_models, list):
                model_source = source_info.get('model')
                if isinstance(model_source, str):
                    try:
                        model = apps.get_model(app_label='clinicalcode', model_name=model_source)
                        output = model.get_detailed_source_value(data, tree_models, default=default)
                        if isinstance(output, list):
                            return output
                    except Exception as e:
                        logger.warning(f'Failed to derive template data values of "{field}" with err:\n\n{e}')
            elif isinstance(model_name, str):
                values = []
                for item in data:
                    value = get_detailed_sourced_value(item, info)
                    if value is None:
                        continue

                    values.append(value)
                return values
        elif isinstance(options, dict) and isinstance(data, list):
            values = [{ 'name': options.get(x), 'value': x } for x in data if isinstance(options.get(x), str)]
            return values if len(values) > 0 else default
        else:
            return default
    elif field_type == 'concept':
        values = []
        for item in data:
            value = concept_utils.get_clinical_concept_data(
                    item['concept_id'],
                    item['concept_version_id'],
                    hide_user_details=hide_user_details,
                    derive_access_from=request
            )

            if value:
                values.append(value)

        return values

    return default


def is_single_search_only(template, field):
    """
        Checks if the single_search_only attribute is present in a given template's field
    """
    template = try_get_content(template, field)
    if template is None:
        return False

    search = get_field_item(template, field, 'search')
    if search is None:
        return False

    return try_get_content(search, 'single_search_only')
