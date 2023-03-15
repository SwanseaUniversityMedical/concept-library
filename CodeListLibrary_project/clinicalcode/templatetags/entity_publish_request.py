from cmath import e
from email import message
from pyexpat.errors import messages
import re
from django import template
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse

register = template.Library()

@register.inclusion_tag('components/publish_request/show_errors_approval.html', takes_context=True, name='render_errors_approval')
def render_errors_approval(context, *args, **kwargs):
    errors = []
    if  context['entity_is_deleted']:
        message = "This entity has been deleted and cannot be approved."
        errors.append(message)
        
    
    if  not context['is_owner'] and not context['is_moderator']:
        message = 'You must be the owner to publish.'
        errors.append(message)
    
    if not context['entity_has_data']:
        message = 'This entity has no data and cannot be approved.'
        errors.append(message)
    else:
        if  not context['is_allowed_view_children']:
            message = 'You must have view access to all concepts/phenotypes.'
            errors.append(message)
        
        if not context['all_not_deleted']:
            message = 'All concepts/phenotypes must not be deleted.'
            errors.append(message)
        
        if not context['all_are_published']:
            message = 'All concepts/phenotypes must be published.'
            errors.append(message)

    return {'errors': errors}


@register.inclusion_tag('components/publish_request/publish_button.html', takes_context=True, name='render_publish_button')
def render_publish_button(context, *args, **kwargs):
    user_group = context['request'].user.groups.filter(name='Moderators').exists()
    button_context = {}
    if user_group:
        if not context['live_ver_is_deleted']:
            if context["approval_status"]== 1 and context["is_latest_pending_version"]:
                button_context = {'class_modal':"js-load-modal btn btn-warning",
                        'url':reverse('generic_entity_publish', kwargs={'pk': context['entity']['id'], 'history_id': context['entity']['history_id']}),
                        'title': "Needs to be approved"}
                        
            else:
                if context['approval_status'] == 3:
                    button_context = {'class_modal':"js-load-modal  btn btn-danger",
                        'url':reverse('generic_entity_publish', kwargs={'pk': context['entity']['id'], 'history_id': context['entity']['history_id']}),
                        'title': "Approve declined entity"
                        }
                else:
                    button_context = {'class_modal':"js-load-modal btn btn-outline-primary btn-cl btn-cl-secondary",
                        'url':reverse('generic_entity_publish', kwargs={'pk': context['entity']['id'], 'history_id': context['entity']['history_id']}),
                        'title': "Publish immediately"
                        }
        else:
            button_context =  {'class_modal':"btn btn-primary",
                        'title': "This version is already published" if context["is_published"] and context["approval_status"] == 2  
                        else  "Deleted phenotypes cannot be published !!" if context["live_ver_is_deleted"] else ""
                        }
        
        if context["approval_status"] == 1 and context["is_latest_pending_version"]:
            button_context["Button_type"] = "Approve"
            return button_context
        else:
            button_context["Button_type"] = "Publish"
            return button_context
    else:
        if not context["is_lastapproved"] and context["approval_status"] is None and not user_group:
            button_context = {'class_modal':"js-load-modal btn btn-outline-primary btn-cl btn-cl-secondary",
                        'url':reverse('generic_entity_request_publish', kwargs={'pk': context['entity']['id'], 'history_id': context['entity']['history_id']}),
                        'title': "Needs to be approved"}
        elif  context["is_lastapproved"] and not context["live_ver_is_deleted"] and not context["approval_status"] == 3:
            button_context = {'class_modal':"js-load-modal btn btn-outline-primary btn-cl btn-cl-secondary",
                        'url':reverse('generic_entity_publish', kwargs={'pk': context['entity']['id'], 'history_id': context['entity']['history_id']}),
                        'title': "Publish immediately"}
        else:
            if context["is_published"] and context["approval_status"] == 2:
                button_context = {'class_modal':"btn btn-primary",
                            'title': "This version is already published"}
            elif context["live_ver_is_deleted"]:
                button_context = {'class_modal':"btn btn-primary",
                            'title': "Deleted phenotypes cannot be published !!"}
            elif context["approval_status"] == 3:
                button_context = {'class_modal':"btn btn-danger",
                                  'disabled': 'true',
                            'title': "This version has been declined"}
            elif context["approval_status"] == 1:
                if context["entity"]["owner_id"] == context["request"].user.id:
                    button_context = {'class_modal':"btn btn-warning",
                                      'disabled': 'true',
                            'title': "This version is pending approval"}
                else:
                    button_context = {'class_modal':"btn btn-primary",'disabled': 'true',
                            'title': "Unavailable to publish"}
        
        if context["approval_status"] == 3:
            button_context["Button_type"] = "Rejected"
            return button_context
        elif context["approval_status"] == 1:
            button_context["Button_type"] = "Pending"
            return button_context
        else:
            button_context["Button_type"] = "Publish"
            return button_context
                    

            

            
        
    




    



    

