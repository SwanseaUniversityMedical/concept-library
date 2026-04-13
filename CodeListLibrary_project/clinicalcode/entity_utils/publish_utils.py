from django.urls import reverse
from django.contrib.auth import get_user_model
from clinicalcode.entity_utils import model_utils

import re

from clinicalcode.tasks import send_review_email
from clinicalcode.entity_utils import constants, permission_utils
from clinicalcode.models.Organisation import Organisation, OrganisationMembership
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.templatetags.entity_renderer import get_template_entity_name
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity

User = get_user_model()

def form_validation(request, data, pk, history_id, entity, checks):
    """
    Update correct historical table and send email message, and success message to screen.
    
    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request   (HttpRequest): the request context
        data    (Dict[Str,Any]): computed client & email data _assoc._ with this request
        pk                (str): the ID of the entity to publish
        history_id        (int): the history ID of the entity to publish
        entity          (Model): the entity to be published
        checks  (Dict[Str,Any]): conditional checks computed for the entity of interest

    Returns:
        (Dict[Str,Any]): a `dict` updated by ref to _incl._ the historical table and request message(s)
    """
    data['form_is_valid'] = True
    data['latest_history_ID'] = history_id

    # Send email message state and client side message
    data['message'] = send_message(request, data, pk, history_id, entity, checks)['message']
    return data

def send_message(request, data, pk, history_id, entity, checks):
    """
    Send email message with variational decisions approved/pending/declined and show message to the client side.
    
    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request   (HttpRequest): the request context
        data    (Dict[Str,Any]): computed client & email data _assoc._ with this request
        pk                (str): the ID of the entity to publish
        history_id        (int): the history ID of the entity to publish
        entity          (Model): the entity to be published
        checks  (Dict[Str,Any]): conditional checks computed for the entity of interest

    Returns:
        (Dict[Str,Any]): a `dict` updated by ref to _incl._ the historical table and request message(s)
    """
    # Message templates
    approved_template = '''The {entity_type} version has been successfully published.<a href="{url}" class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history})</a>'''
    rejected_template = '''The {entity_type} version has been rejected .<a href="{url}" class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history})</a>'''
    pending_template = '''The {entity_type} version is going to be reviewed by the moderator.<a href="{url}" class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history})</a>'''

    # Determine the appropriate message template and send email
    pub_status = data.get('approval_status', None)
    not_pubbed = pub_status is None or (isinstance(pub_status, bool) and not pub_status)

    if pub_status == constants.APPROVAL_STATUS.APPROVED:
        return format_message_and_send_email(request, data, pk, history_id, entity, checks, approved_template)
    elif pub_status == constants.APPROVAL_STATUS.REJECTED:
        return format_message_and_send_email(request, data, pk, history_id, entity, checks, rejected_template)
    elif pub_status == constants.APPROVAL_STATUS.PENDING:
        return format_message_and_send_email(request, data, pk, history_id, entity, checks, pending_template)
    elif not_pubbed and checks['is_moderator']:
        return format_message_and_send_email(request, data, pk, history_id, entity, checks, approved_template)
    elif (
        PublishedGenericEntity.objects.filter(entity=pk, approval_status=constants.APPROVAL_STATUS.APPROVED.value).count() > 0
        and pub_status != constants.APPROVAL_STATUS.REJECTED
    ):
        return format_message_and_send_email(request, data, pk, history_id, entity, checks, approved_template)

