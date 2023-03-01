from django import template
from django.conf import settings
from jinja2.exceptions import TemplateSyntaxError
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.inclusion_tag('renderables/entity_details.html', takes_context=True, name='render_entity_details')
def render_details(context, *args, **kwargs):
    request = context['request']
    # Do stuff with the context e.g. the JSON passed from template/entity
    print(args, kwargs)

    # Do stuff with any args/kwargs e.g. change the context before passing to ./components/results.html
    should_say_hello = kwargs.get('sayHello', False)
    return {'hello': True} if should_say_hello else { }

@register.inclusion_tag('renderables/entity_cards.html', takes_context=True, name='render_entity_cards')
def render_entities(context, *args, **kwargs):
    request = context['request']
    return { }