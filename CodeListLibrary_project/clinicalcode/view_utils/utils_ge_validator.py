from clinicalcode import db_utils, generic_entity_db_utils
from clinicalcode.constants import APPROVED_STATUS
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity
from clinicalcode.permissions import allowed_to_edit, allowed_to_view, checkIfPublished, get_publish_approval_status
from django.contrib.auth.models import  User
from django.template.loader import render_to_string
from clinicalcode.views.GenericEntity import get_history_table_data
from django.urls import reverse, reverse_lazy
from ..models import *
from ..permissions import *
from ..constants import ENTITY_LAYOUT

def form_validation(request, data, entity_history_id, pk,entity,checks):
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
        'clinicalcode/generic_entity/partial_history_list.html',
        {
            'history': get_history_table_data(request, pk),  # entity.history.all(),
            'current_entity_history_id': int(entity_history_id),  # entity.history.latest().pk,
            'published_historical_ids':
                list(PublishedGenericEntity.objects.filter(entity_id=pk, approval_status=2).values_list('entity_history_id', flat=True))
        },
        request=request)
    #send email message state and client side message
    data['message'] = send_message(pk, data, entity,entity_history_id,checks)['message']

    return data

def send_message(pk, data, entity,entity_history_id,checks):
    """
    Send email message with variational decisions approved/pending/declined and show message to the  client side
    @param pk: entity id
    @param data: dictionary data of approval stage
    @param entity: entity object
    @param entity_history_id: entity history id
    @param checks: additional checks of entity
    @return: updated data dictionary with client side message
    """
    if data['approval_status'] == 2:
        data['message'] = """The {entity_type} version has been successfully published.<a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'], url=reverse('generic_entity_history_detail',  args=(pk,entity_history_id)), pk=pk,history=entity_history_id)

        #send_email_decision_entity(entity,checks['entity_type'], data['approval_status'])
        return data

    #publish message if not declined
    elif len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=2)) > 0 and not data['approval_status'] == 3:
        data['message'] = """The {entity_type} version has been successfully published.
                                 <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'], url=reverse('generic_entity_history_detail', args=(pk,entity_history_id)),
                                                                                                         pk=pk,history=entity_history_id)
        
        send_email_decision_entity(entity, checks['entity_type'],data['approval_status'])

        return data

    #showing rejected message
    elif data['approval_status'] == 3:
        data['message'] = """The {entity_type} version has been rejected .
                                               <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('generic_entity_history_detail', args=(pk,entity_history_id),
            pk=pk,history=entity_history_id))
        
        send_email_decision_entity(entity,checks['entity_type'],data['approval_status'])

        return data

    # ws is approved by moderator if moderator approved different version
    elif data['approval_status'] is None and checks['is_moderator']:
        data['message'] = """The {entity_type} version has been successfully published.
                                                <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('generic_entity_history_detail', args=(pk,entity_history_id)),
            pk=pk,history=entity_history_id)

        return data


    #show pending message if user clicks to request review
    elif data['approval_status'] == 1:
        data['message'] = """The {entity_type} version is going to be reviewed by the moderator.
                                                      <a href='{url}' class="alert-link">({entity_type} ID: {pk}, VERSION ID:{history} )</a>""".format(entity_type=checks['entity_type'],
            url=reverse('generic_entity_history_detail', args=(pk,entity_history_id)),
            pk=pk,history=entity_history_id)

        return data





def checkEntityToPublish(request,pk,entity_history_id):
    '''
        Allow to publish if:
        - workingset is not deleted
        - user is an owner
        - Workingset contains codes
        - all conceots are published
        @param request: user request object
        @param pk: workingset id
        @param entity_history_id: historical id of workingset
        @return: dictionary containing all conditions to publish
    '''
    allow_to_publish = True
    workingset_is_deleted = False
    is_owner = True
    is_moderator = False
    is_latest_pending_version = False

    if (GenericEntity.objects.get(id=pk).is_deleted == True):
        allow_to_publish = False
        workingset_is_deleted = True

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

    #check if current version of ws is the latest version to approve
    if len(PublishedGenericEntity.objects.filter(entity_id=pk, entity_history_id=entity_history_id, approval_status=1)) > 0:
        is_latest_pending_version = True


    entity_ver = GenericEntity.history.get(id=pk, history_id=entity_history_id)
    is_published = checkIfPublished(GenericEntity, pk, entity_history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, entity_history_id)
    is_lastapproved = len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=2)) > 0
    other_pending = len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=1)) > 0
    

    # get historical version by querying SQL command from DB
    entity = generic_entity_db_utils.get_historical_entity(entity_history_id
                                            , highlight_result = [False, True][generic_entity_db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = generic_entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))  
                                            )
                                                                                                            
                                                                   

    if entity['layout']== 1 or entity['layout']== 3:
         has_childs, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors = \
        checkChildren(request,generic_entity_db_utils.get_historical_entity(entity_history_id))
    else:
        has_childs, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors = \
        checkChildConcept(request,entity_history_id)
    
   

    if not isOK:
        allow_to_publish = False

    #check if table is not empty
    table_ofEntity = lambda entity_type:  'concept_informations' if entity_type==1  else 'workingset_concept_informations'
    entity_has_data = len(GenericEntity.history.get(id=pk, history_id=entity_history_id).template_data[table_ofEntity(entity['layout'])]) > 0
    entity_type = ENTITY_LAYOUT[entity['layout']-1][1]
    if not entity_has_data and entity['layout'] == 3:
        allow_to_publish = False


    checks = {
        'entity': entity,
        'entity_type': entity_type,
        'name': entity_ver.name,
        'errors':errors,
        'allowed_to_publish':allow_to_publish,
        'entity_is_deleted':workingset_is_deleted,
        'is_owner':is_owner,
        'is_moderator':is_moderator,
        'approval_status': approval_status,
        'is_lastapproved': is_lastapproved,
        'other_pending':other_pending,
        'entity_has_data':entity_has_data,
        'is_published': is_published,
        'is_latest_pending_version':is_latest_pending_version,
        'is_allowed_view_children':is_allowed_view_children,#to see if child phenotypes of ws is not deleted/not published etc
        'all_are_published':all_are_published,
        'all_not_deleted':all_not_deleted
    }
    return checks

