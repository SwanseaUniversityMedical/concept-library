from django.apps import apps
from django import template
from jinja2.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.http.request import HttpRequest
from django.conf import settings

import re
import json

from ..entity_utils import permission_utils, template_utils, model_utils, gen_utils, constants, concept_utils
from ..models.GenericEntity import GenericEntity

register = template.Library()

@register.filter(name='is_member')
def is_member(user, args):
    '''
        Det. whether has a group membership

        Args:
            user {RequestContext.user()} - the user model
            args {string} - a string, can be deliminated by ',' to confirm membership in multiple groups
        
        Returns:
            {boolean} that reflects membership status
    '''
    if args is None:
        return False
    
    args = [arg.strip() for arg in args.split(',')]
    for arg in args:
        if permission_utils.is_member(user, arg):
            return True
    return False

@register.filter(name='jsonify')
def jsonify(value, should_print=False):
    '''
        Attempts to dump a value to JSON
    '''
    if should_print:
        print(type(value), value)
    
    if value is None:
        value = { }
    
    if isinstance(value, (dict, list)):
        return json.dumps(value, cls=gen_utils.ModelEncoder)
    return model_utils.jsonify_object(value)

@register.filter(name='trimmed')
def trimmed(value):
    return re.sub(r'\s+', '_', value).lower()

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


@register.tag(name='render_wizard_sidemenu')
def render_aside_wizard(parser, token):
    '''
        Responsible for rendering the <aside/> sidemenu item for detail pages
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
        raise TemplateSyntaxError('Unable to parse wizard aside renderer tag')

    nodelist = parser.parse(('endrender_wizard_sidemenu'))
    parser.delete_first_token()
    return EntityWizardAside(params, nodelist)

class EntityWizardAside(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def render(self, context):
        request = self.request.resolve(context)
        output = ''
        template = context.get('template', None)
        if template is None:
            return output

        # We should be getting the FieldTypes.json related to the template
        detail_page_sections = []
        template_sections = template.definition.get('sections')
        template_sections.extend(constants.DETAIL_PAGE_APPENDED_SECTIONS)
        for section in template_sections:
            if section.get('hide_on_detail', False):
                continue   
                
            if section.get('requires_auth', False):
                if not request.user.is_authenticated:
                    #print('SECTION: requires_auth')
                    continue                   
                
            if section.get('do_not_show_in_production', False):
                if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                    #print('SECTION: do_not_show_in_production')
                    continue  
            
            detail_page_sections.append(section)

            # still need to handle: section 'hide_if_empty' ??? 

        
        output = render_to_string(constants.DETAIL_WIZARD_ASIDE, {
            'detail_page_sections': detail_page_sections    
        })

        return output

@register.tag(name='render_wizard_sections_detail_pg')
def render_steps_wizard(parser, token):
    '''
        Responsible for rendering the <li/> sections for detail pages
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
        raise TemplateSyntaxError('Unable to parse wizard aside renderer tag')

    nodelist = parser.parse(('endrender_wizard_sections_detail_pg'))
    parser.delete_first_token()
    return EntityWizardSections(params, nodelist)

def get_data_sources(ds_ids, info, default=None):
    '''
        Tries to get the sourced value of data_sources id/name/url
    '''
    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    try:
        source_info = validation.get('source')
        model = apps.get_model(app_label='clinicalcode', model_name=source_info.get('table'))
        # relative = None
        # if 'relative' in source_info:
        #     relative = source_info['relative']

        # query = None
        # if 'query' in source_info:
        #     query = {
        #         source_info['query']: data
        #     }
        # else:
        #     query = {
        #         'pk': data
        #     }

        if ds_ids:
            queryset = model.objects.filter(id__in = ds_ids)
            if queryset.exists():
                #queryset = model.objects.get(id__in = ds_ids)
                return queryset
        
        return default
    except:
        return default
    
def get_template_creation_data(entity, layout, field, request=None, default=None):
    '''
        Used to retrieve assoc. data values for specific keys, e.g.
        concepts, in its expanded format for use with create/update pages
    '''
    data = template_utils.get_entity_field(entity, field)
    info = template_utils.get_layout_field(layout, field)
    if not info or not data:
        return default
    
    if info.get('is_base_field'):
        info = template_utils.try_get_content(constants.metadata, field)

    validation = template_utils.try_get_content(info, 'validation')
    if validation is None:
        return default

    field_type = template_utils.try_get_content(validation, 'type')
    if field_type is None:
        return default
    
    if field_type == 'concept':
        values = []
        for item in data:
            value = concept_utils.get_clinical_concept_data(
                item['concept_id'],
                item['concept_version_id'],
                remove_userdata=True,
                hide_user_details=True,
                include_component_codes=False, 
                include_attributes=True, 
                include_reviewed_codes=True,
                derive_access_from=request
            )


            if value:
                values.append(value)
        
        return values
    
    if info.get('field_type') == 'data_sources':
        return get_data_sources(data, info, default=default)
    
    if template_utils.is_metadata(entity, field):
        return template_utils.get_metadata_value_from_source(entity, field, default=default)
    
    return template_utils.get_template_data_values(entity, layout, field, default=default)


