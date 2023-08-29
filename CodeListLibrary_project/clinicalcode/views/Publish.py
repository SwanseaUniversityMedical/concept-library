
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic.base import TemplateResponseMixin, View
from django.utils.decorators import method_decorator
from ..entity_utils import publish_utils, permission_utils, constants
from ..permissions import *
from .View import *


class Publish(LoginRequiredMixin, permission_utils.HasAccessToViewGenericEntityCheckMixin, TemplateResponseMixin, View):
    model = GenericEntity
    template_name = 'clinicalcode/generic_entity/publish/publish.html'

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self,request, pk, history_id):
        """
        Get method to generate modal response and pass additional information about working set
        @param request: user request object
        @param pk: entity id for database query
        @param entity_history_id: historical entity id from database
        @return: render response object to generate on template
        """
        checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)

        if not checks['is_published']:
            checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)
        
        checks['entity_history_id'] = history_id
        checks['entity_id'] = pk
        # --------------------------------------------
        return JsonResponse(checks, safe=False)

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def post(self,request,pk, history_id):
        """
        Post data containing current state of entity to backend (published/declined/pending)
        @param request: request user object
        @param pk:entity id for database query
        @param entity_history_id: historical id of entity
        @return: JsonResponse and status message
        """
        is_published = checkIfPublished(GenericEntity, pk, history_id)
        checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)
        # if not is_published:
        #     checks = publish_utils.check_entity_to_publish(request, pk, history_id)

        data = dict()

        #check if entity could be published if not show error
        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)
            return JsonResponse(data)

        try:
            if self.condition_to_publish(checks, is_published):
                # start a transaction
                with transaction.atomic():
                    entity = GenericEntity.objects.get(pk=pk)

                    #Check if moderator first and if was already approved to filter by only approved entitys
                    if checks['is_moderator']:
                        if checks['is_lastapproved']:
                            self.last_approved_publish(self.request,entity,history_id)
                        else:
                            self.moderator_publish(self.request,history_id,pk,checks,data)
                    
                    if checks['is_publisher']:
                        published_entity = PublishedGenericEntity(entity=entity,entity_history_id=history_id, moderator_id=request.user.id,
                                                        created_by_id=GenericEntity.objects.get(pk=pk).created_by.id,approval_status=constants.APPROVAL_STATUS.APPROVED)
                        published_entity.save()
                            
                    #Check if was already published by user only to filter entitys and take the moderator id
                    if checks['is_lastapproved'] and not checks['is_moderator'] and not checks['is_publisher']:
                        self.last_approved_publish(self.request,entity,history_id)

                    #Approve other pending entity if available to publish
                    if checks['other_pending']:
                        published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                                    approval_status=constants.APPROVAL_STATUS.PENDING)
                        for en in published_entity:
                            en.approval_status = constants.APPROVAL_STATUS.APPROVED
                            en.moderator_id = self.request.user.id
                            en.save()

                    data['form_is_valid'] = True
                    data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
                    #show state message to the client side and send email
                    data = publish_utils.form_validation(self.request, data, history_id, pk, entity,checks)

            #check if moderator and current entity is in pending state
            elif checks['approval_status'] == constants.APPROVAL_STATUS.PENDING and checks['is_moderator']:
                with transaction.atomic():
                    self.moderator_publish(self.request,history_id,pk,checks,data)

            #check if entity declined and user is moderator to review again
            elif checks['approval_status'] == constants.APPROVAL_STATUS.REJECTED and checks['is_moderator']:
                with transaction.atomic():
                    self.moderator_publish(self.request,history_id,pk,checks,data)

        except Exception as e:
            print(e)
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {},
                                               self.request)

        return JsonResponse(data)

    def condition_to_publish(self,checks,is_published):
        """
        Additonal conditional to publish in the view
        @param checks: entity conditional from util function
        @param is_published: if already published
        @return: return True if this condition satisfies

        if (ws is allowed to publish by default , approval not exist in database ) OR (ws approved but not yet published) = True
        """

        if (checks['allowed_to_publish'] and not is_published and checks['approval_status'] is None) or\
                (checks['approval_status'] == constants.APPROVAL_STATUS.APPROVED and not is_published):
            return True
    

    def moderator_publish(self,request,history_id,pk,conditions,data):  
        entity = GenericEntity.objects.get(pk=pk) 
        if conditions['approval_status'] == constants.APPROVAL_STATUS.PENDING:
            published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                        approval_status=constants.APPROVAL_STATUS.PENDING)
            #filter and publish all pending ws
            for en in published_entity:
                en.approval_status = constants.APPROVAL_STATUS.APPROVED
                en.moderator_id = request.user.id
                en.save()

            data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
            data['form_is_valid'] = True
            data = publish_utils.form_validation(request, data, history_id, pk, entity, conditions)

        elif conditions['approval_status'] == constants.APPROVAL_STATUS.REJECTED:
            #filter by declined ws
            published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                        entity_history_id=history_id,
                                                                        approval_status=constants.APPROVAL_STATUS.REJECTED
                                                                        ).first()
            published_entity.approval_status = constants.APPROVAL_STATUS.APPROVED
            published_entity.moderator_id=request.user.id
            published_entity.save()

            #check if other pending exist to approve this ws automatically
            if conditions['other_pending']:
                published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                            approval_status=constants.APPROVAL_STATUS.PENDING)
                for en in published_entity:
                    en.approval_status = constants.APPROVAL_STATUS.APPROVED
                    en.moderator_id = request.user.id
                    en.save()

            data['approval_status'] = constants.APPROVAL_STATUS.APPROVED
            data['form_is_valid'] = True
            #send message to the client
            data = publish_utils.form_validation(request, data, history_id, pk, entity, conditions)

        else:
            published_entity = PublishedGenericEntity(entity=entity,entity_history_id=history_id, moderator_id=request.user.id,
                                                        created_by_id=GenericEntity.objects.get(pk=pk).created_by.id,approval_status=constants.APPROVAL_STATUS.APPROVED)
            
            published_entity.save()
            
    def last_approved_publish(self,request,entity,history_id):
            last_moderated = PublishedGenericEntity.objects.filter(entity_id=entity.id,approval_status=constants.APPROVAL_STATUS.APPROVED).first()

            published_entity = PublishedGenericEntity(entity=entity,
                                                        entity_history_id=history_id,
                                                        moderator_id=last_moderated.moderator.id,
                                                        created_by_id=request.user.id,
                                                        approval_status=constants.APPROVAL_STATUS.APPROVED)
            published_entity.save()

