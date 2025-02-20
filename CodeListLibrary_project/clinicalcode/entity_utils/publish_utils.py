from django.urls import reverse

import re
from django.contrib.auth.models import  User
from django.urls import reverse, reverse_lazy
from django.template.loader import render_to_string
from clinicalcode.entity_utils import model_utils
from clinicalcode.models import Organisation
from clinicalcode.tasks import send_review_email
from clinicalcode.entity_utils import constants, permission_utils, entity_db_utils

from clinicalcode.models.Concept import Concept
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity

def form_validation(request, data, entity_history_id, pk, entity,checks):
    """
    Update correct historical table and send email message, and success message to screen
    @param request: user request object
    @param data: from any current operations with publish
    @param entity_history_id: entity historical id
    @param pk: entity id for database query
    @param entity: object
    @param checks: additional utils checks  before approval
    @return: updated data dictionary to update historical table and request message
    """
    data['form_is_valid'] = True
    data['latest_history_ID'] = entity_history_id  # entity.history.latest().pk
    #send email message state and client side message
    data['message'] = send_message(request, pk, data, entity, entity_history_id, checks)['message']

    return data

def send_message(request, pk, data, entity, entity_history_id, checks):
    """
    Send email message with variational decisions approved/pending/declined and show message to the  client side
    @param pk: entity id
    @param data: dictionary data of approval stage
    @param entity: entity object
    @param entity_history_id: entity history id
    @param checks: additional checks of entity
    @return: updated data dictionary with client side message
    """
    # Message templates
    approved_template = """The {entity_type} version has been successfully published.<a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>"""
    rejected_template = """The {entity_type} version has been rejected .<a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>"""
    pending_template = """The {entity_type} version is going to be reviewed by the moderator.<a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>"""

    # Determine the appropriate message template and send email
    approval_status = data['approval_status']
    if approval_status == constants.APPROVAL_STATUS.APPROVED:
        return format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, approved_template)
    elif approval_status == constants.APPROVAL_STATUS.REJECTED:
        return format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, rejected_template)
    elif approval_status == constants.APPROVAL_STATUS.PENDING:
        return format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, pending_template)
    elif approval_status is None and checks['is_moderator']:
        return format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, approved_template)
    elif len(PublishedGenericEntity.objects.filter(
            entity=GenericEntity.objects.get(pk=pk).id, 
            approval_status=constants.APPROVAL_STATUS.APPROVED)) > 0 and approval_status != constants.APPROVAL_STATUS.REJECTED:
        return format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, approved_template)


def check_entity_to_publish(request, pk, entity_history_id):
    '''
        Allow to publish if:
        - entity is not deleted
        - user is an owner
        - Workingset contains codes
        - all conceots are published
        @param request: user request object
        @param pk: entity id
        @param entity_history_id: historical id of entity
        @return: dictionary containing all conditions to publish
    '''
    # Fetch the required objects from the database only once
    generic_entity = GenericEntity.objects.get(id=pk)
    user_is_moderator = request.user.groups.filter(name="Moderators").exists()
    user_entity_access = permission_utils.can_user_edit_entity(request, generic_entity.id) #generic_entity.owner == request.user

    latest_pending_version_exists = PublishedGenericEntity.objects.filter(
        entity_id=pk, 
        entity_history_id=entity_history_id, 
        approval_status=constants.APPROVAL_STATUS.PENDING
    ).exists()

    # Determine the status of the entity
    entity_is_deleted = generic_entity.is_deleted
    is_entity_user = not entity_is_deleted and user_entity_access
    is_publisher = not entity_is_deleted and generic_entity.owner == request.user and request.user.groups.filter(name="publishers").exists()
    is_moderator = not entity_is_deleted and user_is_moderator
    is_latest_pending_version = not entity_is_deleted and latest_pending_version_exists

    # Determine the final permission to publish
    allow_to_publish = is_entity_user or is_moderator or is_publisher

    generic_entity = GenericEntity.objects.get(pk=pk)
    published_entity_approved = PublishedGenericEntity.objects.filter(
        entity=generic_entity.id, 
        approval_status=constants.APPROVAL_STATUS.APPROVED
    )
    published_entity_pending = PublishedGenericEntity.objects.filter(
        entity=generic_entity.id, 
        approval_status=constants.APPROVAL_STATUS.PENDING
    )

    # Initialize the status variables based on the fetched data
    entity_ver = GenericEntity.history.get(id=pk, history_id=entity_history_id)
    is_published = permission_utils.check_if_published(GenericEntity, pk, entity_history_id)
    approval_status = permission_utils.get_publish_approval_status(GenericEntity, pk, entity_history_id)
    is_lastapproved = published_entity_approved.exists()
    other_pending = published_entity_pending.exists()

    # Get historical version
    highlight_result = entity_db_utils.is_referred_from_search_page(request)
    q_highlight = entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))
    entity = entity_db_utils.get_historical_entity(pk, entity_history_id, highlight_result, q_highlight)

    # Entity class
    entity_class = entity.template.entity_class.name 

    # Check children
    if is_valid_entity_class(entity_class):
        is_ok, all_not_deleted, all_are_published, errors = check_child_validity(request,entity,get_entity_class(entity_class))

        if not is_ok:
            allow_to_publish = False

    entity_has_data = bool(GenericEntity.history.get(id=pk, history_id=entity_history_id).template_data[get_table_of_entity(entity_class)])

    # Check entity data and class
    if not entity_has_data and entity_class == "Workingset":
        allow_to_publish = False
    
    check_organisation_authorities(request,entity, entity_class)
    
    checks = {
        'entity_type': entity_class,
        'name': entity_ver.name,
        'errors': errors or None,
        'allowed_to_publish': allow_to_publish,
        'entity_is_deleted': entity_is_deleted,
        'is_entity_user': is_entity_user,
        'is_moderator': is_moderator,
        'is_publisher': is_publisher,
        'approval_status': approval_status,
        'is_lastapproved': is_lastapproved,
        'other_pending': other_pending,
        'entity_has_data': entity_has_data,
        'is_published': is_published,
        'is_latest_pending_version': is_latest_pending_version,
        'all_are_published': all_are_published,
        'all_not_deleted': all_not_deleted
    }
    return checks

