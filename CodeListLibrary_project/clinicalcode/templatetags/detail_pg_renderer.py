from django.apps import apps
from django import template
from jinja2.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static
from django.conf import settings

import re
import json

from ..entity_utils import permission_utils, template_utils, search_utils, model_utils, create_utils, gen_utils, constants, concept_utils
from ..models.GenericEntity import GenericEntity

register = template.Library()

@register.inclusion_tag('components/search/pagination/pagination.html', takes_context=True, name='render_entity_pagination')
def render_pagination(context, *args, **kwargs):
    '''
        Renders pagination button(s) for search pages
            - Provides page range so that it always includes the first and last page,
              and if available, provides the page numbers 1 page to the left and the right of the current page
    '''
    request = context['request']
    page_obj = context['page_obj']

    page = page_obj.number
    num_pages = page_obj.paginator.num_pages
    page_items = []
    if num_pages <= 9:
        page_items = set(range(1, num_pages + 1))
    else:
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

    return {
        'page': page,
        'page_range': [1, num_pages],
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'pages': page_items
    }

@register.filter(name='is_member')
def is_member(user, args):
    '''
        Det. whether has a group membership

        Args:
            user {RequestContext.user()} - the user model
            args {string} - a string, can be deliminated by ',' to confirm membership in multiple groups
        
        Returns:
            {boolean} that reflects membership status
    '''
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

@register.filter(name='trimmed')
def trimmed(value):
    return re.sub(r'\s+', '_', value).lower()

@register.filter(name='stylise_number')
def stylise_number(n):
    '''
        Stylises a number so that it adds a comma delimiter for numbers greater than 1000
    '''
    return '{:,}'.format(n)

@register.filter(name='stylise_date')
def stylise_date(date):
    '''
        Stylises a datetime object in the YY-MM-DD format
    '''
    return date.strftime('%Y-%m-%d')

@register.simple_tag(name='truncate')
def truncate(value, lim=0, ending=None):
    '''
        Truncates a string if its length is greater than the limit
            - can append an ending, e.g. an ellipsis, by passing the 'ending' parameter
    '''
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
    '''
        Responsible for rendering fields after transforming them using their respective layouts
            - in the case of 'type' (in this case, phenotype clinical types) where pk__eq=1 would be 'Disease or Syndrome'
            instead of returning the pk, it would return the field's string representation from either (a) its source or (b) the options parameter
            
            - in the case of 'coding_system', it would read each individual element within the ArrayField, 
            and return a rendered output based on the 'desired_output' parameter
                OR
                it would render output based on the 'through' parameter, which points to a component to be rendered
    '''
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
    '''
        Gets the field's value from an entity, compares it with it's expected layout (per the template), and returns
        a list of values that relate to that field
            e.g. in the case of CodingSystems it would return [{name: 'ICD-10', value: 1}] where 'value' is the PK
    '''
    if template_utils.is_metadata(entity, field):
        # handle metadata e.g. collections, tags etc
        return template_utils.get_metadata_value_from_source(entity, field, default=[])
    
    return template_utils.get_template_data_values(entity, layout, field)

@register.tag(name='render_entity_cards')
def render_entities(parser, token):
    '''
        Responsible for rendering the entity cards on a search page
            - Uses the entity's template to determine how to render the card (e.g. which to use)
            - Each card is rendered with its own context pertaining to that entity
    '''
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
            layout = template_utils.try_get_content(layouts, f'{entity.template.id}/{entity.template_data.get("version")}')
            if not template_utils.is_layout_safe(layout):
                continue
            card = template_utils.try_get_content(layout['definition'], 'card_type', constants.DEFAULT_CARD)
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
    '''
        Responsible for rendering filters for entities on the search pages
    '''
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
    
    def __render_metadata_component(self, context, field, structure):
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
        else:
            validation = template_utils.try_get_content(structure, 'validation')
            if validation is not None:
                if 'source' in validation:
                    options = search_utils.get_source_references(structure)
                
        filter_info['options'] = options
        context['filter_info'] = filter_info
        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __render_template_component(self, context, field, structure, layout):
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

@register.tag(name='render_wizard_sidemenu')
def render_aside_wizard(parser, token):
    '''
        Responsible for rendering the <aside/> sidemenu item for detail pages
    '''
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

    nodelist = parser.parse(('endrender_wizard_sidemenu'))
    parser.delete_first_token()
    return EntityWizardAside(params, nodelist)