class RequestPublish(LoginRequiredMixin, permission_utils.HasAccessToViewGenericEntityCheckMixin, TemplateResponseMixin, View):
    '''
        User request to publish entity
    '''
    model = GenericEntity
    template_name = 'clinicalcode/generic_entity/publish/request_publish.html'

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, pk, history_id):
        """
        Get method to generate the modal window template to submit entity
        @param request: user request object
        @param pk: entity id for database query
        @param entity_history_id: historical entity id
        @return: render the modal to user with an appropriate information
        """
        #get additional checks in case if ws is deleted/approved etc
        checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)
        checks['entity_history_id'] = history_id
        checks['entity_id'] = pk

        return JsonResponse(checks, safe=False)
    
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def post(self,request, pk, history_id):
        """
        Send the request to publish data to the server
        @param request: user request object
        @param pk: entity id for database query
        @param history_id: historical id of entity
        @return: JSON success body response
        """
        is_published = checkIfPublished(GenericEntity, pk, history_id)
        checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)
        if not is_published:
            checks = publish_utils.check_entity_to_publish(self.request, pk, history_id)

        data = dict()
        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {}, self.request)
            return JsonResponse(data)

        try:
            # (allowed to permit) AND (ws not published) AND (approval_status not in database) AND (user not moderator)
            if checks['allowed_to_publish'] and not is_published and checks['approval_status'] is None and not checks['is_moderator']:
                    # start a transaction
                    with transaction.atomic():
                        entity = GenericEntity.objects.get(pk=pk)
                        published_entity = PublishedGenericEntity(entity=entity, entity_history_id=history_id,
                                                                    created_by_id=self.request.user.id,approval_status=constants.APPROVAL_STATUS.PENDING)
                        published_entity.save()
                        data['form_is_valid'] = True
                        data['approval_status'] = constants.APPROVAL_STATUS.PENDING
                        data = publish_utils.form_validation(self.request, data, history_id, pk, entity, checks)


        except Exception as e:
            print(e)
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {},
                                               self.request)

        return JsonResponse(data)
