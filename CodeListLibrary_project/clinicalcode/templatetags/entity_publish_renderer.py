from django import template
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

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
    user_is_owner = permission_utils.can_user_edit_entity(context['request'], context['entity'].id) #context['entity'].owner == context['request'].user
    user_is_publisher = user_is_owner and permission_utils.is_member(context['request'].user, "publishers")

    button_context = {
        'url_decline': reverse('generic_entity_decline', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
        'url_redirect': reverse('entity_history_detail', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
    }

    if user_is_moderator:
        if not context['live_ver_is_deleted']:
            if context["approval_status"]== constants.APPROVAL_STATUS.PENDING and context["is_latest_pending_version"]:
                button_context.update({'class_modal':"primary-btn text-warning bold dropdown-btn__label ",
                                    'Button_type':"Approve",
                                  'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                  'title': "Requires approval"
                                  })            
            else:
                if context['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
                     button_context.update({'class_modal':"primary-btn text-danger bold dropdown-btn__label",
                                      'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                      'Button_type':"Publish",
                                      'title': "Approve declined entity"
                                      })
                else:
                     button_context.update({'class_modal':"primary-btn bold dropdown-btn__label ",
                                      'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                      'Button_type':"Publish",
                                      'title': "Publish immediately"
                                      })
        else:
            if context["is_published"] and context["approval_status"] == constants.APPROVAL_STATUS.APPROVED:
                 button_context.update({'class_modal':"primary-btn__text-success bold dropdown-btn__label",
                                'Button_type': constants.APPROVAL_STATUS.APPROVED.name.capitalize(),	
                               'title': "This version is already published" 
                               })
            else:
                button_context.update({'class_modal':"primary-btn bold text-danger dropdown-btn__label",
                                 'disabled': 'true',
                                 'Button_type':"Entity is deleted",
                                 'title':  "Deleted phenotypes cannot be published!"
                               })
        return button_context
    else:
        if not context["is_lastapproved"] and context["approval_status"] is None and user_is_owner and not context["live_ver_is_deleted"]:
            if user_is_publisher:
                button_context.update({'class_modal':"primary-btn bold dropdown-btn__label",
                            'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                            'Button_type':"Publish",
                            'title': "Publish immediately"
                            })
            else:
                button_context.update({'class_modal':"primary-btn bold dropdown-btn__label",
                                'Button_type': "Request publication",
                                'url': reverse('generic_entity_request_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                'title': "Needs to be approved"
                                })
        elif context["is_lastapproved"] and not context["live_ver_is_deleted"] and context["approval_status"] != constants.APPROVAL_STATUS.REJECTED:
             button_context.update({'class_modal':"primary-btn bold dropdown-btn__label",
                              'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                              'Button_type': "Publish",	
                              'title': "Publish immediately"
                              })
        else:
            if context["is_published"] and context["approval_status"] == constants.APPROVAL_STATUS.APPROVED:
                 button_context.update({'class_modal':"primary-btn__text-success bold dropdown-btn__label",
                                  'title': f"This version is already {constants.APPROVAL_STATUS.APPROVED.name.lower()} "
                                  })
                 
            elif context["live_ver_is_deleted"]:
                  button_context.update({'class_modal':"primary-btn bold text-danger dropdown-btn__label",
                                 'disabled': 'true',
                                 'Button_type': "Entity is deleted",
                                 'title': "Deleted phenotypes cannot be published!"
                               })
                 
            elif context["approval_status"] == constants.APPROVAL_STATUS.REJECTED:
                 button_context.update({'class_modal':"primary-btn bold text-danger dropdown-btn__label",
                                  'disabled': 'true',
                                  'Button_type': constants.APPROVAL_STATUS.REJECTED.name.capitalize(),	
                                  'title': "This version has been rejected."
                                  })
                 
            elif context["approval_status"] == constants.APPROVAL_STATUS.PENDING and user_is_owner:
                button_context.update({'class_modal':"primary-btn bold text-warning dropdown-btn__label",
                                'disabled': 'true',
                                'Button_type': constants.APPROVAL_STATUS.PENDING.name.capitalize(),
                                'title': "This version is pending approval.",
                                'url': reverse('generic_entity_publish', kwargs={'pk': context['entity'].id, 'history_id': context['entity'].history_id}),
                                })
            else:
                button_context.update({ 'pub_btn_hidden': True })
                #  button_context.update({'class_modal':"primary-btn bold dropdown-btn__label",
                #                         'Button_type': "Not permitted",
                #                         'disabled': 'true',
                #                         'title': "Unavailable to publish"
                #                         })

        return button_context
