from clinicalcode import generic_entity_db_utils
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity


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
        'clinicalcode/phenotypeworkingset/partial_history_list.html',
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

def send_message( pk, data, entity,entity_history_id,checks):
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
        data['message'] = """The entity version has been successfully published.
                         <a href='{url}' class="alert-link">(WORKINGSET ID: {pk}, VERSION ID:{history} )</a>""".format(url=reverse('phenotypeworkingset_history_detail', args=(pk,workingset_history_id)), pk=pk,history=workingset_history_id)

        send_email_decision_workingset(workingset, data['approval_status'])
        return data

    #publish message if not declined
    elif len(PublishedGenericEntity.objects.filter(workingset=PhenotypeWorkingset.objects.get(pk=pk).id, approval_status=2)) > 0 and not data['approval_status'] == 3:
        data['message'] = """The workingset version has been successfully published.
                                 <a href='{url}' class="alert-link">(WORKINGSET ID: {pk}, VERSION ID:{history} )</a>""".format(url=reverse('phenotypeworkingset_history_detail', args=(pk,workingset_history_id)),
                                                                                                         pk=pk,history=workingset_history_id)
        send_email_decision_workingset(workingset, data['approval_status'])

        return data

    #showing rejected message
    elif data['approval_status'] == 3:
        data['message'] = """The workingset version has been rejected .
                                               <a href='{url}' class="alert-link">(WORKINGSET ID: {pk}, VERSION ID:{history} )</a>""".format(
            url=reverse('phenotypeworkingset_history_detail', args=(pk,workingset_history_id)),
            pk=pk,history=workingset_history_id)
        send_email_decision_workingset(workingset, data['approval_status'])

        return data

    # ws is approved by moderator if moderator approved different version
    elif data['approval_status'] is None and checks['is_moderator']:
        data['message'] = """The workingset version has been successfully published.
                                                <a href='{url}' class="alert-link">(WORKINGSET ID: {pk}, VERSION ID:{history} )</a>""".format(
            url=reverse('phenotypeworkingset_history_detail', args=(pk,workingset_history_id)),
            pk=pk,history=workingset_history_id)

        return data


    #show pending message if user clicks to request review
    elif data['approval_status'] == 1:
        data['message'] = """The workingset version is going to be reviewed by the moderator.
                                                      <a href='{url}' class="alert-link">(WORKINGSET ID: {pk}, VERSION ID:{history} )</a>""".format(
            url=reverse('phenotypeworkingset_history_detail', args=(pk,workingset_history_id)),
            pk=pk,history=workingset_history_id)

        return data


def checkEntityTocheck(request,pk,history_id):
    entity = GenericEntity.objects.get(id=pk,history_id=history_id)

    if entity.layout == 1:
        return checkPhenotypeTobePublished(request,pk,history_id)
    elif entity.layout == 2:
        return checkConceptTobePublished(request,pk,history_id)
    elif entity.layout == 3:
        return checkWorkingsetTobePublished(request,pk,history_id)


def checkWorkingsetTobePublished(request,pk,workingset_history_id):
    '''
        Allow to publish if:
        - workingset is not deleted
        - user is an owner
        - Workingset contains codes
        - all conceots are published
        @param request: user request object
        @param pk: workingset id
        @param workingset_history_id: historical id of workingset
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
    if len(PublishedGenericEntity.objects.filter(workingset_id=pk, workingset_history_id=workingset_history_id, approval_status=1)) > 0:
        is_latest_pending_version = True


    workingset_ver = GenericEntity.history.get(id=pk, history_id=workingset_history_id)
    is_published = checkIfPublished(GenericEntity, pk, workingset_history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, workingset_history_id)
    is_lastapproved = len(PublishedGenericEntity.objects.filter(workingset=GenericEntity.objects.get(pk=pk).id, approval_status=2)) > 0
    other_pending = len(PublishedGenericEntity.objects.filter(workingset=GenericEntity.objects.get(pk=pk).id, approval_status=1)) > 0

    # get historical version by querying SQL command from DB
    workingset = getHistoryGenericEntity(workingset_history_id,
                                                                   highlight_result=[False, True][
                                                                       generic_entity_db_utils.is_referred_from_search_page(request)],
                                                                   q_highlight=generic_entity_db_utils.get_q_highlight(request,
                                                                                                        request.session.get(
                                                                                                            'ph_workingset_search',
                                                                                                            ''))
                                                                   )
    has_child_phenenotypes, isOK, all_not_deleted, all_are_published, is_allowed_view_children, errors = \
        checkAllChildData4Publish_Historical(request,workingset_history_id)

    if not isOK:
        allow_to_publish = False

    #check if table is not empty
    workingset_has_data = len(GenericEntity.history.get(id=pk, history_id=workingset_history_id).phenotypes_concepts_data) > 0
    if not workingset_has_data:
        allow_to_publish = False


    checks = {
        'workingset': workingset,
        'name': workingset_ver.name,
        'errors':errors,
        'allowed_to_publish':allow_to_publish,
        'workingset_is_deleted':workingset_is_deleted,
        'is_owner':is_owner,
        'is_moderator':is_moderator,
        'approval_status': approval_status,
        'is_lastapproved': is_lastapproved,
        'other_pending':other_pending,
        'workingset_has_data':workingset_has_data,
        'is_published': is_published,
        'is_latest_pending_version':is_latest_pending_version,
        'is_allowed_view_children':is_allowed_view_children,#to see if child phenotypes of ws is not deleted/not published etc
        'all_are_published':all_are_published,
        'all_not_deleted':all_not_deleted
    }
    return checks

def send_email_decision_entity(entity, approved):
    """
    Call util function to send email decision
    @param workingset: workingset object
    @param approved: approved status flag
    """
    
    if approved == 1:
        generic_entity_db_utils.send_review_email(entity,
                                   "Published",
                                   "Workingset has been successfully approved and published on the website")

    elif approved == 2:
        # This line for the case when user want to get notification of same workingset id but different version
        generic_entity_db_utils.send_review_email(entity,
                                   "Published",
                                   "Workingset has been successfully approved and published on the website")
    elif approved == 3:
        generic_entity_db_utils.send_review_email(entity,
                                   "Rejected",
                                   "Workingset has been rejected by the moderator. Please consider update changes and try again")
