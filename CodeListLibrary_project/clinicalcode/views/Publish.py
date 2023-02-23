import csv
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
# from django.contrib.messages import constants
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import EmptyPage, Paginator
# from django.db.models import Q
from django.db import transaction  # , models, IntegrityError
# from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.templatetags.static import static
# from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .. import generic_entity_db_utils, utils
from ..models.Brand import Brand
from ..models.CodingSystem import CodingSystem
from ..models.DataSource import DataSource
from ..models.Phenotype import Phenotype
from ..models.PublishedPhenotype import PublishedPhenotype
from ..models.Tag import Tag
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.constants import *
from django.db.models.functions import Lower

from django.utils.timezone import make_aware

# from rest_framework.permissions import BasePermission

class Publish(LoginRequiredMixin, HasAccessToViewPhenotypeWorkingsetCheckMixin, TemplateResponseMixin, View):
    
    model = GenericEntity
    template_name = 'clinicalcode/ge/publish.html'


    def get(self, request, pk, entity_history_id):
        """
        Get method to generate modal response and pass additional information about working set
        @param request: user request object
        @param pk: workingset id for database query
        @param workingset_history_id: historical workingset id from database
        @return: render response object to generate on template
        """
        checks = utils_ge_validator.checkEntityTobePublished(self.request, pk, entity_history_id)

        if not checks['is_published']:
            checks = utils_ge_validator.checkEntityTobePublished(self.request, pk, entity_history_id)

        # --------------------------------------------
        return self.render_to_response({
            'workingset': checks['workingset'],
            'name': checks['name'],
            'workingset_history_id': entity_history_id,
            'is_published': checks['is_published'],
            'allowed_to_publish': checks['allowed_to_publish'],
            'is_owner': checks['is_owner'],
            'workingset_is_deleted': checks['workingset_is_deleted'],
            'approval_status': checks['approval_status'],
            'is_lastapproved': checks['is_lastapproved'],
            'is_latest_pending_version': checks['is_latest_pending_version'], # check if it is latest to approve
            'is_moderator': checks['is_moderator'],
            'workingset_has_data': checks['workingset_has_data'],#check if table exists to publish ws
            'is_allowed_view_children': checks['is_allowed_view_children'],
            'all_are_published': checks['all_are_published'],#see if rest of the phenotypes is published already
            'other_pending':checks['other_pending'],#data if other pending ws
            'all_not_deleted': checks['all_not_deleted'],# check if phenotypes is not deleted
            'errors':checks['errors']
        })

    def post(self, request, pk, entity_history_id):
        """
        Post data containing current state of workingset to backend (published/declined/pending)
        @param request: request user object
        @param pk:workingset id for database query
        @param workingset_history_id: historical id of workingset
        @return: JsonResponse and status message
        """
        is_published = checkIfPublished(PhenotypeWorkingset, pk, entity_history_id)
        checks = workingset_db_utils.checkWorkingsetTobePublished(request, pk, entity_history_id)
        if not is_published:
            checks = workingset_db_utils.checkWorkingsetTobePublished(request, pk, entity_history_id)

        data = dict()

        #check if workingset could be published if not show error
        if not checks['allowed_to_publish'] or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {},
                                               self.request)
            return JsonResponse(data)

        try:
            if self.condition_to_publish(checks, is_published):
                    # start a transaction
                    with transaction.atomic():
                        workingset = PhenotypeWorkingset.objects.get(pk=pk)


                        #Check if moderator first and if was already approved to filter by only approved workingsets
                        if checks['is_moderator']:
                            if checks['is_lastapproved']:
                                published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id,
                                                                                          approval_status=2).first()
                                published_workingset = PublishedWorkingset(workingset=workingset,
                                                                           workingset_history_id=entity_history_id,
                                                                           moderator_id=published_workingset.moderator.id,
                                                                           created_by_id=request.user.id)
                                published_workingset.approval_status = 2
                                published_workingset.save()
                            else:
                                published_workingset = PublishedWorkingset(workingset=workingset, workingset_history_id=entity_history_id,moderator_id = request.user.id,
                                                                        created_by_id=PhenotypeWorkingset.objects.get(pk=pk).created_by.id)
                                published_workingset.approval_status = 2
                                published_workingset.save()



                        #Check if was already published by user only to filter workingsets and take the moderator id
                        if checks['is_lastapproved'] and not checks['is_moderator']:
                            published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id, approval_status=2).first()
                            published_workingset = PublishedWorkingset(workingset = workingset,workingset_history_id=workingset_history_id,moderator_id=published_workingset.moderator.id,created_by_id=request.user.id)
                            published_workingset.approval_status = 2
                            published_workingset.save()


                        #Approve other pending workingset if available to publish
                        if checks['other_pending']:
                            published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id,
                                                                                      approval_status=1)
                            for ws in published_workingset:
                                ws.approval_status = 2
                                ws.moderator_id = request.user.id
                                ws.save()

                        data['form_is_valid'] = True
                        data['approval_status'] = 2
                        #show state message to the client side and send email
                        data = form_validation(request, data, workingset_history_id, pk, workingset,checks)

            #check if moderator and current workingset is in pending state
            elif checks['approval_status'] == 1 and checks['is_moderator']:
                    with transaction.atomic():
                        workingset = PhenotypeWorkingset.objects.get(pk=pk)
                        published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id,
                                                                                  approval_status=1)
                        #filter and publish all pending ws
                        for ws in published_workingset:
                            ws.approval_status = 2
                            ws.moderator_id = request.user.id
                            ws.save()

                        data['approval_status'] = 2
                        data['form_is_valid'] = True
                        data = form_validation(request, data, entity_history_id, pk, workingset, checks)

            #check if workingset declined and user is moderator to review again
            elif checks['approval_status'] == 3 and checks['is_moderator']:
                with transaction.atomic():
                    workingset = PhenotypeWorkingset.objects.get(pk=pk)

                    #filter by declined ws
                    published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id,
                                                                              entity_history_id=entity_history_id,approval_status=3).first()
                    published_workingset.approval_status = 2
                    published_workingset.moderator_id=request.user.id
                    published_workingset.save()

                    #check if other pending exist to approve this ws automatically
                    if checks['other_pending']:
                        published_workingset = PublishedWorkingset.objects.filter(workingset_id=workingset.id,
                                                                                  approval_status=1)
                        for ws in published_workingset:
                            ws.approval_status = 2
                            ws.moderator_id = request.user.id
                            ws.save()


                    data['approval_status'] = 2
                    data['form_is_valid'] = True
                    #send message to the client
                    data = form_validation(request, data, entity_history_id, pk, workingset, checks)




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
        @param checks: workingset conditional from util function
        @param is_published: if already published
        @return: return True if this condition satisfies

        if (ws is allowed to publish by default , approval not exist in database ) OR (ws approved but not yet published) = True
        """

        if (checks['allowed_to_publish'] and not is_published and checks['approval_status'] is None) or\
                (checks['approval_status'] == 2 and not is_published):
            return True
