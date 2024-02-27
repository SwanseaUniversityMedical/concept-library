from django import template
from django.conf import settings
from jinja2.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

import re
import json
import warnings

from ..entity_utils import permission_utils, template_utils, search_utils, model_utils, create_utils, gen_utils, constants
from ..models.GenericEntity import GenericEntity
from ..models.Brand import Brand

register = template.Library()

@register.simple_tag
def sort_by_alpha(arr, column="name", order="desc"):
    """
        Sorts an array of objects by the defined column, and orders by
        asc/desc given its params
    """
    sorted_arr = None
    try:
        reverse = order == 'asc'
        sorted_arr = sorted(arr, key=lambda x: x[column], reverse=reverse)
    except:
        sorted_arr = arr
    return sorted_arr

@register.simple_tag
def get_brand_base_icons(brand):
    path = settings.APP_LOGO_PATH
    if brand and getattr(brand, 'logo_path'):
        path = brand.logo_path

    return {
        'favicon': path + 'favicon-32x32.png',
        'apple': path + 'apple-touch-icon.png',
    }

@register.simple_tag
def get_brand_base_title(brand):
    """
        Gets the brand-related site title if available, otherwise returns
        the APP_TITLE per settings.py
    """
    if not brand or not getattr(brand, 'site_title'):
        return settings.APP_TITLE
    return brand.site_title

@register.simple_tag
def get_brand_base_embed_desc(brand):
    """
        Gets the brand-related site desc if available, otherwise returns
        the APP_DESC per settings.py
    """
    if not brand or not getattr(brand, 'site_title'):
        return settings.APP_DESC.format(app_title=settings.APP_TITLE)
    return settings.APP_DESC.format(app_title=brand.site_title)

@register.simple_tag
def get_brand_base_embed_img(brand):
    """
        Gets the brand-related site desc if available, otherwise returns
        the APP_DESC per settings.py
    """
    if not brand or not getattr(brand, 'logo_path'):
        return settings.APP_EMBED_ICON.format(logo_path=settings.APP_LOGO_PATH)
    return settings.APP_EMBED_ICON.format(logo_path=brand.logo_path)

@register.inclusion_tag('components/search/pagination/pagination.html', takes_context=True, name='render_entity_pagination')
def render_pagination(context, *args, **kwargs):
    """
        Renders pagination button(s) for search pages
            - Provides page range so that it always includes the first and last page,
              and if available, provides the page numbers 1 page to the left and the right of the current page
    """
    page_obj = context['page_obj']

    page = page_obj.number
    num_pages = page_obj.paginator.num_pages

    packet = {
        'page': page,
        'page_range': [1, num_pages],
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
    }

    if num_pages <= 9:
        packet['pages'] = set(range(1, num_pages + 1))
        return packet

    page_items = []
    min_page = page - 1
    max_page = page + 1
    if min_page <= 1:
        min_page = 1
        max_page = min(page + 2, num_pages)
    else:
        page_items += [1, 'divider']

    if max_page > num_pages:
        min_page = max(page - 2, 1)
        max_page = min(page, num_pages)

    page_items += list(range(min_page, max_page + 1))
    if num_pages not in page_items:
        page_items += ['divider', num_pages]

    packet['pages'] = page_items
    return packet

@register.filter(name='is_member')
def is_member(user, args):
    """
        Det. whether has a group membership

        Args:
            user (RequestContext.user()) - the user model
            args (string) - a string, can be deliminated by ',' to confirm membership in multiple groups
        
        Returns:
            (boolean) that reflects membership status
    """
    if args is None:
        return False
    
    args = [arg.strip() for arg in args.split(',')]
    for arg in args:
        if permission_utils.is_member(user, arg):
            return True
    return False

@register.filter(name='jsonify')
def jsonify(value, should_print=False):
    '''
        Attempts to dump a value to JSON
    '''
    if should_print:
        print(type(value), value)
    
    if value is None:
        value = { }
    
    if isinstance(value, (dict, list)):
        return json.dumps(value, cls=gen_utils.ModelEncoder)
    return model_utils.jsonify_object(value)

@register.simple_tag
def parse_as_json_object(value, remove_userdata=True, should_print=False):
    '''
        Attempts to dump a value to JSON
    '''
    if should_print:
        print(type(value), value)
    
    if value is None:
        value = { }
    
    if isinstance(value, (dict, list)):
        return json.dumps(value, cls=gen_utils.ModelEncoder)
    return model_utils.jsonify_object(value, remove_userdata=remove_userdata)

@register.filter(name='trimmed')
def trimmed(value):
    return re.sub(r'\s+', '_', value).lower()

@register.filter(name='stylise_number')
def stylise_number(n):
    """
        Stylises a number so that it adds a comma delimiter for numbers greater than 1000
    """
    if n is not None:
        return '{:,}'.format(n)
    return ''

