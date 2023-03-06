from email import message
from pyexpat.errors import messages
from django import template
from django.conf import settings
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.inclusion_tag('components/publish_request/show_errors_approval.html', takes_context=True, name='render_errors_approval')
def render_errors_approval(context, *args, **kwargs):
    errors = []
    if  not context['entity_is_deleted']:
        message = "This entity has been deleted and cannot be approved."
        errors.append(message)
        
    
    if  not context['is_owner'] and not context['is_moderator']:
        message = 'You must be the owner to publish.'
        errors.append(message)
    
    if not context['entity_has_data']:
        message = 'This entity has no data and cannot be approved.'
        errors.append(message)
    else:
        if  context['is_allowed_view_children']:
            message = 'You must have view access to all concepts/phenotypes.'
            errors.append(message)
        
        if not context['all_not_deleted']:
            message = 'All concepts/phenotypes must not be deleted.'
            errors.append(message)
        
        if not context['all_are_published']:
            message = 'All concepts/phenotypes must be published.'
            errors.append(message)

    return {'errors': errors}
    


    

