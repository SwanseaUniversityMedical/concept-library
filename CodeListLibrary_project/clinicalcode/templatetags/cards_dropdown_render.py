from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.inclusion_tag('components/navigation/dropdown_list_item.html', takes_context=True, name='card_render')
def render_card(context,url_drop, *args, **kwargs):
    card_context = {"title": "", "description": "", "icon": "about_icon"}
    
    card_context["title"] = context['lnk'].get('title','')
    card_context["description"] = context['lnk'].get('description','')
    card_context["icon"] = context['lnk'].get('svg','')
    card_context["url"] = url_drop 
    if isinstance(context['lnk'].get('page_name',''),list):
        card_context["list_pages"] = context['lnk'].get('page_name','')
        
    return card_context
