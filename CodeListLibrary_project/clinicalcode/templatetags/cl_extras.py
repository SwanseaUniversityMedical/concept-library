import bleach
import markdown
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from re import IGNORECASE, compile, escape as rescape
import re 
from clinicalcode.constants import Type_status
from clinicalcode.entity_utils import entity_db_utils


register = template.Library()


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
def markdownify00(text):
    # safe mode is deprecated, see: https://pythonhosted.org/Markdown/reference.html#safe_mode
    untrusted_text = markdown.markdown(text)  #, safe_mode='escape'
    html = bleach.clean(
        untrusted_text,
        tags=settings.MARKDOWNIFY["default"]["WHITELIST_TAGS"],
        attributes=settings.MARKDOWNIFY["default"]["WHITELIST_ATTRS"],
    )
    html = bleach.linkify(html)
    return html


###############################################################
import warnings
from functools import partial


def legacy():
    """
    Function used to transform old style settings to new style settings
    """

    # Bleach settings
    whitelist_tags = getattr(settings, 'MARKDOWNIFY_WHITELIST_TAGS', bleach.sanitizer.ALLOWED_TAGS)
    whitelist_attrs = getattr(settings, 'MARKDOWNIFY_WHITELIST_ATTRS', bleach.sanitizer.ALLOWED_ATTRIBUTES)
    whitelist_styles = getattr(settings, 'MARKDOWNIFY_WHITELIST_STYLES', bleach.sanitizer.ALLOWED_STYLES)
    whitelist_protocols = getattr(settings, 'MARKDOWNIFY_WHITELIST_PROTOCOLS', bleach.sanitizer.ALLOWED_PROTOCOLS)

    # Markdown settings
    strip = getattr(settings, 'MARKDOWNIFY_STRIP', True)
    extensions = getattr(settings, 'MARKDOWNIFY_MARKDOWN_EXTENSIONS', [])

    # Bleach Linkify
    values = {}
    linkify_text = getattr(settings, 'MARKDOWNIFY_LINKIFY_TEXT', True)

    if linkify_text:
        values = {
            "PARSE_URLS": True,
            "PARSE_EMAIL": getattr(settings, 'MARKDOWNIFY_LINKIFY_PARSE_EMAIL', False),
            "CALLBACKS": getattr(settings, 'MARKDOWNIFY_LINKIFY_CALLBACKS', None),
            "SKIP_TAGS": getattr(settings, 'MARKDOWNIFY_LINKIFY_SKIP_TAGS', None)
        }

    return {
        "STRIP": strip,
        "MARKDOWN_EXTENSIONS": extensions,
        "WHITELIST_TAGS": whitelist_tags,
        "WHITELIST_ATTRS": whitelist_attrs,
        "WHITELIST_STYLES": whitelist_styles,
        "WHITELIST_PROTOCOLS": whitelist_protocols,
        "LINKIFY_TEXT": values,
        "BLEACH": getattr(settings, 'MARKDOWNIFY_BLEACH', True)
    }


@register.filter
def markdownify(text, custom_settings="default"):

    # Check for legacy settings
    setting_keys = [
        'WHITELIST_TAGS',
        'WHITELIST_ATTRS',
        'WHITELIST_STYLES',
        'WHITELIST_PROTOCOLS',
        'STRIP',
        'MARKDOWN_EXTENSIONS',
        'LINKIFY_TEXT',
        'BLEACH',
    ]
    has_settings_old_style = False
    for key in setting_keys:
        #        if getattr(settings, f"MARKDOWNIFY_{key}", None):
        if getattr(settings, "MARKDOWNIFY_" + key, None):
            has_settings_old_style = True
            break

    if has_settings_old_style:
        markdownify_settings = legacy()
    else:
        try:
            markdownify_settings = settings.MARKDOWNIFY[custom_settings]
        except (AttributeError, KeyError):
            markdownify_settings = {}

    # Bleach settings
    whitelist_tags = markdownify_settings.get('WHITELIST_TAGS', bleach.sanitizer.ALLOWED_TAGS)
    whitelist_attrs = markdownify_settings.get('WHITELIST_ATTRS', bleach.sanitizer.ALLOWED_ATTRIBUTES)
    whitelist_styles = markdownify_settings.get('WHITELIST_STYLES', bleach.sanitizer.ALLOWED_STYLES)
    whitelist_protocols = markdownify_settings.get('WHITELIST_PROTOCOLS', bleach.sanitizer.ALLOWED_PROTOCOLS)

    # Markdown settings
    strip = markdownify_settings.get('STRIP', True)
    extensions = markdownify_settings.get('MARKDOWN_EXTENSIONS', [])

    # Bleach Linkify
    linkify = None
    linkify_text = markdownify_settings.get('LINKIFY_TEXT', {"PARSE_URLS": True})
    if linkify_text.get("PARSE_URLS"):
        linkify_parse_email = linkify_text.get('PARSE_EMAIL', False)
        linkify_callbacks = linkify_text.get('CALLBACKS', [])
        linkify_skip_tags = linkify_text.get('SKIP_TAGS', [])
        linkifyfilter = bleach.linkifier.LinkifyFilter

        linkify = [
            partial(linkifyfilter,
                    callbacks=linkify_callbacks,
                    skip_tags=linkify_skip_tags,
                    parse_email=linkify_parse_email)
        ]

    # Convert markdown to html
    html = markdown.markdown(text or "", extensions=extensions)

    # Sanitize html if wanted
    if markdownify_settings.get("BLEACH", True):
        cleaner = bleach.Cleaner(
            tags=whitelist_tags,
            attributes=whitelist_attrs,
            styles=whitelist_styles,
            protocols=whitelist_protocols,
            strip=strip,
            filters=linkify,
        )

        html = cleaner.clean(html)

    # this weird step is to reverse the effect of code tag although it is blacklisted 
    html = html.replace('&lt;','<').replace('&gt;', '>')
    
    return mark_safe(html)




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
    
    return str([t[1] for t in Type_status if t[0]==type_int][0])
    
    
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
def can_be_shown(field_data, is_authenticated):
    '''
        check is the field can be shown
    '''
    return entity_db_utils.can_field_be_shown(field_data, is_authenticated)



@register.filter   
def get_html_element(field_data):
    '''
        get suitable HTML element, like badge/cod, ..
    '''
    
    value = str(field_data['value'])
    if 'value_highlighted' in field_data:
        value = str(field_data['value_highlighted'])
        
    ret_html = value
    
    if 'apply_badge_style' in field_data['field_type_data'] and field_data['field_type_data']['apply_badge_style'] == True:
        ret_html = "<span class='badge entity-type-badge card-tag-sizing'><i><strong>" + value + "</i></strong></span>"
        
    if 'apply_code_style' in field_data['field_type_data'] and field_data['field_type_data']['apply_code_style'] == True:
        ret_html = "<code>" + value + "</code>"
   
    
    
    return ret_html


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




        