class EntityWizardSections(template.Node):
    def __init__(self, params, nodelist):
        self.request = template.Variable('request')
        self.params = params
        self.nodelist = nodelist
    
    def __try_get_entity_value(self, template, entity, field):
        value = get_template_creation_data(entity, template, field, request=self.request, default=None)
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
    
    def __try_get_computed(self, request, field):
        struct = template_utils.get_layout_field(constants.metadata, field)
        if struct is None:
            return

        validation = template_utils.try_get_content(struct, 'validation')
        if validation is None:
            return
        
        if not validation.get('computed'):
            return
        
        if field == 'group':
            return permission_utils.get_user_groups(request)

    def __generate_wizard(self, request, context):
        output = ''
        template = context.get('template', None)
        entity = context.get('entity', None)
        if template is None:
            return output
        
        merged_definition = template_utils.get_merged_definition(template, default={})
        template_fields = template_utils.try_get_content(merged_definition, 'fields')
        template_fields.update(constants.DETAIL_PAGE_APPENDED_FIELDS)
        template.definition['fields'] = template_fields

        
        # We should be getting the FieldTypes.json related to the template
        field_types = constants.FIELD_TYPES
        template_sections = template.definition.get('sections')
        #template_sections.extend(constants.DETAIL_PAGE_APPENDED_SECTIONS)
        for section in template_sections:
            if section.get('hide_on_detail', False):
                continue   
            
            if section.get('requires_auth', False):
                if not context.get('user').is_authenticated:
                    continue   
                
            if section.get('do_not_show_in_production', False):
                if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                    continue    
                    
            # still need to handle: section 'hide_if_empty' ??? 
        
            # don't show section description in detail page
            section['hide_description'] = True
            
            output += self.__try_render_item(template_name=constants.DETAIL_WIZARD_SECTION_START
                                             , request=request
                                             , context=context.flatten() | { 'section': section })

            for field in section.get('fields'):
                template_field = template_utils.get_field_item(template.definition, 'fields', field)
                if not template_field:
                    template_field = template_utils.try_get_content(constants.metadata, field)

                if not template_field:
                    continue
                
                active = template_field.get('active', False)
                if isinstance(active, bool) and not active:
                    continue
                
                if template_field.get('hide_on_detail'):
                    continue
                
                if template_field.get('is_base_field', False):
                    template_field = constants.metadata.get(field) | template_field

                component = template_utils.try_get_content(field_types, template_field.get('field_type'))                
                if component is None:
                    continue

                if template_utils.is_metadata(GenericEntity, field):
                    field_data = template_utils.try_get_content(constants.metadata, field)
                else:
                    field_data = template_utils.get_layout_field(template, field)
                

                if template_field.get('requires_auth', False):
                    if not request.user.is_authenticated:
                        continue    
  

                if template_field.get('do_not_show_in_production', False):
                    if (not settings.IS_DEMO and not settings.IS_DEVELOPMENT_PC):
                        continue                                                  

                if field_data is None:
                    field_data = ''
                    #continue


                component['field_name'] = field
                component['field_data'] = field_data

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
                
                if template_utils.is_metadata(GenericEntity, field):
                    options = template_utils.get_template_sourced_values(constants.metadata, field)

                    if options is None:
                        options = self.__try_get_computed(request, field)
                else:
                    options = template_utils.get_template_sourced_values(template, field)
                
                if options is not None:
                    component['options'] = options

                if entity:
                    component['value'] = self.__try_get_entity_value(template, entity, field)
                else:
                    component['value'] = ''

                if template_field.get('hide_if_empty', False):
                    if component['value'] is None or str(component['value']) == '':
                        continue    
                                    

                output_type = component.get("output_type")
                uri = f'{constants.DETAIL_WIZARD_OUTPUT_DIR}/{output_type}.html'
                output += self.__try_render_item(template_name=uri, request=request, context=context.flatten() | { 'component': component })

        output += render_to_string(template_name=constants.DETAIL_WIZARD_SECTION_END, request=request, context=context.flatten() | { 'section': section })
        return output
    
    def render(self, context):
        if not isinstance(self.request, HttpRequest):
            self.request = self.request.resolve(context)
        return self.__generate_wizard(self.request, context)