def check_organisation_authorities(request,entity,entity_class):
    organisation_checks = {}

    organisation = permission_utils.get_organisation_info(request.user)
    organisation_permissions = permission_utils.has_org_authority(request,organisation)
    organisation_user_role = permission_utils.get_organisation_role(request.user)
    print(organisation_permissions)
     
    if organisation_permissions["org_user_managed"] is None or False:
        return False

    if organisation_permissions["can_moderate"]:
       if organisation_user_role.value >= 1:
           organisation_checks["allowed_to_publish"] = True
           print(organisation_checks)

    return organisation_checks


def check_child_validity(request, entity, entity_class, check_publication_validity=False):
    """
    Wrapper for 'check_children' method authored by @zinnurov
    to optionally test publication & deletion status

    [!] Implementation required until we can discuss how to handle the issues
    surrounding legacy Phenotypes / Concepts that have imported entities from
    archived and/or unpublished entities.

    Args:
        request {RequestContext}: the request context of the form
        entity {instance}: an instance of an entity
        entity_class {Model()}: the model entity class
    
    Returns:
        {boolean} - a boolean that describes the validity of the child entity
        {boolean} - a boolean that describes whether the entity passed the deleted test
        {boolean} - a boolean that describes whether the entity passed the publication check
        {list} - a list of any errors that may have been encountered when testing each entity
    """

    if check_publication_validity:
        return check_children(request, entity, entity_class)
    
    # defaults to true
    return True, True, True, []

