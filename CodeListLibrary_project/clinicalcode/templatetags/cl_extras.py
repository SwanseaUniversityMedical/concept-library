from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.safestring import mark_safe
from django.conf.urls.static import static
from functools import partial
from re import IGNORECASE, compile, escape as rescape

import os
import re

from ..entity_utils.constants import TypeStatus

register = template.Library()

@register.simple_tag(takes_context=True)
def render_og_tags(context, *args, **kwargs):
    request = context['request']
    brand = request.BRAND_OBJECT

    title = None
    embed = None
    if not brand or not getattr(brand, 'site_title'):
        title = settings.APP_TITLE
        embed = settings.APP_EMBED_ICON.format(logo_path=settings.APP_LOGO_PATH)
    else:
        title = brand.site_title
        embed = settings.APP_EMBED_ICON.format(logo_path=brand.logo_path)

    desc = kwargs.pop('desc', settings.APP_DESC.format(app_title=title))
    title = kwargs.pop('title', title)
    embed = kwargs.pop('embed', embed)

    header = kwargs.pop('header', None)
    if isinstance(header, str):
        title = '{0} | {1}'.format(title, header)

    return mark_safe(
        '''
            <meta property="og:type" content="website">
            <meta property="og:url" content="{url}">
            <meta property="og:title" content="{title}">
            <meta property="og:description" content="{desc}">
            <meta property="og:image" content="{img_path}">

            <meta property="twitter:card" content="summary_large_image">
            <meta property="twitter:url" content="{url}">
            <meta property="twitter:title" content="{title}">
            <meta property="twitter:description" content="{desc}">
            <meta property="twitter:image" content="{img_path}">
        ''' \
        .format(
            url=request.build_absolute_uri(),
            desc=desc,
            title=title,
            img_path=os.path.join(settings.STATIC_URL, embed)
        )
    )

@register.filter(name='from_phenotype')
def from_phenotype(value, index, default=''):
    if index in value:
        return value[index]['concepts']
    return default

@register.filter(name='size')
def size(value):
    return len(value)

@register.filter(name='title')
def title(value):
    return str(value).title()

@register.filter
def cut(value, arg):
    """Removes all occurrences of arg from the given string"""
    return value.replace(arg, '')

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter
def islist(value):
    """Check if value is of type list"""
    return type(value) == list

@register.filter
def tolist(value, arg):
    """Convert comma separated value to a list of type arg"""

    if arg == "int":
        return [int(t) for t in value.split(',')]
    else:
        return [str(t) for t in value.split(',')]

@register.filter
def toString(value):
    """Convert value to string"""
    return str(value)

@register.filter
def addStr(value, arg):
    """concatenate value & arg"""
    return str(value) + str(arg)

@register.filter
def getBrandLogo(value):
    """get brand logos"""
    return f'/static/img/brands/{value}/apple-touch-icon.png'

@register.filter   
def highlight(text, q):
    q = q.lower()
    q = q.replace('"', '').replace(' -', ' ').replace(' - ', ' ')
    q = q.replace(' or ', ' ')

    q = re.sub(' +', ' ', q.strip())
    return_text = text
    for w in q.split(' '):
        if w.strip() == '':
            continue
        
        rw = r'\b{}\b'.format(rescape(w)) 
        rgx = compile(rw, IGNORECASE)
        
        #rgx = compile(rescape(w), IGNORECASE)
        return_text = rgx.sub(
                            lambda m: "<b stylexyz001>{}</b>".format(m.group()),
                            return_text
                        )

    return mark_safe(return_text.replace("stylexyz001", " class='hightlight-txt' "))
  
def highlight_all_search_text(text, q):
    # highlight all phrase as a unit
    q = q.strip()
    if q == '':
        return text
    
    rw = r'\b{}\b'.format(rescape(q)) 
    rgx = compile(rw, IGNORECASE)
        
    #rgx = compile(rescape(q), IGNORECASE)
    return mark_safe(
        rgx.sub(
            lambda m: '<b class="hightlight-txt">{}</b>'.format(m.group()),
            text
        )
    )  

@register.filter   
def get_ws_type_name(type_int):
    '''
        get working set type name
    '''
    
    return str([t[1] for t in TypeStatus.Type_status if t[0]==type_int][0])
    
@register.filter   
def get_title(txt, makeCapital=''):
    '''
        get title case
    '''
    txt = txt.replace('_', ' ')
    txt = txt.title()
    if makeCapital.strip() != '':
        txt = txt.replace(makeCapital.title(), makeCapital.upper())
    
    return txt
    
@register.filter   
def is_in_list(txt, list_values):
    '''
        check is value is in list
    '''
    return(txt in [i.strip() for i in list_values.split(',')])

@register.filter   
def concat_str(txt, txt2):
    '''
        concat 2 strings
    '''
    ret_str = ''
    if txt:
        ret_str = txt
        
    if txt2:
        ret_str += ' ' + txt2
        
    return ret_str

@register.filter   
def concat_doi(details, doi):
    '''
        concat publications details + doi
    '''
    ret_str = ''
    if details:
        ret_str = details
        
    if doi:
        ret_str += ' (DOI:' + doi + ')'
        
    return ret_str
