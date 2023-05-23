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

    # update history list
    data['html_history_list'] = render_to_string(
        'components/details/version_history.html',
        {
            'history': get_history_table_data(request, pk),  # entity.history.all(),
            'current_entity_history_id': int(entity_history_id),  # entity.history.latest().pk,
            'published_historical_ids':
                list(PublishedGenericEntity.objects.filter(entity_id=pk, approval_status=constants.APPROVAL_STATUS.APPROVED).values_list('entity_history_id', flat=True))
        },
        request=request)
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
    if data['approval_status'] == constants.APPROVAL_STATUS.APPROVED:
        data['message'] = """The {entity_type} version has been successfully published.<a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'], url=reverse('entity_history_detail',  args=(pk,entity_history_id)), pk=pk,history=entity_history_id)

        send_email_decision_entity(entity, checks['entity_type'], data['approval_status'])
        return data

    #publish message if not declined
    elif len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=constants.APPROVAL_STATUS.APPROVED)) > 0 and not data['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
        data['message'] = """The {entity_type} version has been successfully published.
                                 <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'], url=reverse('entity_history_detail', args=(pk,entity_history_id)),
                                                                                                         pk=pk,history=entity_history_id)
        
        send_email_decision_entity(entity, checks['entity_type'], data['approval_status'])

        return data

    #showing rejected message
    elif data['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
        data['message'] = """The {entity_type} version has been rejected .
                                               <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('entity_history_detail', args=(pk,entity_history_id)),
            pk=pk,history=entity_history_id)
        
        send_email_decision_entity(entity,checks['entity_type'],data['approval_status'])

        return data

    # ws is approved by moderator if moderator approved different version
    elif data['approval_status'] is None and checks['is_moderator']:
        data['message'] = """The {entity_type} version has been successfully published.
                                                <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('entity_history_detail', args=(pk,entity_history_id)),
            pk=pk,history=entity_history_id)

        return data


    #show pending message if user clicks to request review
    elif data['approval_status'] == constants.APPROVAL_STATUS.PENDING:
        data['message'] = """The {entity_type} version is going to be reviewed by the moderator.
                                                      <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('entity_history_detail', args=(pk,entity_history_id)),
            pk=pk,history=entity_history_id)
        
        send_email_decision_entity(entity,checks['entity_type'],0)

        return data





def checkEntityToPublish(request, pk, entity_history_id):
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
    allow_to_publish = True
    entity_is_deleted = False
    is_owner = True
    is_moderator = False
    is_latest_pending_version = False

    if (GenericEntity.objects.get(id=pk).is_deleted == True):
        allow_to_publish = False
        entity_is_deleted = True

    #check if user is not owner
    if (GenericEntity.objects.filter(Q(id=pk), Q(owner=request.user)).count() == 0):
        allow_to_publish = False
        is_owner = False

    if (request.user.groups.filter(name="Moderators").exists()):
        allow_to_publish = True
        is_moderator = True

    #check if either moderator or owner
    if (request.user.groups.filter(name="Moderators").exists()
            and not (GenericEntity.objects.filter(Q(id=pk), Q(owner=request.user)).count() == 0)):
        allow_to_publish = True
        is_owner = True
        is_moderator = True

    #check if current version of entity is the latest version to approve
    if len(PublishedGenericEntity.objects.filter(entity_id=pk, entity_history_id=entity_history_id, approval_status=constants.APPROVAL_STATUS.PENDING)) > 0:
        is_latest_pending_version = True


    entity_ver = GenericEntity.history.get(id=pk, history_id=entity_history_id)
    is_published = checkIfPublished(GenericEntity, pk, entity_history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, entity_history_id)
    is_lastapproved = len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=constants.APPROVAL_STATUS.APPROVED)) > 0
    other_pending = len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=constants.APPROVAL_STATUS.PENDING)) > 0
    

    # get historical version 
    entity = entity_db_utils.get_historical_entity(pk, entity_history_id
                                            , highlight_result = [False, True][entity_db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))  
                                            )
                                                                                                            
    entity_class = entity.template.entity_class.name                                                          

    if entity_class == "Phenotype" or entity_class == "Workingset":
         has_childs, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors = \
        checkChildren(request, entity)
    else: #???
        has_childs, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors = \
        checkChildConcept(request, entity_history_id)
    
   

    if not isOK:
        allow_to_publish = False

    #check if table is not empty
    table_ofEntity = lambda entity_class:  'concept_information' if entity_class== "Phenotype"  else 'workingset_concept_information'
    entity_has_data = len(GenericEntity.history.get(id=pk, history_id=entity_history_id).template_data[table_ofEntity(entity_class)]) > 0

    if not entity_has_data and entity_class == "Workingset":
        allow_to_publish = False


    checks = {
        'entity': entity,
        'entity_type': entity_class,
        'name': entity_ver.name,
        'errors': errors,
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
        'is_allowed_view_children': is_allowed_view_children, #to see if child phenotypes of ws is not deleted/not published etc
        'all_are_published': all_are_published,
        'all_not_deleted': all_not_deleted
    }
    return checks

def checkChildren(request, entity):
        """
        Check if entity child data is validated
        @param request: user request object
        @param entity: historical entity object
        @return: collection of boolean conditions
        """

        entity_class = entity.template.entity_class.name 
         
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
            has_child_entitys = False
            child_entitys_versions = ''
        else:
            child_entitys_versions = [(x[child_id], x[child_version_id]) for x in entity.template_data[name_table]]

        # Now check all the child concepts for deletion(from live version) and Publish(from historical version)
        # we check access(from live version) here.

        errors = {}
        has_child_entitys = False
        all_not_deleted = True
        is_allowed_view_children = True
        all_are_published = True

        if child_entitys_versions:
            has_child_entitys = True


        for p in child_entitys_versions:
            isDeleted = (Concept.objects.filter(Q(id=p[0])).exclude(is_deleted=True).count() == 0) if entity_class == "Phenotype" else (GenericEntity.objects.filter(Q(id=p[0])).exclude(is_deleted=True).count() == 0) 
            if isDeleted:
                errors[p[0]] = 'Child ' + name_child + '(' + str(p[0]) + ') is deleted'
                all_not_deleted = False


        for p in child_entitys_versions:
            is_published = checkIfPublished(Concept, p[0], p[1]) if entity_class == "Phenotype" else checkIfPublished(GenericEntity, p[0], p[1])
            if not is_published:
                errors[str(p[0]) + '/' + str(p[1])] = 'Child ' + name_child + '(' + str(p[0]) + '/' + str(p[1]) + ') is not published'
                all_are_published = False


        for p in child_entitys_versions: #??? update to new permission chk
            permitted = allowed_to_view(request,
                                        Concept,
                                        set_id=p[0],
                                        set_history_id=p[1]) if entity_class == "Phenotype" else allowed_to_view(request,
                                                                                                        GenericEntity,
                                                                                                        set_id=p[0],
                                                                                                        set_history_id=p[1])

            if not permitted:
                errors[str(p[0]) + '_view'] = 'Child ' + name_child + '(' + str(p[0]) + ') is not permitted.'
                is_allowed_view_children = False

        isOK = (all_not_deleted and all_are_published and is_allowed_view_children)

        return  has_child_entitys, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors


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

    