def checkChildren(request,entity):
        """
        Check if workingset child data is validated
        @param request: user request object
        @param workingset_history_id: historical id ws
        @return: collection of boolean conditions
        """

        if entity['layout'] == 1:
            name_table = 'concept_informations'
            child_id = 'concept_id'
            child_version_id = 'concept_version_id'
            name_child = 'concept'
        elif entity['layout'] == 3:
            name_table = 'workingset_concept_informations'
            child_id = 'phenotype_id'
            child_version_id = 'phenotype_version_id'
            name_child = 'phenotype'
        


        if len(entity['template_data'][name_table]) == 0:
            has_child_entitys = False
            child_entitys_versions = ''
        else:
            child_entitys_versions = [(x[child_id], x[child_version_id]) for x in entity['template_data'][name_table]]

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
            isDeleted = (Concept.objects.filter(Q(id=p[0])).exclude(is_deleted=True).count() == 0) if entity['layout'] == 1 else (GenericEntity.objects.filter(Q(id=p[0])).exclude(is_deleted=True).count() == 0) 
            if isDeleted:
                errors[p[0]] = 'Child ' + name_child + '(' + str(p[0]) + ') is deleted'
                all_not_deleted = False


        for p in child_entitys_versions:
            is_published = checkIfPublished(Concept, p[0], p[1]) if entity['layout'] == 1 else checkIfPublished(GenericEntity, p[0], p[1])
            if not is_published:
                errors[str(p[0]) + '/' + str(p[1])] = 'Child ' + name_child + '(' + str(p[0]) + '/' + str(p[1]) + ') is not published'
                all_are_published = False


        for p in child_entitys_versions:
            permitted = allowed_to_view(request,
                                        Concept,
                                        set_id=p[0],
                                        set_history_id=p[1]) if entity['layout'] == 1 else allowed_to_view(request,
                                                                                                        GenericEntity,
                                                                                                        set_id=p[0],
                                                                                                        set_history_id=p[1])

            if not permitted:
                errors[str(p[0]) + '_view'] = 'Child ' + name_child + '(' + str(p[0]) + ') is not permitted.'
                is_allowed_view_children = False

        isOK = (all_not_deleted and all_are_published and is_allowed_view_children)

        return  has_child_entitys,isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors


def send_email_decision_entity(entity,entity_type,approved):
    """
    Call util function to send email decision
    @param workingset: workingset object
    @param approved: approved status flag
    """
    
    if approved == 1:
        db_utils.send_review_email(entity,
                                   "Published",
                                   f"{entity_type} has been successfully approved and published on the website")

    elif approved == 2:
        # This line for the case when user want to get notification of same workingset id but different version
        db_utils.send_review_email(entity,
                                   "Published",
                                   f"{entity_type} has been successfully approved and published on the website")
    elif approved == 3:
        db_utils.send_review_email(entity,
                                   "Rejected",
                                   f"{entity_type} has been rejected by the moderator. Please consider update changes and try again")

    """"
        Get history table data for the template
        @param request: user request object
        @param pk: workingset id for database query
        @return: return historical table data to generate table context
    """

    versions = GenericEntity.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = generic_entity_db_utils.get_historical_entity(v.history_id
                                            , highlight_result = [False, True][generic_entity_db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = generic_entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))  
                                            )

        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        ver['updated_by'] = None
        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(GenericEntity, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedGenericEntity.objects.get(q=ver['id'],
                                                                  entity_history_id=ver['history_id'],
                                                                  approval_status=2).created
        else:
            ver['publish_date'] = None

        ver['approval_status'] = -1
        ver['approval_status_label'] = ''
        if PublishedGenericEntity.objects.filter(entity_id=ver['id'],
                                              entity_history_id=ver['history_id']).exists():
            ver['approval_status'] = PublishedGenericEntity.objects.get(entity_id=ver['id'], entity_history_id=ver[
                'history_id']).approval_status
            ver['approval_status_label'] = APPROVED_STATUS[ver['approval_status']][1]

        if request.user.is_authenticated:
            if allowed_to_edit(request, GenericEntity, pk) or allowed_to_view(request, GenericEntity, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)

    return historical_versions