from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

import os

from ..entity_utils import gen_utils
from ..entity_utils.constants import TypeStatus


register = template.Library()


@register.simple_tag(takes_context=True)
def render_og_tags(context, *args, **kwargs):
    request = context['request']
    brand = request.BRAND_OBJECT

    title = None
    embed = None
    if brand is None or ((isinstance(brand, dict) and not brand.get('id')) or not getattr(brand, 'site_title')):
        title = settings.APP_TITLE
        embed = settings.APP_EMBED_ICON.format(logo_path=settings.APP_LOGO_PATH)
    else:
        title = brand.get('site_title') if isinstance(brand, dict) else brand.site_title
        lpath = brand.get('logo_path') if isinstance(brand, dict) else brand.logo_path
        if lpath is None or gen_utils.is_empty_string(lpath):
            lpath = settings.APP_LOGO_PATH

        embed = settings.APP_EMBED_ICON.format(logo_path=lpath)

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

@register.filter
def get_type(value):
    """Resolves the type of the specified value"""
    return type(value).__name__

@register.filter(name='from_phenotype')
def from_phenotype(value, index, default=''):
    if index in value:
        return value[index]['concepts']
    return default

@register.filter(name='is_empty_value')
def is_empty_value(value):
    if value is None:
        return True
    elif isinstance(value, str):
        return gen_utils.is_empty_string(value)
    return False

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
def is_list(value):
    """Check if value is of type list"""
    return isinstance(value, list)

@register.filter
def to_list(value, arg):
    """Convert comma separated value to a list of type arg"""
    if arg == "int":
        return [int(t) for t in value.split(',')]
    return [str(t) for t in value.split(',')]

@register.filter
def to_string(value):
    """Convert value to string"""
    return str(value)

@register.filter
def add_str(value, arg):
    """concatenate value & arg"""
    return str(value) + str(arg)

@register.filter
def get_brand_logo(value):
    """get brand logos"""
    return f'/static/img/brands/{value}/apple-touch-icon.png'

@register.filter   
def get_ws_type_name(type_int):
    """get working set type name"""
    return str([t[1] for t in TypeStatus.Type_status if t[0]==type_int][0])
    
@register.filter   
def get_title(txt, makeCapital=''):
    """
        get title case
    """
    txt = txt.replace('_', ' ')
    txt = txt.title()
    if makeCapital.strip() != '':
        txt = txt.replace(makeCapital.title(), makeCapital.upper())
    return txt
    
@register.filter   
def is_in_list(txt, list_values):
    """check is value is in list"""
    return (txt in [i.strip() for i in list_values.split(',')])

@register.filter   
def concat_str(txt0, txt1):
    """Safely concatenate the given string(s)"""
    if txt0 is not None and txt1 is not None:
        return '%s %s' % (str(txt0), str(txt1),) 
    elif txt0 is not None:
        return str(txt0)
    elif txt1 is not None:
        return str(txt1)
    return ''

@register.filter   
def concat_doi(details, doi):
    """concat publications details + doi"""
    details = str(details)
    if doi is None or (isinstance(doi, str) and (len(doi.strip()) < 1 or doi.isspace())):
        return details

    return '%s (DOI: %s)' % (details, str(doi))
