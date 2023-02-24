from clinicalcode import urls_generic_entity


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
                list(PublishedWorkingset.objects.filter(entity_id=pk, approval_status=2).values_list('entity_history_id', flat=True))
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
    elif len(PublishedWorkingset.objects.filter(workingset=PhenotypeWorkingset.objects.get(pk=pk).id, approval_status=2)) > 0 and not data['approval_status'] == 3:
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



def send_email_decision_entity(entity, approved):
    """
    Call util function to send email decision
    @param workingset: workingset object
    @param approved: approved status flag
    """
    
    if approved == 1:
        urls_generic_entity.send_review_email(entity,
                                   "Published",
                                   "Workingset has been successfully approved and published on the website")

    elif approved == 2:
        # This line for the case when user want to get notification of same workingset id but different version
        urls_generic_entity.send_review_email(entity,
                                   "Published",
                                   "Workingset has been successfully approved and published on the website")
    elif approved == 3:
        urls_generic_entity.send_review_email(entity,
                                   "Rejected",
                                   "Workingset has been rejected by the moderator. Please consider update changes and try again")
