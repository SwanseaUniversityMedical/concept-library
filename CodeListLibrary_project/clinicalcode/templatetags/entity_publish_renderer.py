from cmath import e
from email import message
from pyexpat.errors import messages
import re
from django import template
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, reverse
from ..entity_utils import permission_utils, constants

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
    user_is_moderator = permission_utils.is_member(context['request'].user, "Moderators")
    user_is_owner = context['entity'].owner == context['request'].user
    button_context = {'url_decline': reverse('generic_entity_decline', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id})}
    if user_is_moderator:
        if not context['live_ver_is_deleted']:
            if context["approval_status"]== constants.APPROVAL_STATUS.PENDING and context["is_latest_pending_version"]:
                button_context.update({'class_modal':"primary-btn dropdown-btn__label ",
                                  'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                  'title': "Needs to be approved"
                                  })
               
                        
            else:
                if context['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
                     button_context.update({'class_modal':"primary-btn dropdown-btn__label",
                                      'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                      'title': "Approve declined entity"
                                      })
                else:
                     button_context.update({'class_modal':"primary-btn dropdown-btn__label ",
                                      'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                      'title': "Publish immediately"
                                      })
        else:
             button_context.update({'class_modal':"btn btn-primary",
                               'title': "This version is already published" if context["is_published"] and context["approval_status"] == constants.APPROVAL_STATUS.APPROVED  
                               else  "Deleted phenotypes cannot be published !!" if context["live_ver_is_deleted"] else ""
                               })
        
        if context["approval_status"] == constants.APPROVAL_STATUS.PENDING and context["is_latest_pending_version"]:
            button_context["Button_type"] = "Approve"
            return button_context
        else:
            button_context["Button_type"] = "Publish"
            return button_context
    else:
        
        if not context["is_lastapproved"] and context["approval_status"] is None and user_is_owner:
             button_context.update({'class_modal':"primary-btn dropdown-btn__label",
                              'url': reverse('generic_entity_request_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                              'title': "Needs to be approved"
                              })
        elif  context["is_lastapproved"] and not context["live_ver_is_deleted"] and not context["approval_status"] == constants.APPROVAL_STATUS.REJECTED:
             button_context.update({'class_modal':"primary-btn dropdown-btn__label",
                              'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                              'title': "Publish immediately"
                              })
        else:
            if context["is_published"] and context["approval_status"] == constants.APPROVAL_STATUS.APPROVED:
                 button_context.update({'class_modal':"primary-btn__text-success dropdown-btn__label",
                                  'title': f"This version is already {constants.APPROVAL_STATUS.APPROVED.name.lower()} "
                                  })
            elif context["live_ver_is_deleted"]:
                 button_context.update({'class_modal':"primary-btn dropdown-btn__label",
                                    'disabled': 'true',
                                  'title': "Deleted phenotypes cannot be published !!"
                                  })
            elif context["approval_status"] == constants.APPROVAL_STATUS.REJECTED:
                 button_context.update({'class_modal':"primary-btn text-danger dropdown-btn__label",
                                  'disabled': 'true',
                                  'title': f"This version has been {constants.APPROVAL_STATUS.REJECTED.name.lower()}"
                                  })
            elif context["approval_status"] == constants.APPROVAL_STATUS.PENDING:
                if context["entity"].owner_id== context["request"].user.id:
                     button_context.update({'class_modal':"primary-btn text-warning dropdown-btn__label",
                                      'disabled': 'true',
                                      'title': "This version is pending approval",
                                      'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                      })
                    
            else:
                 button_context.update({'class_modal':"primary-btn dropdown-btn__label",
                                      'disabled': 'true',
                                      'title': "Unavailable to publish"
                                      })

        
        if context["approval_status"] == constants.APPROVAL_STATUS.REJECTED:
            button_context["Button_type"] = constants.APPROVAL_STATUS.REJECTED.name.capitalize()
            return button_context
        elif context["approval_status"] == constants.APPROVAL_STATUS.PENDING:
            button_context["Button_type"] = constants.APPROVAL_STATUS.PENDING.name.capitalize()
            return button_context
        else:
            button_context["Button_type"] = "Publish"
            return button_context