class EntityWizardAside(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def render(self, context):
        request = self.request.resolve(context)
        output = ''
        template = context.get('template', None)
        if template is None:
            return output

        # We should be getting the FieldTypes.json related to the template
        detail_page_sections = []
        for section in template.definition.get('detail_page_sections'):
            if section.get('requires_auth', False):
                if not request.user.is_authenticated:
                    #print('SECTION: requires_auth')
                    continue   
                
            if section.get('do_not_show_in_production', False):
                if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                    #print('SECTION: do_not_show_in_production')
                    continue  
            
            detail_page_sections.append(section)

            # still need to handle: section 'hide_if_empty' ??? 

        output = render_to_string(constants.DETAIL_WIZARD_ASIDE, {
            'detail_page_sections': detail_page_sections    # template.definition.get('detail_page_sections')
        })

        return output

@register.tag(name='render_wizard_sections_detail_pg')
def render_steps_wizard(parser, token):
    '''
        Responsible for rendering the <li/> sections for detail pages
    '''
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

    nodelist = parser.parse(('endrender_wizard_sections_detail_pg'))
    parser.delete_first_token()
    return EntityWizardSections(params, nodelist)

def get_data_sources(ds_ids, info, default=None):
    '''
        Tries to get the sourced value of data_sources id/name/url
    '''
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        # relative = None
        # if 'relative' in source_info:
        #     relative = source_info['relative']

        # query = None
        # if 'query' in source_info:
        #     query = {
        #         source_info['query']: data
        #     }
        # else:
        #     query = {
        #         'pk': data
        #     }

        if ds_ids:
            queryset = model.objects.filter(id__in = ds_ids)
            if queryset.exists():
                #queryset = model.objects.get(id__in = ds_ids)
                return queryset
        
        return default
    except:
        return default
    
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
            value = concept_utils.get_clinical_concept_data(
                item['concept_id'],
                item['concept_version_id'],
                include_component_codes=False, 
                include_attributes=True, 
                include_reviewed_codes=True)


            if value:
                values.append(value)
        
        return values
    
    if info.get('field_type') == 'data_sources':
        return get_data_sources(data, info, default=default)
    
    if template_utils.is_metadata(entity, field):
        return template_utils.get_metadata_value_from_source(entity, field, default=default)
    
    return template_utils.get_template_data_values(entity, layout, field, default=default)


class EntityWizardSections(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_get_entity_value(self, template, entity, field):
        value = get_template_creation_data(entity, template, field, default=None)
        #print('value===11======'+str(value))
        if value is None:
            #print('value===22======'+str(template_utils.get_entity_field(entity, field)))
            return template_utils.get_entity_field(entity, field)

        return value

    def __try_render_item(self, **kwargs):
        try:
            html = render_to_string(**kwargs)
        except:
            return ''
        else:
            return html
    
    def __try_get_computed(self, request, field):
        struct = template_utils.get_layout_field(constants.metadata, field)
        if struct is None:
            return

        validation = template_utils.try_get_content(struct, 'validation')
        if validation is None:
            return
        
        if not validation.get('computed'):
            return
        
        if field == 'group':
            return permission_utils.get_user_groups(request)

    def __generate_wizard(self, request, context):
        output = ''
        template = context.get('template', None)
        entity = context.get('entity', None)
        if template is None:
            return output

        
        # We should be getting the FieldTypes.json related to the template
        field_types = constants.FIELD_TYPES
        for section in template.definition.get('detail_page_sections'):
            if section.get('requires_auth', False):
                #if not request.user.is_authenticated:
                if not context.get('user').is_authenticated:
                    #print('SECTION: requires_auth22')
                    continue   
                
            if section.get('do_not_show_in_production', False):
                if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                    #print('SECTION: do_not_show_in_production')
                    continue    
                    
            # still need to handle: section 'hide_if_empty' ??? 
        
            output += self.__try_render_item(template_name=constants.DETAIL_WIZARD_SECTION_START
                                             , request=request
                                             , context=context.flatten() | { 'section': section })

            for field in section.get('fields'):
                #print('field==== '+str(field))
                template_field = template_utils.get_field_item(template.definition, 'fields', field)
                #print('template_field-temp='+ str(template_field) )
                if not template_field:
                    template_field = template_utils.try_get_content(constants.metadata, field)
                    #print('template_field-base='+ str(template_field) )

                if not template_field:
                    #print('not template_field')
                    continue
                
                if template_field.get('is_base_field', False):
                    template_field = constants.metadata.get(field) | template_field

                component = template_utils.try_get_content(field_types, template_field.get('field_type'))                
                if component is None:
                    #print('component is None')
                    continue

                if template_utils.is_metadata(GenericEntity, field):
                    field_data = template_utils.try_get_content(constants.metadata, field)
                else:
                    field_data = template_utils.get_layout_field(template, field)

                #print('field_data===****==='+str(field_data))
                

                if template_field.get('requires_auth', False):
                    if not request.user.is_authenticated:
                        #print('requires_auth')
                        continue    

                if not template_field.get('active', False):
                    #print('NOT active')
                    continue       

                if template_field.get('do_not_show_in_production', False):
                    if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                        #print('do_not_show_in_production')
                        continue                                                  

                if field_data is None:
                    #print('field_data is None ==>> str()')
                    field_data = ''
                    #continue


                component['field_name'] = field
                component['field_data'] = field_data

                desc = template_utils.try_get_content(template_field, 'description')
                if desc is not None:
                    component['description'] = desc
                    component['hide_input_details'] = False
                else:
                    component['hide_input_details'] = True
                
                # don't show description in detail page
                component['hide_input_details'] = True
                
                if template_utils.is_metadata(GenericEntity, field):
                    options = template_utils.get_template_sourced_values(constants.metadata, field)

                    if options is None:
                        options = self.__try_get_computed(request, field)
                else:
                    options = template_utils.get_template_sourced_values(template, field)
                
                if options is not None:
                    component['options'] = options

                if entity:
                    component['value'] = self.__try_get_entity_value(template, entity, field)
                else:
                    component['value'] = ''
                    
                if template_field.get('hide_if_empty', False):
                    if component['value'] is None or str(component['value']) == '':
                        #print('hide_if_empty')
                        continue    
                                    

                output_type = component.get("output_type")
                uri = f'{constants.DETAIL_WIZARD_OUTPUT_DIR}/{output_type}.html'
                output += self.__try_render_item(template_name=uri, request=request, context=context.flatten() | { 'component': component })

        output += render_to_string(template_name=constants.DETAIL_WIZARD_SECTION_END, request=request, context=context.flatten() | { 'section': section })
        return output
    
    def render(self, context):
        request = self.request.resolve(context)
        return self.__generate_wizard(request, context)

