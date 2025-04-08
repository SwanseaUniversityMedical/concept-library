from copy import deepcopy
from django import template
from datetime import datetime
from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.db.models import Model
from django.utils.html import _json_script_escapes as json_script_escapes
from jinja2.exceptions import TemplateSyntaxError, FilterArgumentError
from django.http.request import HttpRequest
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

import re
import json
import inspect
import numbers
import warnings

from ..models.Brand import Brand
from ..entity_utils import (
  concept_utils, permission_utils, template_utils, search_utils,
  model_utils, create_utils, gen_utils, constants
)


register = template.Library()


@register.simple_tag
def sort_by_alpha(arr, column="name", order="desc"):
    """
        Sorts a `list` of objects by the defined column, and orders by asc/desc given its params; erroneous inputs are caught and ignored

        Args:
            arr    (list|any): an array of objects to sort
            column      (str): specify a column of the object to sort by; defaults to `name`
            order       (str): specify one of `asc` or `desc` to set the array sort order; defaults to `desc`

        Returns:
            The sorted (list) if applicable; returns the `arr` input argument if invalid
    """
    sorted_arr = None
    try:
        reverse = order == 'asc'
        sorted_arr = sorted(arr, key=lambda x: x[column], reverse=reverse)
    except:
        sorted_arr = arr
    return sorted_arr


@register.simple_tag(takes_context=True)
def get_brand_map_rules(context, brand=None, default=constants.DEFAULT_CONTENT_MAPPING):
    if brand is None:
        brand = model_utils.try_get_brand(context.get('request'))
    elif isinstance(brand, str) and not gen_utils.is_empty_string(brand):
        brand = model_utils.try_get_instance(Brand, name__iexact=brand)
    elif isinstance(brand, int) and brand >= 0:
        brand = model_utils.try_get_instance(Brand, pk=brand)
    elif not isinstance(brand, Brand) and (not inspect.isclass(brand) or not issubclass(brand, Brand)):
        brand = None

    if brand is None:
        return default

    return brand.get_map_rules(default=default)


@register.simple_tag(takes_context=True)
def fmt_brand_mapped_string(context, target, brand=None, default=None):
    brand = get_brand_map_rules(context, brand, default=None)
    if brand is None:
        if isinstance(default, str):
            return default
        brand = constants.DEFAULT_CONTENT_MAPPING if not isinstance(default, dict) else default
    return target.format(**brand)


@register.simple_tag(takes_context=True)
def get_brand_mapped_string(context, target, default=None, brand=None):
    if not isinstance(default, str):
        raise Exception('Failed to map string, expected a default value of type str, got %s' % type(default).__name__)

    if not isinstance(target, str):
        raise Exception('Expected mapping key as str, got %s' % type(target).__name__)

    brand = get_brand_map_rules(context, brand)
    return brand.get(target, default)


@register.simple_tag
def get_brand_base_icons(brand):
    """
        Gets the brand-related favicon & apple-touch-icons; defaults to base icons if not applicable for this brand

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (dict) with key-value pairs specifying the `favicon` and `apple` (`apple-touch-icon`) path
    """
    path = settings.APP_LOGO_PATH
    if brand and hasattr(brand, 'logo_path') and getattr(brand, 'logo_path', None):
        path = brand.logo_path if not gen_utils.is_empty_string(brand.logo_path) else path

    return {
        'favicon': path + 'favicon-32x32.png',
        'apple': path + 'apple-touch-icon.png',
    }


@register.simple_tag
def get_brand_base_title(brand):
    """
        Gets the brand-related site title if available, otherwise returns the `APP_TITLE` per `settings.py`

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the site title
    """
    if isinstance(brand, dict):
        title = brand.get('site_title', None)
    elif isinstance(brand, Model):
        title = getattr(brand, 'site_title', None) if hasattr(brand, 'site_title') else None
    else:
        title = None

    if title is None or gen_utils.is_empty_string(title):
        return settings.APP_TITLE
    return title


@register.simple_tag
def get_brand_base_desc(brand):
    """
        Gets the brand-related site description if available, otherwise returns the base embed description (see `APP_DESC` in `settings.py`)

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the site description
    """
    if isinstance(brand, dict):
        desc = brand.get('site_description', None)
    elif isinstance(brand, Model):
        desc = getattr(brand, 'site_description', None) if hasattr(brand, 'site_description') else None
    else:
        desc = None

    if desc is None or gen_utils.is_empty_string(desc):
        return settings.APP_DESC.format(app_title=settings.APP_TITLE)
    return desc


