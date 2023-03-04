from django import template
from django.conf import settings
from jinja2.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from ..entity_utils import view_utils

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
    request = context['request']
    return { }

'''
    Returns an entity ID with its prefix e.g. PH1
'''
@register.filter(name='get_entity_id')
def get_entity_id(entity, default=''):
    try:
        safe_id = f'{entity.entity_prefix}{entity.entity_id}'
    except:
        return default
    else:
        return safe_id

'''
    Stylises a number so that it adds a comma delimiter for numbers greater than 1000
'''
@register.filter(name='stylise_number')
def stylise_number(n):
    return '{:,}'.format(n)

'''
    Stylises a datetime object in the YY-MM-DD format
'''
@register.filter(name='stylise_date')
def stylise_date(date):
    return date.strftime('%Y-%m-%d')

'''
    Truncates a string if its length is greater than the limit
        - can append an ending, e.g. an ellipsis, by passing the 'ending' parameter
'''
@register.simple_tag(name='truncate')
def truncate(value, lim=0, ending=None):
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

'''
    Responsible for rendering fields after transforming them using their respective layouts
        - in the case of 'type' (in this case, phenotype clinical types) where pk__eq=1 would be 'Disease or Syndrome'
          instead of returning the pk, it would return the field's string representation from either (a) its source or (b) the options parameter
        
        - in the case of 'coding_system', it would read each individual element within the ArrayField, 
          and return a rendered output based on the 'desired_output' parameter
              OR
              it would render output based on the 'through' parameter, which points to a component to be rendered
'''
@register.simple_tag(name='render_field_value')
def render_field_value(entity, layout, field, through=None):
    data = view_utils.get_entity_field(entity, field)
    info = view_utils.get_layout_field(layout, field)

    if not info or not data:
        # Should we try to return data, or maybe some filler?
        return ''
    
    # Probably should be a in hashmap or class
    if info['field_type'] == 'enum':
        output = None
        if 'options' in info:
            output = view_utils.get_options_value(data, info)
        elif 'source' in info:
            output = view_utils.get_sourced_value(data, info)
        
        if output is not None:
            return output
    elif info['field_type'] == 'int_array':
        if 'source' in info:
            values = [ ]
            for item in data:
                value = view_utils.get_sourced_value(item, info)
                if value is not None:
                    values.append({
                        'name': value,
                        'value': data,
                    })

            if through is not None:
                # Use override template
                return ''
            else:
                # Use desired output
                return ''

    return ''

'''
    Gets the field's value from an entity, compares it with it's expected layout (per the template), and returns
    a list of values that relate to that field
        e.g. in the case of CodingSystems it would return [{name: 'ICD-10', value: 1}] where 'value' is the PK
'''
@register.simple_tag(name='renderable_field_values')
def renderable_field_values(entity, layout, field):
    if view_utils.is_metadata(entity, field):
        # handle metadata e.g. collections, tags etc
        return view_utils.get_metadata_value_from_source(entity, field, default=[])
    
    data = view_utils.get_entity_field(entity, field)
    info = view_utils.get_layout_field(layout, field)
    if not info or not data:
        return []
    
    if info['field_type'] == 'enum':
        output = None
        if 'options' in info:
            output = view_utils.get_options_value(data, info)
        elif 'source' in info:
            output = view_utils.get_sourced_value(data, info)
        
        if output is not None:
            return [{
                'name': output,
                'value': data
            }]
    elif info['field_type'] == 'int_array':
        if 'source' in info:
            values = [ ]
            for item in data:
                value = view_utils.get_sourced_value(item, info)
                if value is not None:
                    values.append({
                        'name': value,
                        'value': item,
                    })
            
            return values

    return []

'''
    Responsible for rendering the entity cards on a search page
        - Uses the entity's template to determine how to render the card (e.g. which to use)
        - Each card is rendered with its own context pertaining to that entity
'''
@register.tag(name='render_entity_cards')
def render_entities(parser, token):
    params = {
        # Any future params that modifies behaviour
    }

    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[2:]
        
        for param in parsed:
            ctx = param.split('=')
            params[ctx[0]] = eval(ctx[1])
    except ValueError:
        raise TemplateSyntaxError('Unable to parse entity cards renderer')

    nodelist = parser.parse(('endrender_entity_cards'))
    parser.delete_first_token()
    return EntityCardsNode(params, nodelist)

class EntityCardsNode(template.Node):
    DEFAULT_CARD = 'generic'
    CARDS_DIRECTORY = 'components/search/cards'

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
            layout = view_utils.try_get_content(layouts, entity.entity_prefix)
            if not view_utils.is_layout_safe(layout):
                continue
            
            card = view_utils.try_get_content(layout['definition'], 'card_type', self.DEFAULT_CARD)
            card = f'{self.CARDS_DIRECTORY}/{card}.html'

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