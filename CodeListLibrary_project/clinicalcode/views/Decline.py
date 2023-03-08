

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

class EntityDecline(LoginRequiredMixin, HasAccessToViewGenericEntityCheckMixin, TemplateResponseMixin, View):
    '''
        Decline the current working set.
    '''

    model = GenericEntity
    #use same template as we have two buttons publish and decline
    template_name = 'clinicalcode/generic_entity/publish.html'


    
    def post(self, request, pk, history_id):
        """
        Send request to server to  decline entity
        @param request: user request object
        @param pk: entity id for database query
        @param history_id: historical id entity
        @return: JSON response to the page
        """
        is_published = checkIfPublished(GenericEntity, pk, history_id)
        checks = utils_ge_validator.checkEntityToPublish(request, pk, history_id)
        if not is_published:
            checks = utils_ge_validator.checkEntityToPublish(request, pk, history_id)

        data = dict()

        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {},
                                               self.request)
            return JsonResponse(data)

        try:
            # start a transaction
            with transaction.atomic():
                entity = GenericEntity.objects.get(pk=pk)
                #if moderator and in pending state
                if checks['is_moderator'] and checks['approval_status'] == 1:
                    published_entity = PublishedGenericEntity.objects.filter(entity_id=entity.id, approval_status=1).first()#find first record
                    published_entity.approval_status = 3
                    published_entity.save()
                    data['form_is_valid'] = True
                    data['approval_status'] = 3

                    data = utils_ge_validator.form_validation(request, data, history_id, pk, entity, checks)
                    



        except Exception as e:
            print(e)
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {},
                                               self.request)

        return JsonResponse(data)

