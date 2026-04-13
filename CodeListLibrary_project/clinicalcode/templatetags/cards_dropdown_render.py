from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.inclusion_tag('components/navigation/dropdown_list_item.html', takes_context=True, name='card_render')
def render_card(context, url_drop, *args, **kwargs):
    lnk = context.get('lnk', {})
    ctx = {
        'title': lnk.get('title', ''),
        'description': lnk.get('description', ''),
        'icon': lnk.get('svg',''),
        'url': url_drop,
    }

    pages = lnk.get('page_name')
    if isinstance(pages, list):
        ctx |= { 'list_pages': pages }

    return ctx