@register.filter(name='stylise_date')
def stylise_date(date):
    """
        Stylises a datetime object in the YY-MM-DD format
    """
    return date.strftime('%Y-%m-%d')

@register.simple_tag(name='truncate')
def truncate(value, lim=0, ending=None):
    """
        Truncates a string if its length is greater than the limit
            - can append an ending, e.g. an ellipsis, by passing the 'ending' parameter
    """
    if lim <= 0:
        return value

    try:
        truncated = str(value)
        if len(truncated) > lim:
            truncated = truncated[0:lim]
            if ending is not None:
                truncated = truncated + ending
    except:
        return value
    else:
        return truncated

@register.simple_tag(name='render_field_value')
def render_field_value(entity, layout, field, through=None):
    """
        Responsible for rendering fields after transforming them using their respective layouts
            - in the case of 'type' (in this case, phenotype clinical types) where pk__eq=1 would be 'Disease or Syndrome'
            instead of returning the pk, it would return the field's string representation from either (a) its source or (b) the options parameter
            
            - in the case of 'coding_system', it would read each individual element within the ArrayField, 
            and return a rendered output based on the 'desired_output' parameter
                OR
                it would render output based on the 'through' parameter, which points to a component to be rendered
    """
    data = template_utils.get_entity_field(entity, field)
    info = template_utils.get_layout_field(layout, field)

    if not info or not data:
        return ''
    
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return ''
    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return ''
    
    if field_type == 'enum' or field_type == 'int':
        output = template_utils.get_template_data_values(entity, layout, field, default=None)
        if output is not None and len(output) > 0:
            return template_utils.try_get_content(output[0], 'name')
    elif field_type == 'int_array':
        if 'source' in validation:
            values = template_utils.get_template_data_values(entity, layout, field, default=None)

            if values is not None:
                if through is not None:
                    # Use override template
                    return ''
                else:
                    # Use desired output
                    return ''

    return ''

@register.simple_tag(name='renderable_field_values')
def renderable_field_values(entity, layout, field):
    """
        Gets the field's value from an entity, compares it with it's expected layout (per the template), and returns
        a list of values that relate to that field
            e.g. in the case of CodingSystems it would return [{name: 'ICD-10', value: 1}] where 'value' is the PK
    """
    if template_utils.is_metadata(entity, field):
        # handle metadata e.g. collections, tags etc
        return template_utils.get_metadata_value_from_source(entity, field, default=[])
    
    return template_utils.get_template_data_values(entity, layout, field, default=[])

@register.tag(name='render_entity_cards')
def render_entities(parser, token):
    """
        Responsible for rendering the entity cards on a search page
            - Uses the entity's template to determine how to render the card (e.g. which to use)
            - Each card is rendered with its own context pertaining to that entity
    """
    params = {
        # Any future params that modifies behaviour
    }

    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[1:]
        
        for param in parsed:
            ctx = param.split('=')
            params[ctx[0]] = eval(ctx[1])
    except ValueError:
        raise TemplateSyntaxError('Unable to parse entity cards renderer')

    nodelist = parser.parse(('endrender_entity_cards'))
    parser.delete_first_token()
    return EntityCardsNode(params, nodelist)

