from django import template
from jinja2.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from ..entity_utils import template_utils, search_utils, constants
from ..models import Statistics
from django.conf import settings

register = template.Library()

@register.inclusion_tag('components/details/entity_details.html', takes_context=True, name='render_entity_details')
def render_details(context, *args, **kwargs):
    request = context['request']
    # Do stuff with the context e.g. the JSON passed from template/entity
    print(args, kwargs)

    # Do stuff with any args/kwargs e.g. change the context before passing to ./components/results.html
    should_say_hello = kwargs.get('sayHello', False)
    return {'hello': True} if should_say_hello else { }

@register.inclusion_tag('components/search/pagination.html', takes_context=True, name='render_entity_pagination')
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

@register.filter(name='get_entity_id')
def get_entity_id(entity, default=''):
    '''
        Returns an entity ID with its prefix e.g. PH1
    '''
    try:
        safe_id = f'{entity.entity_prefix}{entity.entity_id}'
    except:
        return default
    else:
        return safe_id

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
        
    if info['field_type'] == 'enum':
        output = template_utils.get_template_data_values(entity, layout, field, default=None)
        if output is not None and len(output) > 0:
            return template_utils.try_get_content(output[0], 'name')
    elif info['field_type'] == 'int_array':
        if 'source' in info:
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
            layout = template_utils.try_get_content(layouts, entity.entity_prefix)
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
                continue
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
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''

        if 'compute_statistics' in structure:
            filter_info['options'] = search_utils.get_metadata_stats_by_field(field)
        else:
            if 'source' in structure:
                filter_info['options'] = search_utils.get_source_references(structure)
        
        context['filter_info'] = filter_info
        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __render_template_component(self, context, field, structure, layout):
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''
        
        statistics = search_utils.try_get_template_statistics(layout, filter_info.get('field'))
        if statistics is None:
            return ''
        
        context['filter_info'] = {
            **filter_info,
            'options': statistics
        }

        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __generate_metadata_filters(self, context, is_single_search=False):
        request = self.request.resolve(context)

        output = ''
        for field, structure in constants.metadata.items():
            if 'filterable' in structure:
                if field != 'template' or is_single_search:
                    output += self.__render_metadata_component(context, field, structure)

        return output
    
    def __generate_template_filters(self, context, output, layouts):
        request = self.request.resolve(context)
        
        layout = next((x for x in layouts.values()), None)
        if not template_utils.is_layout_safe(layout):
            return output

        fields = template_utils.try_get_content(layout.get('definition'), 'fields')
        if not fields:
            return output
        
        
        template_fields = []
        
        order = template_utils.try_get_content(layouts, 'order')
        if order is not None:
            template_fields = [field for field in order if template_utils.try_get_content(fields.get(field), 'filterable')]
        else:
            template_fields = [field for field, structure in fields.items() if 'filterable' in structure]

        for field in template_fields:
            output += self.__render_template_component(context, field, fields[field], layout)

        return output

    def render(self, context):
        layouts = context.get('layouts', None)
        if layouts is None:
            return ''
        
        # When in dev env, 'Entity Type' filter will always be present
        is_single_search = settings.DEBUG or len(layouts.keys()) > constants.MIN_SINGLE_SEARCH

        # Render metadata
        output = self.__generate_metadata_filters(context, is_single_search)

        # Render template specific filters
        if not is_single_search or settings.DEBUG:
            output = self.__generate_template_filters(context, output, layouts)

        return output