def check_entity_to_publish(request, pk, history_id):
    """
    Computes permissions, properties, and statuses assoc. with a publication request and the _assoc._ `entity` such that:
        - The user has permissions to both edit and publish the entity (or has a role that allows publication outside of these cases, _e.g._ moderator _etc_);
        - The entity is confirmed to be live, _i.e._ not deleted, and all of its descendants are valid;
        - The characteristics of historical publication requests have been taken into account.

    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request (HttpRequest): the request context
        pk              (str): the ID of the entity to publish
        history_id      (int): the history ID of the entity to publish

    Returns:
        (Dict[Str,Any]): A `dict` specifying all conditions, statuses and properties to be considered when publishing the entity
    """
    # Fetch the required objects from the database only once
    entity = GenericEntity.objects.get(id=pk)
    entity_ver = entity.history.get(history_id=history_id)
    user_is_moderator = request.user.groups.filter(name='Moderators').exists()
    user_entity_access = permission_utils.can_user_edit_entity(request, pk)
    published_entities = PublishedGenericEntity.objects.filter(entity_id=pk)

    # Resolve publication requests
    recent_requests = sorted([x for x in published_entities if x.entity_history_id == history_id], key=lambda x: x.modified, reverse=True)

    any_pending_request = next((x for x in published_entities if x.approval_status == constants.APPROVAL_STATUS.PENDING), None)
    any_approved_request = next((x for x in published_entities if x.approval_status == constants.APPROVAL_STATUS.APPROVED), None)

    versioned_pending_request = next((x for x in published_entities if x.entity_history_id == history_id and x.approval_status == constants.APPROVAL_STATUS.PENDING), None)
    verioned_approved_request = next((x for x in published_entities if x.entity_history_id == history_id and x.approval_status == constants.APPROVAL_STATUS.APPROVED), None)

    other_pending = any_pending_request is not None
    is_lastapproved = any_approved_request is not None
    latest_pending_version_exists = versioned_pending_request is not None

    # Determine the status of the request user and the specified entity
    is_deleted = entity.is_deleted
    is_publisher = not is_deleted and entity.owner == request.user and request.user.groups.filter(name='publishers').exists()
    is_moderator = not is_deleted and user_is_moderator
    is_entity_user = not is_deleted and user_entity_access
    is_latest_pending_version = not is_deleted and latest_pending_version_exists

    # Compute permission to publish, current publication status & descendant validity by entity cls
    entity_type = entity.template.entity_class.name if entity.template is not None and entity.template.entity_class is not None else None
    can_publish = is_entity_user or is_moderator or is_publisher
    is_published = verioned_approved_request is not None
    approval_status = recent_requests.pop(0).approval_status if len(recent_requests) > 0 else False

    # NOTE:
    # - The following is legacy behaviour that we may not need; leaving this as a note until we reimplement
    #
    validity_err = None
    all_children_live = True
    all_children_published = True
    # if is_valid_entity_class(entity_type):
    #     is_ok, all_not_deleted, all_are_published, errors = check_child_validity(request, entity, get_entity_class(entity_type))
    #     if not is_ok:
    #         can_publish = False
    #         validity_err = errors
    #         all_children_live = all_not_deleted
    #         all_children_published = all_are_published

    data_name = get_table_of_entity(entity_type)
    has_dataset = entity_ver.template_data.get(data_name, None) is not None

    checks = {
        'name': entity_ver.name,
        'errors': validity_err,
        'entity_type': entity_type,
        'is_moderator': is_moderator,
        'is_publisher': is_publisher,
        'is_published': is_published,
        'other_pending': other_pending,
        'is_entity_user': is_entity_user,
        'approval_status': approval_status,
        'is_lastapproved': is_lastapproved,
        'entity_has_data': has_dataset,
        'all_not_deleted': all_children_live,
        'all_are_published': all_children_published,
        'entity_is_deleted': is_deleted,
        'branded_entity_cls': get_template_entity_name(entity.template.entity_class, entity.template),
        'allowed_to_publish': can_publish,
        'is_latest_pending_version': is_latest_pending_version,
    } 

    # Compute organisation authority and vary the publication conditions
    checks |= check_organisation_authorities(request, entity)

    return checks

def check_organisation_authorities(request, entity):
    """
    Computes permissions, properties, and statuses assoc. with a publication request and the _assoc._ `entity` in the context of:
        1. The desired behaviour of publication as specified by the `HttpRequest`'s `Brand`;
        2. The permissions afforded to the user _assoc._ with this request by the organisation whom shares ownership of the `entity`.

    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request (HttpRequest): the request context
        entity        (Model): the entity to inspect

    Returns:
        (Dict[Str,Any]): A `dict` specifying all conditions, statuses and properties to be considered when publishing the entity in this `Brand`'s organisation ctx
    """
    organisation_checks = { }

    try:
        organisation = entity.organisation
    except Organisation.DoesNotExist:
        organisation = None

    if organisation is None:
        brand = model_utils.try_get_brand(request)
        if brand is not None:
            org_user_managed = permission_utils.is_org_managed(request)
            organisation_checks |= {
                'org_user_managed': org_user_managed,
                'allowed_to_publish': not org_user_managed
            }

        return organisation_checks

    organisation_user_role = permission_utils.get_organisation_role(request.user, organisation)
    organisation_permissions = permission_utils.has_org_authority(request, organisation)

    if isinstance(organisation_permissions, dict) and organisation_user_role is not None:
        if organisation_permissions['org_user_managed']:
            # Reset & derive publication conditions
            org_user_managed = organisation_permissions['org_user_managed']
            can_moderate_org = organisation_permissions.get('can_moderate', False)

            allowed_to_publish = can_moderate_org and organisation_user_role.value >= 1
            allowed_to_moderate = can_moderate_org and organisation_user_role.value >= 2

            organisation_checks |= {
                'is_published': False,
                'is_moderator': allowed_to_moderate,
                'is_publisher': False,
                'other_pending': False,
                'is_lastapproved': False,
                'org_user_managed': org_user_managed,
                'all_are_published': False,
                'allowed_to_publish': allowed_to_publish,
                'is_latest_pending_version': False,
            }
    elif permission_utils.is_org_managed(request):
        organisation_checks |= { 'allowed_to_publish': False }

    return organisation_checks