class EntityCardsNode(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def render(self, context):
        request = self.request.resolve(context)
        entities = context['page_obj'].object_list
        layouts = context['layouts']

        output = ''
        for entity in entities:
            layout = template_utils.try_get_content(layouts, f'{entity.template.id}/{entity.template_version}')
            if not template_utils.is_layout_safe(layout):
                continue
            card = template_utils.try_get_content(layout['definition'].get('template_details'), 'card_type', constants.DEFAULT_CARD)
            card = f'{constants.CARDS_DIRECTORY}/{card}.html'
            try:
                html = render_to_string(card, {
                    'entity': entity,
                    'layout': layout
                })
            except:
                raise
            else:
                output += html
        return output

@register.tag(name='render_entity_filters')
def render_filters(parser, token):
    """
        Responsible for rendering filters for entities on the search pages
    """
    params = {
        # Any future modifiers
    }

    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[1:]
        
        for param in parsed:
            ctx = param.split('=')
            params[ctx[0]] = eval(ctx[1])
    except ValueError:
        raise TemplateSyntaxError('Unable to parse entity filters renderer')

    nodelist = parser.parse(('endrender_entity_filters'))
    parser.delete_first_token()
    return EntityFiltersNode(params, nodelist)

class EntityFiltersNode(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_compile_reference(self, context, field, structure):
        """
            Attempts to compile the reference data for a metadata field
        """
        if field == 'template':
            layouts = context.get('layouts', None)
            modifier = {
                'entity_class__id__in': [layout['id'] for key, layout in layouts.items()]
            }
        else:
            modifier = None

        return search_utils.get_source_references(structure, default=[], modifier=modifier)
    
    def __check_excluded_brand_collections(self, context, field, current_brand, options):
        """
            Checks and removes Collections excluded from filters
        """
        updated_options = options
        if field == 'collections':
            if current_brand !='' and current_brand != 'ALL':
                if Brand.objects.all().filter(name__iexact=current_brand).exists():
                    brand = Brand.objects.get(name__iexact=current_brand)
                    collections_excluded_from_filters = brand.collections_excluded_from_filters
                    if collections_excluded_from_filters:
                        updated_options = [o for o in options if o['pk'] not in collections_excluded_from_filters]
                        
        return updated_options   

    def __render_metadata_component(self, context, field, structure):
        """
            Renders a metadata field, as defined by constants.py
        """
        request = self.request.resolve(context)
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''

        options = None
        if 'compute_statistics' in structure:
            current_brand = request.CURRENT_BRAND or 'ALL'
            options = search_utils.get_metadata_stats_by_field(field, brand=current_brand)
            options = self.__check_excluded_brand_collections(context, field, current_brand, options)

        if options is None:
            validation = template_utils.try_get_content(structure, 'validation')
            if validation is not None:
                if 'source' in validation:
                    options = self.__try_compile_reference(context, field, structure)
                
        filter_info['options'] = options
        context['filter_info'] = filter_info
        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __render_template_component(self, context, field, structure, layout):
        """
            Renders a component for a template field after computing its reference data
            as defined by its validation & field type
        """
        request = self.request.resolve(context)
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''
        
        current_brand = request.CURRENT_BRAND or 'ALL'
        statistics = search_utils.try_get_template_statistics(filter_info.get('field'), brand=current_brand)
        if statistics is None or len(statistics) < 1:
            return ''
        
        context['filter_info'] = {
            **filter_info,
            'options': statistics
        }

        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __generate_metadata_filters(self, context, is_single_search=False):
        """
            Generates the filters for all metadata fields within a template
        """
        output = ''
        for field, structure in constants.metadata.items():
            search = template_utils.try_get_content(structure, 'search')
            if search is None:
                continue

            if 'filterable' not in search:
                continue
            
            output += self.__render_metadata_component(context, field, structure)

        return output
    
    def __generate_template_filters(self, context, output, layouts):
        """
            Generates a filter for each field of a template
        """
        layout = next((x for x in layouts.values()), None)
        if not template_utils.is_layout_safe(layout):
            return output

        fields = template_utils.try_get_content(layout.get('definition'), 'fields')
        if not fields:
            return output
        
        template_fields = []
        
        order = template_utils.try_get_content(layouts, 'order')
        if order is not None:
            template_fields = [field for field in order if template_utils.is_filterable(fields, field)]
        else:
            template_fields = [field for field, structure in fields.items() if template_utils.is_filterable(fields, field)]

        for field in template_fields:
            output += self.__render_template_component(context, field, fields.get(field), layout)

        return output

    def render(self, context):
        entity_type = context.get('entity_type', None)
        layouts = context.get('layouts', None)
        if layouts is None:
            return ''
        
        is_single_search = entity_type is None

        # Render metadata
        output = self.__generate_metadata_filters(context, is_single_search)

        # Render template specific filters
        if not is_single_search:
            output = self.__generate_template_filters(context, output, layouts)

        return output

@register.tag(name='render_wizard_navigation')
def render_aside_wizard(parser, token):
    """
        Responsible for rendering the <aside/> navigation item for create pages
    """
    params = {
        # Any future modifiers
    }

    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[1:]
        
        for param in parsed:
            ctx = param.split('=')
            params[ctx[0]] = eval(ctx[1])
    except ValueError:
        raise TemplateSyntaxError('Unable to parse wizard aside renderer tag')

    nodelist = parser.parse(('endrender_wizard_navigation'))
    parser.delete_first_token()
    return EntityWizardAside(params, nodelist)

class EntityWizardAside(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def render(self, context):
        output = ''
        template = context.get('template', None)
        if template is None:
            return output
        
        sections = template.definition.get('sections')
        if sections is None:
            return ''

        final_sections = [section for section in sections if not section.get('hide_on_create')]
        final_sections.extend(constants.APPENDED_SECTIONS)

        output = render_to_string(constants.CREATE_WIZARD_ASIDE, {
            'create_sections': final_sections
        })

        return output

@register.tag(name='render_wizard_sections')
def render_steps_wizard(parser, token):
    """
        Responsible for rendering the <li/> sections for create pages
    """
    params = {
        # Any future modifiers
    }

    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[1:]
        
        for param in parsed:
            ctx = param.split('=')
            params[ctx[0]] = eval(ctx[1])
    except ValueError:
        raise TemplateSyntaxError('Unable to parse wizard aside renderer tag')

    nodelist = parser.parse(('endrender_wizard_sections'))
    parser.delete_first_token()
    return EntityWizardSections(params, nodelist)

class EntityWizardSections(template.Node):
    SECTION_END = render_to_string(template_name=constants.CREATE_WIZARD_SECTION_END)

    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_get_entity_value(self, request, template, entity, field):
        """
            Attempts to safely generate the creation data for field within a template
        """
        value = create_utils.get_template_creation_data(request, entity, template, field, default=None)

        if value is None:
            return template_utils.get_entity_field(entity, field)

        return value

    def __try_render_item(self, **kwargs):
        """
            Attempts to safely render the HTML to string and sinks exceptions
        """
        try:
            html = render_to_string(**kwargs)
        except Exception as e:
            if settings.DEBUG:
                warnings.warn(str(e))
            return ''
        else:
            return html
    
    def __try_get_props(self, template, field):
        """
            Attempts to safely get the properties of a validation field, if present
        """
        struct = template_utils.get_layout_field(template, field)
        if not isinstance(struct, dict):
            return
        
        validation = struct.get('validation')
        if not validation:
            return
        return validation.get('properties')
    
    def __try_get_computed(self, request, field):
        """
            Attempts to safely parse computed fields
        """
        struct = template_utils.get_layout_field(constants.metadata, field)
        if struct is None:
            return

        validation = template_utils.try_get_content(struct, 'validation')
        if validation is None:
            return
        
        if not validation.get('computed'):
            return
        
        # append other computed fields if required
        if field == 'group':
            return permission_utils.get_user_groups(request)
        return

    def __apply_mandatory_property(self, template, field):
        """
            Returns boolean that reflects the mandatory status of a field given its
            template's validation field (if present)
        """
        validation = template_utils.try_get_content(template, 'validation')
        if validation is None:
            return False
        
        mandatory = template_utils.try_get_content(validation, 'mandatory')
        return mandatory if isinstance(mandatory, bool) else False

    def __append_section(self, output, section_content):
        if gen_utils.is_empty_string(section_content):
            return output
        return output + section_content + self.SECTION_END

    def __generate_wizard(self, request, context):
        """
            Generates the creation wizard template
        """
        output = ''
        template = context.get('template', None)
        entity = context.get('entity', None)
        if template is None:
            return output
        
        field_types = constants.FIELD_TYPES
        sections = template.definition.get('sections')
        if sections is None:
            return ''

        sections = [section for section in sections if not section.get('hide_on_create')]
        sections.extend(constants.APPENDED_SECTIONS)

        for section in sections:
            section_content = self.__try_render_item(template_name=constants.CREATE_WIZARD_SECTION_START, request=request, context=context.flatten() | { 'section': section })

            for field in section.get('fields'):
                if template_utils.is_metadata(GenericEntity, field):
                    template_field = constants.metadata.get(field)
                else:
                    template_field = template_utils.get_field_item(template.definition, 'fields', field)

                if not template_field:
                    continue

                active = template_field.get('active')
                if isinstance(active, bool) and not active:
                    continue
                
                if template_field.get('hide_on_create'):
                    continue
                
                component = template_utils.try_get_content(field_types, template_field.get('field_type'))                
                if component is None:
                    continue

                if template_utils.is_metadata(GenericEntity, field):
                    field_data = template_utils.try_get_content(constants.metadata, field)
                else:
                    field_data = template_utils.get_layout_field(template, field)
                
                if field_data is None:
                    continue
                component['field_name'] = field
                component['field_data'] = field_data
                
                desc = template_utils.try_get_content(template_field, 'description')
                if desc is not None:
                    component['description'] = desc
                    component['hide_input_details'] = False
                else:
                    component['hide_input_details'] = True
                
                if template_utils.is_metadata(GenericEntity, field):
                    options = template_utils.get_template_sourced_values(constants.metadata, field, request=request)

                    if options is None:
                        options = self.__try_get_computed(request, field)
                else:
                    options = template_utils.get_template_sourced_values(template, field, request=request)
                
                if options is not None:
                    component['options'] = options
                
                field_properties = self.__try_get_props(template, field)
                if field_properties is not None:
                    component['properties'] = field_properties
                
                if entity:
                    component['value'] = self.__try_get_entity_value(request, template, entity, field)
                else:
                    component['value'] = ''
                component['mandatory'] = self.__apply_mandatory_property(template_field, field)

                uri = f'{constants.CREATE_WIZARD_INPUT_DIR}/{component.get("input_type")}.html'
                section_content += self.__try_render_item(template_name=uri, request=request, context=context.flatten() | { 'component': component })
            output = self.__append_section(output, section_content)

        return output
    
    def render(self, context):
        """
            Renders the wizard
        """
        request = self.request.resolve(context)
        return self.__generate_wizard(request, context)