@register.simple_tag(takes_context=True)
def get_brand_base_website(context, brand=None):
    """
        Gets the brand-related site description if available, otherwise returns the base embed description (see `APP_DESC` in `settings.py`)

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the site description
    """
    request = context.get('request')
    if brand is None:
        brand = model_utils.try_get_brand(request)
    elif isinstance(brand, str) and not gen_utils.is_empty_string(brand):
        brand = model_utils.try_get_instance(Brand, name__iexact=brand)
    elif isinstance(brand, int) and brand >= 0:
        brand = model_utils.try_get_instance(Brand, pk=brand)
    elif not isinstance(brand, dict) and not isinstance(brand, Brand) and (not inspect.isclass(brand) or not issubclass(brand, Brand)):
        brand = None

    if isinstance(brand, dict):
        url = brand.get('website', None)
    elif isinstance(brand, Model):
        url = getattr(brand, 'website', None) if hasattr(brand, 'website') else None
    else:
        url = None

    if url is not None and not gen_utils.is_empty_string(url):
        return url

    if brand is not None:
        return f'/{brand.name}'
    return request.build_absolute_uri()


@register.simple_tag(takes_context=True)
def get_brand_citation_req(context, brand=None):
    """
        Gets the brand-related citation requirement if available, otherwise returns the base embed description (see `APP_CITATION` in `settings.py`)

        Args:
            context        (RequestContext): the page's request context (auto-prepended)
            brand (Request|Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the site citation requirement message
    """
    request = context.get('request')
    if brand is None:
        brand = model_utils.try_get_brand(request)
    elif isinstance(brand, str) and not gen_utils.is_empty_string(brand):
        brand = model_utils.try_get_instance(Brand, name__iexact=brand)
    elif isinstance(brand, int) and brand >= 0:
        brand = model_utils.try_get_instance(Brand, pk=brand)
    elif not isinstance(brand, Brand) and (not inspect.isclass(brand) or not issubclass(brand, Brand)):
        brand = None

    if brand is not None:
        map_rules = brand.get_map_rules()
        citation = map_rules.get('citation')
        website = map_rules.get('website')
    else:
        map_rules = constants.DEFAULT_CONTENT_MAPPING
        citation = None
        website = map_rules.get('website')

    has_valid_website = isinstance(website, str) and not gen_utils.is_empty_string(website)
    if isinstance(brand, dict):
        title = brand.get('site_title', None)
        website = brand.get('website', None) if not has_valid_website else website
    elif isinstance(brand, Model):
        title = getattr(brand, 'site_title', None) if hasattr(brand, 'site_title') else None
        website = getattr(brand, 'website', None) if not has_valid_website and hasattr(brand, 'website') else website
    else:
        title = None
        website = website if has_valid_website else None

    if title is None or gen_utils.is_empty_string(title):
        title = settings.APP_TITLE

    if website is None or gen_utils.is_empty_string(website):
        website = request.build_absolute_uri()

    if not isinstance(citation, str) or gen_utils.is_empty_string(citation):
        citation = settings.APP_CITATION

    return citation.format(
        **map_rules,
        app_title=title,
        brand_name=brand.name if brand else 'SAIL',
        brand_website=website
    )


@register.simple_tag
def get_brand_base_embed_desc(brand):
    """
        Gets the brand-related embedding desc if available, otherwise returns the `APP_DESC` per `settings.py` (OG tags)

        Note:
            - Interpolated by the `Brand`'s `site_title` attribute

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the embed description
    """
    if isinstance(brand, dict):
        title = brand.get('site_title', None)
    elif isinstance(brand, Model):
        title = getattr(brand, 'site_title', None) if hasattr(brand, 'site_title') else None
    else:
        title = None

    if title is None or gen_utils.is_empty_string(title):
        return settings.APP_DESC.format(app_title=settings.APP_TITLE)
    return settings.APP_DESC.format(app_title=title)


@register.simple_tag
def get_brand_base_embed_img(brand):
    """
        Gets the brand-related site open-graph embed image if applicable, otherwise returns the `APP_EMBED_ICON` per `settings.py`

        Args:
            brand (Brand|dict|None): the brand from which to resolve the info

        Returns:
            A (str) specifying the site embed icon
    """
    if isinstance(brand, dict):
        path = brand.get('logo_path', None)
    elif isinstance(brand, Model):
        path = getattr(brand, 'logo_path', None) if hasattr(brand, 'logo_path') else None
    else:
        path = None

    if path is None or gen_utils.is_empty_string(path):
        return settings.APP_EMBED_ICON.format(logo_path=settings.APP_LOGO_PATH)
    return settings.APP_EMBED_ICON.format(logo_path=path)