def is_valid_entity_class(entity_class):
    """
    [!] LEGACY

    Regex function to check entity class name
    @param entity_class: entity class to check
    """
    return bool(re.match(r"(?i)^(Phenotype|Workingset)$", entity_class))

def get_entity_class(entity_class):
    """
    [!] LEGACY

    Decide either phenotype or workingset is present so that we can use only one word
    @param entity_class: entity class to check
    """
    final_entity = lambda entity_class: 'Phenotype' if re.search(r"(?i)Phenotype", entity_class) else ('Workingset' if re.search(r"(?i)Workingset", entity_class) else None)
    return final_entity(entity_class)

def get_table_of_entity(entity_class):
    """
    [!] LEGACY

    Decide either table data from phenotype or workingset
    @param entity_class: entity class to check
    """
    return 'concept_information' if entity_class == "Phenotype" else 'workingset_concept_information'


def format_message_and_send_email(request, data, pk, history_id, entity, checks, message_template):
    """
    Format the message, send an email, and update data with the new message.
    
    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request   (HttpRequest): the request context
        data    (Dict[Str,Any]): computed client & email data _assoc._ with this request
        pk                (str): the ID of the entity to publish
        history_id        (int): the history ID of the entity to publish
        entity          (Model): the entity to be published
        checks  (Dict[Str,Any]): conditional checks computed for the entity of interest
        message_template  (str): the message to be formatted for this entity's publication e-mail

    Returns:
        (Dict[Str,Any]): a `dict` updated by ref to _incl._ the formatted request message(s)
    """
    data['message'] = message_template.format(
        entity_type=checks.get('branded_entity_cls'),
        url=reverse('entity_history_detail', args=(pk, history_id)), 
        pk=pk,
        history=history_id
    )
    send_email_decision_entity(request, entity, history_id, checks, data)
    return data

def get_emails_by_groupname(groupname):
    user_list = User.objects.filter(groups__name=groupname)
    return [i.email for i in user_list]

def get_emails_by_organization(request, entity_id=None):
    organisation = permission_utils.get_organisation(request, entity_id=entity_id)
    if organisation:
        user_list = OrganisationMembership.objects.filter(organisation_id=organisation.id)
        email_list = []
        for membership in user_list:
            if membership.role >= 2:
                email_list.append(membership.user.email)
        return email_list

    return None

def send_email_decision_entity(request, entity, history_id, checks, data):
    """
    Calls async function to send decision email.

    Important:
        - Code owner @zinnurova has moved teams so we should clean this up at some point given the significant changes that have been made to perms.

    Args:
        request   (HttpRequest): the request context
        entity          (Model): the entity to be published
        history_id        (int): the history ID of the entity to publish
        checks  (Dict[Str,Any]): conditional checks computed for the entity of interest
        data    (Dict[Str,Any]): computed client & email data _assoc._ with this request
    """
    url_redirect = reverse('entity_history_detail', kwargs={'pk': entity.id, 'history_id': history_id})

    requested_userid = entity.created_by.id
  
    context = {
        'id': entity.id,
        'history_id': history_id,
        'entity_name': data['entity_name_requested'],
        'entity_user_id': requested_userid,
        'url_redirect': url_redirect,
    }

    if data['approval_status'].value == constants.APPROVAL_STATUS.PENDING:
        context['status'] = 'Pending'
        context['message'] = 'Your work has been submitted and is under review.'
        context['staff_emails'] = get_emails_by_groupname('Moderators')
        if checks.get('org_user_managed', False):
            context['staff_emails'] = get_emails_by_organization(request, entity.id)
        send_review_email(request, context)
    elif data['approval_status'].value == constants.APPROVAL_STATUS.APPROVED:
        # This line for the case when user want to get notification of same workingset id but different version
        context['status'] = 'Published'
        context['message'] = 'The work you submitted has been approved and successfully published.'
        send_review_email(request, context)
    elif data['approval_status'].value == constants.APPROVAL_STATUS.REJECTED:
        context['status'] = 'Rejected'
        context['message'] = 'The work you submitted has been rejected by the moderator'
        context['custom_message'] = 'We welcome you to try again but please address the moderator\'s concerns with your work first.'
        send_review_email(request, context)
