from django import template
from django.conf import settings
from jinja2.exceptions import TemplateSyntaxError
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.inclusion_tag('components/details/entity_details.html', takes_context=True, name='render_entity_details')
def render_details(context, *args, **kwargs):
    request = context['request']
    # Do stuff with the context e.g. the JSON passed from template/entity
    print(args, kwargs)

    # Do stuff with any args/kwargs e.g. change the context before passing to ./components/results.html
    should_say_hello = kwargs.get('sayHello', False)
    return {'hello': True} if should_say_hello else { }

@register.inclusion_tag('components/search/cards/clinical.html', takes_context=False, name='render_entity_card')
def render_entity(*args, **kwargs):
    return { }

@register.inclusion_tag('components/search/pagination.html', takes_context=True, name='render_entity_pagination')
def render_pagination(context, *args, **kwargs):
    request = context['request']
    return { }
