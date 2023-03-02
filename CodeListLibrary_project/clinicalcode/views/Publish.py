
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
# from django.contrib.messages import constants
# from django.db.models import Q
from django.db import transaction  # , models, IntegrityError
# from django.forms.models import model_to_dict
from django.http.response import JsonResponse
from django.template.loader import render_to_string
# from django.core.urlresolvers import reverse_lazy, reverse
from django.views.generic.base import TemplateResponseMixin, View

from ..view_utils import utils_ge_validator
from ..permissions import *
from .View import *
from clinicalcode.constants import *


# from rest_framework.permissions import BasePermission

class Publish(LoginRequiredMixin, HasAccessToViewPhenotypeWorkingsetCheckMixin, TemplateResponseMixin, View):
    
    model = GenericEntity
    template_name = 'clinicalcode/generic_entity/publish.html'


    def get(self, pk, entity_history_id):
        """
        Get method to generate modal response and pass additional information about working set
        @param request: user request object
        @param pk: entity id for database query
        @param entity_history_id: historical entity id from database
        @return: render response object to generate on template
        """
        checks = utils_ge_validator.checkEntityTocheck(self.request, pk, entity_history_id)

        if not checks['is_published']:
            checks = utils_ge_validator.checkEntityTocheck(self.request, pk, entity_history_id)

        # --------------------------------------------
        return self.render_to_response({
            'entity': checks['entity'],
            'name': checks['name'],
            'entity_history_id': entity_history_id,
            'is_published': checks['is_published'],
            'allowed_to_publish': checks['allowed_to_publish'],
            'is_owner': checks['is_owner'],
            'entity_is_deleted': checks['entity_is_deleted'],
            'approval_status': checks['approval_status'],
            'is_lastapproved': checks['is_lastapproved'],
            'is_latest_pending_version': checks['is_latest_pending_version'], # check if it is latest to approve
            'is_moderator': checks['is_moderator'],
            'entity_has_data': checks['entity_has_data'],#check if table exists to publish ws
            'is_allowed_view_children': checks['is_allowed_view_children'],
            'all_are_published': checks['all_are_published'],#see if rest of the phenotypes is published already
            'other_pending':checks['other_pending'],#data if other pending ws
            'all_not_deleted': checks['all_not_deleted'],# check if phenotypes is not deleted
            'errors':checks['errors']
        })

    def post(self, request, pk, entity_history_id):
        """
        Post data containing current state of entity to backend (published/declined/pending)
        @param request: request user object
        @param pk:entity id for database query
        @param entity_history_id: historical id of entity
        @return: JsonResponse and status message
        """
        is_published = checkIfPublished(GenericEntity, pk, entity_history_id)
        checks = utils_ge_validator.checkEntityTocheck(request, pk, entity_history_id)
        if not is_published:
            checks = utils_ge_validator.checkEntityTocheck(request, pk, entity_history_id)

        data = dict()

        #check if entity could be published if not show error
        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {},
                                               request)
            return JsonResponse(data)

        try:
            if self.condition_to_publish(checks, is_published):
                    # start a transaction
                    with transaction.atomic():
                        entity = GenericEntity.objects.get(pk=pk)


                        #Check if moderator first and if was already approved to filter by only approved entitys
                        if checks['is_moderator']:
                            if checks['is_lastapproved']:
                                published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                                          approval_status=2).first()
                                published_entity = PublishedGenericEntity(entity=entity,
                                                                           entity_history_id=entity_history_id,
                                                                           moderator_id=published_entity.moderator.id,
                                                                           created_by_id=request.user.id)
                                published_entity.approval_status = 2
                                published_entity.save()
                            else:
                                published_entity = PublishedGenericEntity(entity=entity, entity_history_id=entity_history_id,moderator_id = request.user.id,
                                                                        created_by_id=GenericEntity.objects.get(pk=pk).created_by.id)
                                published_entity.approval_status = 2
                                published_entity.save()



                        #Check if was already published by user only to filter entitys and take the moderator id
                        if checks['is_lastapproved'] and not checks['is_moderator']:
                            published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id, approval_status=2).first()
                            published_entity = PublishedGenericEntity(entity = entity,entity_history_id=entity_history_id,moderator_id=published_entity.moderator.id,created_by_id=request.user.id)
                            published_entity.approval_status = 2
                            published_entity.save()


                        #Approve other pending entity if available to publish
                        if checks['other_pending']:
                            published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                                      approval_status=1)
                            for en in published_entity:
                                en.approval_status = 2
                                en.moderator_id = request.user.id
                                en.save()

                        data['form_is_valid'] = True
                        data['approval_status'] = 2
                        #show state message to the client side and send email
                        data = utils_ge_validator.form_validation(request, data, entity_history_id, pk, entity,checks)

            #check if moderator and current entity is in pending state
            elif checks['approval_status'] == 1 and checks['is_moderator']:
                    with transaction.atomic():
                        entity = GenericEntity.objects.get(pk=pk)
                        published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                                  approval_status=1)
                        #filter and publish all pending ws
                        for en in published_entity:
                            en.approval_status = 2
                            en.moderator_id = request.user.id
                            en.save()

                        data['approval_status'] = 2
                        data['form_is_valid'] = True
                        data = utils_ge_validator.form_validation(request, data, entity_history_id, pk, entity, checks)

            #check if entity declined and user is moderator to review again
            elif checks['approval_status'] == 3 and checks['is_moderator']:
                with transaction.atomic():
                    entity = GenericEntity.objects.get(pk=pk)
                    

                    #filter by declined ws
                    published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                              entity_history_id=entity_history_id,approval_status=3).first()
                    published_entity.approval_status = 2
                    published_entity.moderator_id=request.user.id
                    published_entity.save()

                    #check if other pending exist to approve this ws automatically
                    if checks['other_pending']:
                        published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id,
                                                                                  approval_status=1)
                        for en in published_entity:
                            en.approval_status = 2
                            en.moderator_id = request.user.id
                            en.save()


                    data['approval_status'] = 2
                    data['form_is_valid'] = True
                    #send message to the client
                    data = utils_ge_validator.form_validation(request, data, entity_history_id, pk, entity, checks)




        except Exception as e:
            print(e)
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {},
                                               request)

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
                (checks['approval_status'] == 2 and not is_published):
            return True
