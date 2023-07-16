from os import name
import re
from clinicalcode import db_utils
from clinicalcode.entity_utils import entity_db_utils
from django.contrib.auth.models import  User
from django.urls import reverse, reverse_lazy
from django.template.loader import render_to_string
from clinicalcode.tasks import send_review_email
from ..models import *
from ..permissions import *
from clinicalcode.views.GenericEntity import get_history_table_data
from clinicalcode.permissions import allowed_to_view, checkIfPublished, get_publish_approval_status
from clinicalcode.entity_utils import constants, permission_utils

#from clinicalcode.constants import APPROVED_STATUS
from . import constants

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
    data['message'] = send_message(pk, data, entity, entity_history_id, checks)['message']

    return data

def send_message(pk, data, entity, entity_history_id, checks):
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
        return format_message_and_send_email(pk, data, entity, entity_history_id, checks, approved_template)
    elif approval_status == constants.APPROVAL_STATUS.REJECTED:
        return format_message_and_send_email(pk, data, entity, entity_history_id, checks, rejected_template)
    elif approval_status == constants.APPROVAL_STATUS.PENDING:
        return format_message_and_send_email(pk, data, entity, entity_history_id, checks, pending_template)
    elif approval_status is None and checks['is_moderator']:
        return format_message_and_send_email(pk, data, entity, entity_history_id, checks, approved_template)
    elif len(PublishedGenericEntity.objects.filter(
            entity=GenericEntity.objects.get(pk=pk).id, 
            approval_status=constants.APPROVAL_STATUS.APPROVED)) > 0 and approval_status != constants.APPROVAL_STATUS.REJECTED:
        return format_message_and_send_email(pk, data, entity, entity_history_id, checks, approved_template)


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
    user_is_owner = generic_entity.owner == request.user
    latest_pending_version_exists = PublishedGenericEntity.objects.filter(
        entity_id=pk, 
        entity_history_id=entity_history_id, 
        approval_status=constants.APPROVAL_STATUS.PENDING
    ).exists()

    # Determine the status of the entity
    entity_is_deleted = generic_entity.is_deleted
    is_owner = not entity_is_deleted and user_is_owner
    is_moderator = not entity_is_deleted and user_is_moderator
    is_latest_pending_version = not entity_is_deleted and latest_pending_version_exists

    # Determine the final permission to publish
    allow_to_publish = is_owner or is_moderator
    

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
    is_published = checkIfPublished(GenericEntity, pk, entity_history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, entity_history_id)
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
        is_ok, all_not_deleted, all_are_published, errors = check_children(request,entity,get_entity_class(entity_class))

        if not is_ok:
            allow_to_publish = False

    entity_has_data = bool(GenericEntity.history.get(id=pk, history_id=entity_history_id).template_data[get_table_of_entity(entity_class)])

    # Check entity data and class
    if not entity_has_data and entity_class == "Workingset":
        allow_to_publish = False

    
    checks = {
        'entity_type': entity_class,
        'name': entity_ver.name,
        'errors': errors or None,
        'allowed_to_publish': allow_to_publish,
        'entity_is_deleted': entity_is_deleted,
        'is_owner': is_owner,
        'is_moderator': is_moderator,
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
        
        if len(entity.template_data[name_table]) == 0:
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
        print(errors)

        # Check if all objects are not deleted
        all_not_deleted = not bool(errors)


        for entity_child in child_entitys_versions:
            entity_child_id = entity_child[0]
            entity_child_version = entity_child[1]

            concept_owner_id = Concept.history.get(id=entity_child_id).phenotype_owner_id
            if concept_owner_id != entity.id:
                entity_from_concept = GenericEntity.history.filter(
                id=concept_owner_id,
                publish_status=constants.APPROVAL_STATUS.APPROVED.value)
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
    return bool(re.match(r"(?i)^(Phenotype|Workingset)$", entity_class))

def get_entity_class(entity_class):
    final_entity = lambda entity_class: 'Phenotype' if re.search(r"(?i)Phenotype", entity_class) else ('Workingset' if re.search(r"(?i)Workingset", entity_class) else None)
    return final_entity(entity_class)

def get_table_of_entity(entity_class):
    return 'concept_information' if entity_class == "Phenotype" else 'workingset_concept_information'


def format_message_and_send_email(pk, data, entity, entity_history_id, checks, message_template):
    """
    Format the message, send an email, and update data with the new message
    """
    data['message'] = message_template.format(
        entity_type=checks['entity_type'], 
        url=reverse('entity_history_detail', args=(pk, entity_history_id)), 
        pk=pk,
        history=entity_history_id
    )
    #send_email_decision_entity(entity, checks['entity_type'], data['approval_status'])
    return data


def send_email_decision_entity(entity, entity_type, approved):
    """
    Call util function to send email decision
    @param workingset: workingset object
    @param approved: approved status flag
    """
    if approved == 1:
        send_review_email.delay(entity.id, entity.name, entity.owner_id,
                                   "Published",
                                   f"{entity_type} has been successfully approved and published on the website")
        
    elif approved == 0:
        send_review_email.delay(entity.id, entity.name, entity.owner_id,
                                   "Pending",
                                   f"{entity_type} has been submitted and waiting moderator to publish on the website")

    elif approved == 2:
        # This line for the case when user want to get notification of same workingset id but different version
        send_review_email.delay(entity.id, entity.name, entity.owner_id,
                                   "Published",
                                   f"{entity_type} has been successfully approved and published on the website")
    elif approved == 3:
        send_review_email.delay(entity.id, entity.name, entity.owner_id,
                                   "Rejected",
                                   f"{entity_type} has been rejected by the moderator. Please consider update changes and try again")

    