def check_children(request, entity, entity_class):
        """
        Check if entity child data is validated
        @param request: user request object
        @param entity: historical entity object
        @return: collection of boolean conditions
        """         
        if entity_class == "Phenotype":
            name_table = 'concept_information'
            child_id = 'concept_id'
            child_version_id = 'concept_version_id'
            name_child = 'concept'
        elif entity_class == "Workingset":
            name_table = 'workingset_concept_information'
            child_id = 'phenotype_id'
            child_version_id = 'phenotype_version_id'
            name_child = 'phenotype'
        
        if entity.template_data[name_table] is None or len(entity.template_data[name_table]) == 0:
            child_entitys_versions = ''
        else:
            child_entitys_versions = [(x[child_id], x[child_version_id]) for x in entity.template_data[name_table]]

        # Now check all the child concepts for deletion(from live version) and Publish(from historical version)
        # we check access(from live version) here.
        errors = []
        all_not_deleted = True
        all_are_published = True

        # Collect all ids from child_entitys_versions
        ids = [p[0] for p in child_entitys_versions]

        # Query the database once for each model
        deleted_objects = Concept.objects.filter(id__in=ids, is_deleted=True) if entity_class == "Phenotype" else GenericEntity.objects.filter(id__in=ids, is_deleted=True)

        # Iterate through deleted objects and update errors dictionary
        errors = [{obj.id: f'Child {name_child}({obj.id}) is deleted',"url_parent":None} for obj in deleted_objects]
        # Check if all objects are not deleted
        all_not_deleted = not bool(errors)

        for entity_child in child_entitys_versions:
            entity_child_id = entity_child[0]
            entity_child_version = entity_child[1]

            concept_owner_id = Concept.objects.get(id=entity_child_id).phenotype_owner_id
            if concept_owner_id != entity.id:
                entity_from_concept = GenericEntity.history.filter(
                    id=concept_owner_id,
                    publish_status=constants.APPROVAL_STATUS.APPROVED.value
                )

                if entity_from_concept.exists():
                    inheritated_childs = [(i[child_id],i[child_version_id]) for i in entity_from_concept.values_list("template_data", flat=True)[0][name_table]]
                    is_published = (entity_child_id,entity_child_version) in inheritated_childs
                else:
                    is_published = False
            else:
                is_published = True
            if not is_published:
                errors.append({str(entity_child_id) + '/' + str(entity_child_version):"""{name}({id}/{version}) is not published""".format(
                    name=name_child.capitalize(),
                    id=str(entity_child_id),
                    version=str(entity_child_version)
                ),"url_parent": reverse('entity_detail', kwargs={'pk': concept_owner_id})})
                all_are_published = False

        return all_not_deleted and all_are_published, all_not_deleted, all_are_published, errors

def is_valid_entity_class(entity_class):
    """
    Regex function to check entity class name
    @param entity_class: entity class to check
    """
    return bool(re.match(r"(?i)^(Phenotype|Workingset)$", entity_class))

def get_entity_class(entity_class):
    """
    Decide either phenotype or workingset is present so that we can use only one word
    @param entity_class: entity class to check
    """
    final_entity = lambda entity_class: 'Phenotype' if re.search(r"(?i)Phenotype", entity_class) else ('Workingset' if re.search(r"(?i)Workingset", entity_class) else None)
    return final_entity(entity_class)

def get_table_of_entity(entity_class):
    """
    Decide either table data from phenotype or workingset
    @param entity_class: entity class to check
    """
    return 'concept_information' if entity_class == "Phenotype" else 'workingset_concept_information'


def format_message_and_send_email(request, pk, data, entity, entity_history_id, checks, message_template):
    """
    Format the message, send an email, and update data with the new message
    """
    data['message'] = message_template.format(
        entity_type=checks['entity_type'], 
        url=reverse('entity_history_detail', args=(pk, entity_history_id)), 
        pk=pk,
        history=entity_history_id
    )
    send_email_decision_entity(request,entity, entity_history_id, checks['entity_type'], data)
    return data

def get_emails_by_groupname(groupname):
    user_list = User.objects.filter(groups__name=groupname)
    return [i.email for i in user_list]

def send_email_decision_entity(request, entity, entity_history_id, entity_type,data):
    """
    Call util function to send email decision
    @param workingset: workingset object
    @param approved: approved status flag
    """
    #print(entity_db_utils.send_review_email_generic(entity.id,entity.name, entity.owner_id, "Published", "review_message"))
    url_redirect = reverse('entity_history_detail', kwargs={'pk': entity.id, 'history_id': entity_history_id})
    context = {"id":entity.id,"history_id":entity_history_id, "entity_name":data['entity_name_requested'], "entity_user_id": entity.owner_id,"url_redirect":url_redirect}
    if data['approval_status'].value == constants.APPROVAL_STATUS.PENDING:
        context["status"] = "Pending"
        context["message"] = "Your Phenotype has been submitted and is under review"
        context["staff_emails"] = get_emails_by_groupname("Moderators")
        send_review_email(request, context)
    elif data['approval_status'].value == constants.APPROVAL_STATUS.APPROVED:
        # This line for the case when user want to get notification of same workingset id but different version
        context["status"] = "Published"
        context["message"] = "Your Phenotype has been approved and successfully published"
        send_review_email(request, context)
    elif data['approval_status'].value == constants.APPROVAL_STATUS.REJECTED:
        context["status"] = "Rejected"
        context["message"] = "Your Phenotype submission has been rejected by the moderator"
        context["custom_message"] = "We welcome you to try again but please address these concerns with your Phenotype first" #TODO add custom message logic
        send_review_email(request, context)