@register.simple_tag
def get_template_entity_name(entity_class, template=None):
    tmpl_def = None
    if isinstance(template, Model) or inspect.isclass(template) and issubclass(template, Model):
        tmpl_def = template.definition.get('template_details') if isinstance(template.definition, dict) else None
    elif isinstance(template, dict):
        tmpl_def = template.get('definition').get('template_details') if isinstance(template.get('definition'), dict) else None

    if isinstance(tmpl_def, dict):
        shortname = tmpl_def.get('shortname')
    else:
        shortname = None

    if isinstance(shortname, str) and not gen_utils.is_empty_string(shortname):
        return shortname
    return entity_class.name

@register.simple_tag
def render_citation_block(entity, request):
    """
        Computes an example citation block for the given entity entity

        Args:
            entity   (GenericEntity): some `GenericEntity` instance
            request (RequestContext): the HTTP request context assoc. with this render

        Returns:
            A (str) specifying the citation block content
    """
    phenotype_id = f'{entity.id} / {entity.history_id}'
    name = entity.name
    author = entity.author
    updated = entity.updated.strftime('%d %B %Y')
    date = datetime.now().strftime('%d %B %Y')
    url = request.build_absolute_uri(reverse(
        'entity_history_detail', 
        kwargs={ 'pk': entity.id, 'history_id': entity.history_id }
    ))

    brand = request.BRAND_OBJECT
    brand = None if not isinstance(brand, Brand) else brand
    site_name = settings.APP_TITLE if not brand or not getattr(brand, 'site_title') else brand.site_title

    return f'{author}. *{phenotype_id} - {name}*. {site_name} [Online]. {updated}. Available from: [{url}]({url}). [Accessed {date}]'


@register.inclusion_tag('components/search/pagination/pagination.html', takes_context=True, name='render_entity_pagination')
def render_pagination(context):
    """
        Renders pagination button(s) for search pages

        Note:
            - Provides page range so that it always includes the first and last page;
            - And if available, provides the page numbers 1 page to the left and the right of the current page.

        Args:
            context (Context|dict): specify the rendering context assoc. with this component; see `TemplateContext`_

        Returns:
            A (dict) specifying the pagination options
    
        .. _TemplateContext: https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context
    """
    page_obj = context.get('page_obj', None)
    if page_obj is None:
        return {
            'page': 1,
            'page_range': [1],
            'has_previous': False,
            'has_next': False,
        }

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
            user (RequestContext.user()): the user model
            args                (string): a string, can be deliminated by ',' to confirm membership in multiple groups
        
        Returns:
            A (bool) that reflects membership status
    """
    if args is None:
        return False
    
    args = [arg.strip() for arg in args.split(',')]
    for arg in args:
        if permission_utils.is_member(user, arg):
            return True
    return False


@register.filter(name='jsonify')
def jsonify(value, remove_userdata=True, should_print=False):
    """
        Attempts to dump a value to JSON

        Args:
            value              (*): some JSONifiable-value, _e.g._ some `Model` instance, a `dict`, or `list`
            remove_userdata (bool): optionally specify whether to remove userdata assoc. with some `Model` input instance; defaults to `True`
            should_print    (bool): optionally specify whether to print-debug the value before dumping it; defaults to `False`

        Returns:
            A (str) specifying the citation block content
    """
    if should_print:
        print(type(value), value)

    if value is None:
        value = { }

    if isinstance(value, (dict, list)):
        return json.dumps(value, cls=gen_utils.ModelEncoder)
    return model_utils.jsonify_object(value, remove_userdata=remove_userdata)


@register.filter(name='shrink_underscore')
def shrink_underscore(value):
    """
        Replaces the whitespace of strings with an underscore, and performs a lower case transform

        Args:
            value (str): the `str` value to transform

        Returns:
            The transformed (str) value if applicable; otherwise returns an empty `str`
    """
    return re.sub(r'\s+', '_', value).lower() if isinstance(value, str) else ''


@register.filter(name='stylise_number')
def stylise_number(value):
    """
        Stylises (transforms) a number such that it contains a comma delimiter for numbers greater than 1000, _e.g._ `1,000`, or `1,000,000` _etc_

        Args:
            value (numbers.Number|str): the number or representation of a number to stylise

        Returns:
            The stylised (str) value if applicable; otherwise returns an empty `str`
    """
    if isinstance(value, str):
        try:
            test = float(value)
        except ValueError:
            value = ''
        else:
            value = int(test) if test.is_integer() else test

    if isinstance(value, numbers.Number):
        value = '{:,}'.format(value)

    return value if isinstance(value, str) else ''


@register.filter(name='stylise_date')
def stylise_date(value):
    """
        Stylises a datetime object in the `YY-MM-DD` format

        Args:
            value (datetime): the date to format

        Returns:
            The stylised (str) value if applicable; otherwise returns an empty `str`
    """
    return value.strftime('%Y-%m-%d') if isinstance(value, datetime) else ''


@register.simple_tag(name='truncate')
def truncate(value, lim=10, ending=None):
    """
        Truncates a string if its length is greater than the limit; can append an ending, _e.g._ an ellipsis, by passing the 'ending' parameter

        Args:
            value     (str|*): some value to truncate; note that this value is coerced into a `str` before being truncated
            lim         (int): optionally specify the max length of the `str`; defaults to `10`
            ending (str|None): optionally specify a suffix to append to the resulting `str`; defaults to `None`

        Returns:
            The truncated (str) if applicable; otherwise returns an empty `str`
    """
    lim = lim if isinstance(lim, numbers.Number) else 0
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
def render_field_value(entity, layout, field, through=None, default=''):
    """
        Responsible for rendering fields after transforming them using their respective layouts, such that:
            - In the case of `type` (in this case, phenotype clinical types) where `pk__eq=1` would be "_Disease or Syndrome_" instead of returning the `pk`, it would return the field's string representation from either (a) its source or (b) the options parameter;

            - In the case of `coding_system`, it would read each individual element within the `ArrayField`, and return a rendered output based on the `desired_output` parameter ***OR*** it would render output based on the `through` parameter, which points to a component to be rendered.

        Args:
            entity (GenericEntity): some entity from which to resolve the field value
            layout          (dict): the entity's template data
            field            (str): the name of the field to resolve
            through     (str|None): optionally specify the through field target, if applicable; defaults to `None`
            default          (Any): optionally specify the default value; defaults to an empty (str) `''`

        Returns:
            The renderable (str) value resolved from this entity's field value 
    """
    data = template_utils.get_entity_field(entity, field)
    info = template_utils.get_layout_field(layout, field)
    if not info or not data:
        return default
    
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default
    
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
                    return default
                else:
                    # Use desired output
                    return default

    return default


@register.simple_tag(name='renderable_field_values')
def renderable_field_values(entity, layout, field):
    """
        Gets the field's value from an entity, compares it with it's expected layout (per the template), and returns
        a list of values that relate to that field;  _e.g._ in the case of CodingSystems it would return `[{name: 'ICD-10', value: 1}]` where `value` is the PK

        Args:
            entity (GenericEntity): some entity from which to resolve the field value
            layout          (dict): the entity's template data
            field            (str): the name of the field to resolve

        Returns:
            The resolved (Any)-typed value from the entity's field
    """
    info = template_utils.get_template_field_info(layout, field)
    if info.get('is_metadata'):
        # handle metadata e.g. collections, tags etc
        return template_utils.get_metadata_value_from_source(entity, field, field_info=info, layout=layout, default=[])
    
    return template_utils.get_template_data_values(entity, layout, field, default=[])


@register.tag(name="to_json_script")
def render_jsonified_object(parser, token):
    """
        Attempts to dump a value to JSON and render it as a HTML element in the form of:

        ```html
        <script type="application/json" other-attributes="some-value">
            ...
        </script>
        ```

        Example:
            
        ```html
        {% url 'some_url_var' as some_variable %}
        {% test_jsonify some_jsonifiable_content some-attribute="some_value" other-attribute=some_variable %}
        ```

        Args:
            parser (template.Parser): the Django template tag parser (supplied by renderer)
            token   (template.Token): the processed Django template token (supplied by HTML renderer)

        Kwargs:
            should_print    (bool): optionally specify whether to print-debug the value before dumping it; defaults to `False`
            remove_userdata (bool): optionally specify whether to remove userdata assoc. with some `Model` input instance; defaults to `True`
            attributes  (**kwargs): optionally specify a set of attributes to be applied to the rendered `<script />` node

        Returns:
            A (JsonifiedNode), a subclass of `template.Node`, to be rendered by Django's template renderer
    """
    kwargs = {
        'should_print': False,
        'remove_userdata': False,
    }

    content = None
    attributes = {}
    try:
        parsed = token.split_contents()[1:]
        if len(parsed) > 0 and parsed[0] == 'with':
            parsed = parsed[1:]

        for param in parsed:
            ctx = param.split('=')
            if len(ctx) > 1:
                if ctx[0] in kwargs:
                    value = eval(ctx[1])
                    if type(value) is not type(kwargs[ctx[0]]):
                        raise FilterArgumentError('[to_json_script] Expected %s as %s but got %s' % (ctx[0], type(kwargs[ctx[0]]), type(value),))
                    kwargs[ctx[0]] = value
                else:
                    attributes[ctx[0]] = parser.compile_filter(ctx[1])
            else:
                content = parser.compile_filter(ctx[0])
    except FilterArgumentError as e:
        raise e
    except Exception as e:
        raise TemplateSyntaxError('[to_json_script] Failed to parse tokens: %s' % (str(e),))

    return JsonifiedNode(content, attributes, **kwargs)


class JsonifiedNode(template.Node):
    """Renders the JSON node given the parameters called from `render_jsonified_object`"""
    def __init__(self, content, attributes, **kwargs):
        # opts
        self.should_print = kwargs.pop('should_print', False)
        self.remove_userdata = kwargs.pop('remove_userdata', False)

        # props
        self.content = content
        self.attributes = attributes

    def render(self, context):
        """Inherited method to render the nodes"""
        content = self.content.resolve(context)

        if self.should_print:
            print('[to_json_script] %s -> %s' % (type(content), repr(content),))

        if content is None:
            content = { }

        attributes = [ f'{key}={value.resolve(context)}' for key, value in self.attributes.items() ]

        attribute_string = ''
        if isinstance(attributes, list) and len(attributes) > 0:
            attribute_string = ' %s' % (' '.join(attributes),)

        content_string = None
        if isinstance(content, str):
            content_string = content
        elif isinstance(content, (dict, list)):
            content_string = json.dumps(content, cls=gen_utils.ModelEncoder)
        else:
            content_string = model_utils.jsonify_object(content, remove_userdata=self.remove_userdata)

        content_string = mark_safe(content_string.translate(json_script_escapes))
        return mark_safe(f'<script type="application/json"{attribute_string}>{content_string}</script>')


@register.tag(name='render_entity_cards')
def render_entities(parser, token):
    """
        Responsible for rendering the entity cards on a search page
            - Uses the entity's template to determine how to render the card (_e.g._ which to use);
            - Each card is rendered with its own context pertaining to that entity.

        Note:
            - This tag uses the `TemplateContext`_ to render the cards

        Example:
        ```html
        {% render_entity_cards %}
        {% endrender_entity_cards %}
        ```

        Args:
            parser (template.Parser): the Django template tag parser (supplied by renderer)
            token   (template.Token): the processed Django template token (supplied by HTML renderer)

        Returns:
            A (EntityCardsNode), a subclass of `template.Node`, to be rendered by Django's template renderer

        .. _TemplateContext: https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context
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
    """Renders the cards associated with an entity on the search page"""
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def render(self, context):
        """Inherited method to render the nodes"""
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
            output += render_to_string(card, { 'entity': entity, 'layout': layout })
        return output


@register.tag(name='render_entity_filters')
def render_filters(parser, token):
    """
        Responsible for rendering filters for entities on the search pages

        Note:
            - This tag uses the `TemplateContext`_ to render the filters

        Example:
        ```html
        {% render_entity_filters %}
        {% endrender_entity_filters %}
        ```

        Args:
            parser (template.Parser): the Django template tag parser (supplied by renderer)
            token   (template.Token): the processed Django template token (supplied by HTML renderer)

        Returns:
            A (EntityFiltersNode), a subclass of `template.Node`, to be rendered by Django's template renderer

        .. _TemplateContext: https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context
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
    """Renders the filters on the search page"""
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_compile_reference(self, context, field, structure):
        """Attempts to compile the reference data for a metadata field"""
        if field == 'template':
            layouts = context.get('layouts', None)
            modifier = {
                'entity_class__id__in': [layout['id'] for key, layout in layouts.items()]
            }
        else:
            modifier = None

        return search_utils.get_source_references(structure, default=[], modifier=modifier, request=self.request)
    
    def __check_excluded_brand_collections(self, context, field, current_brand, options):
        """Checks and removes Collections excluded from filters"""
        updated_options = options
        if field == 'collections':
            if current_brand == '' or current_brand == 'ALL':
                return updated_options

            brand = Brand.objects.all().filter(name__iexact=current_brand)
            brand = brand.first() if brand.exists() else None
            if not brand:
                return updated_options

            collections_excluded_from_filters = brand.collections_excluded_from_filters
            if isinstance(collections_excluded_from_filters, list):
                updated_options = [o for o in options if 'pk' in o and o.get('pk') not in collections_excluded_from_filters]

        return updated_options

    def __render_metadata_component(self, context, field, structure):
        """Renders a metadata field, as defined by constants.py"""
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''

        options = None
        if 'compute_statistics' in structure:
            current_brand = self.request.CURRENT_BRAND or 'ALL'
            options = search_utils.get_metadata_stats_by_field(field, brand=current_brand)
            # options = self.__check_excluded_brand_collections(context, field, current_brand, options)

        if options is None:
            validation = template_utils.try_get_content(structure, 'validation')
            if validation is not None:
                if 'source' in validation:
                    options = self.__try_compile_reference(context, field, structure)
                
        filter_info['options'] = options
        context['filter_info'] = filter_info
        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __render_template_component(self, context, field, structure, layout):
        """Renders a component for a template field after computing its reference data as defined by its validation & field type"""
        filter_info = search_utils.get_filter_info(field, structure)
        if not filter_info:
            return ''
    
        component = template_utils.try_get_content(constants.FILTER_COMPONENTS, filter_info.get('type'))
        if component is None:
            return ''
        
        current_brand = self.request.CURRENT_BRAND or 'ALL'
        statistics = search_utils.try_get_template_statistics(filter_info.get('field'), brand=current_brand)
        if statistics is None or len(statistics) < 1:
            return ''
        
        context['filter_info'] = {
            **filter_info,
            'options': statistics
        }

        return render_to_string(f'{constants.FILTER_DIRECTORY}/{component}.html', context.flatten())

    def __generate_metadata_filters(self, context, is_single_search=False):
        """Generates the filters for all metadata fields within a template"""
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
        """Generates a filter for each field of a template"""
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
        """Inherited method to render the nodes"""
        if isinstance(self.request, template.Variable):
            self.request = self.request.resolve(context)

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
        Responsible for rendering the `<aside/>` navigation item for create pages & detail pages

        Example:
        ```html
        {% render_wizard_navigation %}
        {% endrender_wizard_navigation %}
        ```

        Args:
            parser (template.Parser): the Django template tag parser (supplied by renderer)
            token   (template.Token): the processed Django template token (supplied by HTML renderer)

        Kwargs:
            detail_pg (bool): optionally specify whether to render this aside menu for the detail page; defaults to `False`

        Returns:
            A (EntityWizardAside), a subclass of `template.Node`, to be rendered by Django's template renderer
    """
    params = { 'detail_pg': False }
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
    """Responsible for rendering the aside component of the steps wizard"""
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist

    def __render_detail(self, context, template):
        request = self.request.resolve(context)

        # We should be getting the FieldTypes.json related to the template
        detail_page_sections = []
        template_sections = template.definition.get('sections')
        template_sections.extend(constants.DETAIL_PAGE_APPENDED_SECTIONS)
        for section in template_sections:
            if section.get('hide_on_detail', False):
                continue

            if section.get('requires_auth', False) and not request.user.is_authenticated:
                continue

            if section.get('do_not_show_in_production', False) and (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                continue

            detail_page_sections.append(section)

            # still need to handle: section 'hide_if_empty' ??? 

        output = render_to_string(constants.DETAIL_WIZARD_ASIDE, {
            'detail_page_sections': detail_page_sections
        })

        return output

    def __render_create(self, context, template):
        sections = template.definition.get('sections')
        if sections is None:
            return ''

        final_sections = [section for section in sections if not section.get('hide_on_create')]
        final_sections.extend(constants.APPENDED_SECTIONS)

        output = render_to_string(constants.CREATE_WIZARD_ASIDE, {
            'create_sections': final_sections
        })

        return output
    
    def render(self, context):
        """Inherited method to render the nodes"""
        template = context.get('template', None)
        if template is None:
            return ''

        is_detail_pg = self.params.get('detail_pg', False)
        if is_detail_pg:
            return self.__render_detail(context, template)

        return self.__render_create(context, template)


@register.tag(name='render_wizard_sections')
def render_steps_wizard(parser, token):
    """
        Responsible for rendering the `<li/>` sections for create & detail pages

        Example:
        ```html
        {% render_wizard_sections %}
        {% endrender_wizard_sections %}
        ```

        Args:
            parser (template.Parser): the Django template tag parser (supplied by renderer)
            token   (template.Token): the processed Django template token (supplied by HTML renderer)

        Kwargs:
            detail_pg (bool): optionally specify whether to render this component for the detail page; defaults to `False`

        Returns:
            A subclass of (template.Node) to be rendered by Django's template renderer, representing either a (EntityCreateWizardSections) or a (EntityDetailWizardSections)
    """
    params = { 'detail_pg': False }

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

    if params.get('detail_pg', False):
        return EntityDetailWizardSections(params, nodelist)
    return EntityCreateWizardSections(params, nodelist)


class EntityCreateWizardSections(template.Node):
    """Responsible for rendering the sections associated with the create steps wizard"""
    SECTION_END = render_to_string(template_name=constants.CREATE_WIZARD_SECTION_END)

    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_get_entity_value(self, request, template, entity, field, info=None):
        """Attempts to safely generate the creation data for field within a template"""
        value = create_utils.get_template_creation_data(request, entity, template, field, default=None, info=info)

        if value is None:
            return template_utils.get_entity_field(entity, field)

        return value

    def __try_render_item(self, **kwargs):
        """Attempts to safely render the HTML to string and sinks exceptions"""
        try:
            html = render_to_string(**kwargs)
        except Exception as e:
            if settings.DEBUG:
                warnings.warn(str(e))
            return ''
        else:
            return html
    
    def __try_get_props(self, template, field, struct=None):
        """Attempts to safely get the properties of a validation field, if present"""
        if struct is None:
            struct = template_utils.get_layout_field(template, field)

        if not isinstance(struct, dict):
            return
        
        validation = struct.get('validation')
        if not validation:
            return
        return validation.get('properties')
    
    def __try_get_computed(self, request, field, struct=None):
        """Attempts to safely parse computed fields"""
        if struct is None:
            struct = template_utils.get_layout_field(constants.metadata, field)

        if struct is None:
            return

        validation = template_utils.try_get_content(struct, 'validation')
        if validation is None:
            return
        
        if not validation.get('computed'):
            return
        
        # append other computed fields if required
        if field == 'organisation':
            return permission_utils.get_user_organisations(request)
        return

    def __apply_properties(self, component, template, _field):
        """
            Applies properties assoc. with some template's field to some target

            Returns:
                Updates in place but returns the updated (dict)
        """
        validation = template_utils.try_get_content(template, 'validation')
        if validation is not None:
            mandatory = template_utils.try_get_content(validation, 'mandatory')
            component['mandatory'] = mandatory if isinstance(mandatory, bool) else False

        return component

    def __append_section(self, output, section_content):
        """Appends the given section to the current output target"""
        if gen_utils.is_empty_string(section_content):
            return output
        return output + section_content + self.SECTION_END

    def __generate_wizard(self, request, context):
        """Generates the creation wizard template"""
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
                field_info = template_utils.get_template_field_info(template, field)
                template_field = field_info.get('field')
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

                component = deepcopy(component)
                component['field_name'] = field
                component['field_data'] = template_field
                
                desc = template_utils.try_get_content(template_field, 'description')
                if desc is not None:
                    component['description'] = desc
                    component['hide_input_details'] = False
                else:
                    component['hide_input_details'] = True

                is_metadata = field_info.get('is_metadata')
                will_hydrate = template_field.get('hydrated', False)

                options = None
                if not will_hydrate:
                    if is_metadata:
                        options = template_utils.get_template_sourced_values(constants.metadata, field, request=request, struct=template_field)

                        if options is None:
                            options = self.__try_get_computed(request, field, struct=template_field)
                    else:
                        options = template_utils.get_template_sourced_values(template, field, request=request, struct=template_field)

                if options is not None:
                    component['options'] = options

                field_properties = self.__try_get_props(template, field, struct=template_field)
                if field_properties is not None:
                    component['properties'] = field_properties

                if entity:
                    component['value'] = self.__try_get_entity_value(request, template, entity, field, info=field_info)
                else:
                    component['value'] = ''

                self.__apply_properties(component, template_field, field)

                uri = f'{constants.CREATE_WIZARD_INPUT_DIR}/{component.get("input_type")}.html'
                section_content += self.__try_render_item(template_name=uri, request=request, context=context.flatten() | { 'component': component })
            output = self.__append_section(output, section_content)

        return output
    
    def render(self, context):
        """Inherited method to render the nodes"""
        request = self.request.resolve(context)
        return self.__generate_wizard(request, context)


## NOTE:
##  - Need to ask M.E. to document the following at some point
##

def get_data_sources(ds_ids, info, default=None):
    """Tries to get the sourced value of data_sources id/name/url"""
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        if ds_ids:
            queryset = model.objects.filter(id__in=ds_ids)
            if queryset.exists():
                return queryset
    except:
        return default
    else:
        return default


def get_template_creation_data(entity, layout, field, request=None, default=None, info=None):
    """Used to retrieve assoc. data values for specific keys, e.g. concepts, in its expanded format for use with create/update pages"""
    if info is None:
        info = template_utils.get_template_field_info(layout, field)

    data = template_utils.get_entity_field(entity, field)
    if not info or not data:
        return default

    field_info = info.get('field')
    validation = template_utils.try_get_content(field_info, 'validation')
    if validation is None:
        return default

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default

    if field_type == 'concept':
        return concept_utils.get_concept_headers(data)
    elif field_type == 'int_array':
        source_info = validation.get('source')
        tree_models = source_info.get('trees') if isinstance(source_info, dict) else None
        model_source = source_info.get('model')
        if isinstance(tree_models, list) and isinstance(model_source, str):
            try:
                model = apps.get_model(app_label='clinicalcode', model_name=model_source)
                output = model.get_detail_data(node_ids=data, default=default)
                if isinstance(output, list):
                    return output
            except:
                # Logging
                return default

    if field_info.get('field_type') == 'data_sources':
        return get_data_sources(data, field_info, default=default)

    if info.get('is_metadata'):
        return template_utils.get_metadata_value_from_source(entity, field, field_info=info, layout=layout, default=default)

    return template_utils.get_template_data_values(entity, layout, field, default=default)


class EntityDetailWizardSections(template.Node):
    """Renders the detail page template sections"""
    SECTION_END = render_to_string(template_name=constants.DETAIL_WIZARD_SECTION_END)

    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist

    def __try_get_entity_value(self, template, entity, field, info=None):
        value = get_template_creation_data(entity, template, field, request=self.request, default=None, info=info)
        if value is None:
            return template_utils.get_entity_field(entity, field)

        return value

    def __try_render_item(self, **kwargs):
        try:
            html = render_to_string(**kwargs)
        except:
            return ''
        else:
            return html

    def __append_section(self, output, section_content):
        if gen_utils.is_empty_string(section_content):
            return output
        return output + section_content + self.SECTION_END

    def __generate_wizard(self, request, context):
        output = ''
        template = context.get('template', None)
        entity = context.get('entity', None)
        if template is None:
            return output

        flat_ctx = context.flatten()
        is_prod_env = not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC
        is_unauthenticated = not request.user or request.user.is_anonymous

        merged_definition = template_utils.get_merged_definition(template, default={})
        template_fields = template_utils.try_get_content(merged_definition, 'fields')
        template_fields.update(constants.DETAIL_PAGE_APPENDED_FIELDS)
        template.definition['fields'] = template_fields

        # We should be getting the FieldTypes.json related to the template
        field_types = constants.FIELD_TYPES
        template_sections = template.definition.get('sections')
        #template_sections.extend(constants.DETAIL_PAGE_APPENDED_SECTIONS)
        for section in template_sections:
            is_hidden = (
                section.get('hide_on_detail', False)
                or section.get('hide_on_detail', False)
                or (section.get('requires_auth', False) and is_unauthenticated)
                or (section.get('do_not_show_in_production', False) and is_prod_env)
            )
            if is_hidden:
                continue

            section['hide_description'] = True
            section_content = self.__try_render_item(template_name=constants.DETAIL_WIZARD_SECTION_START
                                                     , request=request
                                                     , context=flat_ctx | {'section': section})

            field_count = 0
            for field in section.get('fields'):
                field_info = template_utils.get_template_field_info(template, field)
                template_field = field_info.get('field')
                if not template_field:
                    continue

                component = template_utils.try_get_content(field_types, template_field.get('field_type')) if template_field else None
                if component is None:
                    continue

                component = deepcopy(component)
                active = template_field.get('active', False)
                is_hidden = (
                    (isinstance(active, bool) and not active)
                    or template_field.get('hide_on_detail')
                    or (template_field.get('requires_auth', False) and is_unauthenticated)
                    or (template_field.get('do_not_show_in_production', False) and is_prod_env)
                )
                if is_hidden:
                    continue

                component['field_name'] = field
                component['field_data'] = '' if template_field is None else template_field

                desc = template_utils.try_get_content(template_field, 'description')
                if desc is not None:
                    component['description'] = desc
                    component['hide_input_details'] = False
                else:
                    component['hide_input_details'] = True

                # don't show field description in detail page
                component['hide_input_details'] = True

                component['hide_input_title'] = False
                if len(section.get('fields')) <= 1:
                    # don't show field title if it is the only field in the section
                    component['hide_input_title'] = True

                if entity:
                    component['value'] = self.__try_get_entity_value(template, entity, field, info=field_info)
                else:
                    component['value'] = ''

                if 'sort' in component['field_data'] and component['value'] is not None:
                    component['value'] = sorted(component['value'], **component['field_data']['sort'])

                if template_field.get('hide_if_empty', False):
                    comp_value = component.get('value')
                    if comp_value is None or str(comp_value) == '' or comp_value == [] or comp_value == {}:
                        continue

                output_type = component.get("output_type")
                uri = f'{constants.DETAIL_WIZARD_OUTPUT_DIR}/{output_type}.html'
                field_count += 1
                section_content += self.__try_render_item(template_name=uri, request=request,
                                                          context=flat_ctx | {'component': component})

            if field_count > 0:
                output = self.__append_section(output, section_content)

        return output

    def render(self, context):
        """Inherited method to render the nodes"""
        if not isinstance(self.request, HttpRequest):
            self.request = self.request.resolve(context)

        return self.__generate_wizard(self.request, context)
