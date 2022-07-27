'''
    ---------------------------------------------------------------------------
    CONCEPT VIEW
    
    View-handling for the Concepts.
    ---------------------------------------------------------------------------
'''
import csv
import sys
import time
from _ast import Or
import datetime
import re

from clinicalcode.permissions import allowed_to_view
# from django.contrib.auth.models import User
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction  # , models, IntegrityError
from django.db.models.aggregates import Max
from django.http import HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http import HttpResponseNotFound, response
from django.http.response import Http404, HttpResponse, JsonResponse
from django.template.context_processors import request
from django.template.loader import render_to_string
#from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now, make_aware
from django.views.defaults import permission_denied
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView  # , DeleteView
from simple_history.models import HistoricalRecords

from .. import db_utils, utils
from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models.Brand import Brand
from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.CodeRegex import CodeRegex
from ..models.CodingSystem import CodingSystem
from ..models.PublishedConcept import PublishedConcept
from ..models.Tag import Tag
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand

logger = logging.getLogger(__name__)

import json
from collections import OrderedDict

import numpy as np
import pandas as pd
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe  # , SafeData, SafeString

'''
COM_TYPE_CONCEPT_DESC = 'Concept'
COM_TYPE_QUERY_BUILDER_DESC = 'Query builder'
COM_TYPE_EXPRESSION_DESC = 'Match code with expression'
COM_TYPE_EXPRESSION_SELECT_DESC = 'Select codes individually + import codes'
'''

#----------- Predefs ----------------#
page_size_limits = [20, 50, 100]
#------------------------------------#

class MessageMixin(object):
    '''
        Make it easy to display notification messages when using Class Based Views.
    '''

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(MessageMixin, self).delete(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super(MessageMixin, self).form_valid(form)


class ConceptCreate(LoginRequiredMixin, HasAccessToCreateCheckMixin,
                    MessageMixin, CreateView):
    '''
        Create a concept.
    '''
    model = Concept
    form_class = ConceptForm
    template_name = 'clinicalcode/concept/form.html'

    # Sending user object to the form, to verify which fields to display/remove (depending on group)
    def get_form_kwargs(self):
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def get_success_url(self):
        if allowed_to_edit(self.request, Concept, self.object.id):
            return reverse('concept_update', args=(self.object.id, ))
        elif allowed_to_view(self.request, Concept, self.object.id):
            return reverse('concept_detail', args=(self.object.id, ))
        else:
            return reverse('concept_list')

    def form_invalid(self, form):
        context = self.get_context_data()

        tag_ids = self.request.POST.get('tagids')

        # split tag ids into list
        if tag_ids:
            new_tag_list = [int(i) for i in tag_ids.split(",")]
            context['tags'] = Tag.objects.filter(pk__in=new_tag_list)

        return self.render_to_response(context)

    def form_valid(self, form):

        with transaction.atomic():
            form.instance.created_by = self.request.user

            tag_ids = self.request.POST.get('tagids')

            # split tag ids into list
            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids.split(",")]
                form.instance.tags = new_tag_list

            # form.changeReason = "Created"
            # self.object = form.save()

            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(Concept, self.object.pk,
                                                "Created")
            # to save correctly the computed friendly_id field
            concept = Concept.objects.get(pk=self.object.pk)
            concept.history.latest().delete()
            db_utils.save_Entity_With_ChangeReason(Concept, self.object.pk,
                                                   "Created")
            # concept.changeReason = "Created"
            # concept.save()

            messages.success(self.request,
                             "Concept has been successfully created.")

        return HttpResponseRedirect(self.get_success_url())


class ConceptDelete(LoginRequiredMixin, HasAccessToEditConceptCheckMixin,
                    TemplateResponseMixin, View):
    '''
        Delete a concept.
    '''
    model = Concept
    success_url = reverse_lazy('concept_list')
    template_name = 'clinicalcode/concept/delete.html'

    def get_success_url(self):
        return reverse_lazy('concept_list')

    def get(self, request, pk):
        concept = Concept.objects.get(pk=pk)

        return self.render_to_response({'pk': pk, 'name': concept.name})

    def post(self, request, pk):
        with transaction.atomic():
            db_utils.deleteConcept(pk, request.user)
            db_utils.modify_Entity_ChangeReason(Concept, pk,
                                                "Concept has been deleted")
        messages.success(self.request,
                         "Concept has been successfully deleted.")
        return HttpResponseRedirect(self.get_success_url())


def ConceptDetail_combined(request, pk, concept_history_id=None):
    ''' 
        Display the detail of a concept at a point in time.
    '''
    # validate access for login and public site
    validate_access_to_view(request,
                            Concept,
                            pk,
                            set_history_id=concept_history_id)

    if concept_history_id is None:
        # get the latest version
        concept_history_id = int(Concept.objects.get(pk=pk).history.latest().history_id)

    is_published = checkIfPublished(Concept, pk, concept_history_id)

    # ----------------------------------------------------------------------

    concept = db_utils.getHistoryConcept(concept_history_id
                                        , highlight_result = [False, True][db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = db_utils.get_q_highlight(request, request.session.get('concept_search', ''))  
                                        )
    # The history concept contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the concept.
    if concept['owner_id'] is not None:
        concept['owner'] = User.objects.get(id=int(concept['owner_id']))

    if concept['group_id'] is not None:
        concept['group'] = Group.objects.get(id=int(concept['group_id']))

    concept_history_date = concept['history_date']
    components = db_utils.getHistoryComponents(pk, concept_history_date, check_published_child_concept=True)

    code_attribute_header = concept['code_attribute_header']

    tags = Tag.objects.filter(pk=-1)
    concept_tags = concept['tags']
    if concept_tags:
        tags = Tag.objects.filter(pk__in=concept_tags)

    #     tags =  Tag.objects.filter(pk=-1)
    #     tags_comp = db_utils.getHistoryTags(pk, concept_history_date)
    #     if tags_comp:
    #         tag_list = [i['tag_id'] for i in tags_comp if 'tag_id' in i]
    #         tags = Tag.objects.filter(pk__in=tag_list)
    # ----------------------------------------------------------------------

    if request.user.is_authenticated:
        components_permissions = build_permitted_components_list(request, pk, concept_history_id=concept_history_id)

        can_edit = (not Concept.objects.get(pk=pk).is_deleted) and allowed_to_edit(request, Concept, pk)

        user_can_export = (allowed_to_view_children(request, Concept, pk, set_history_id=concept_history_id)
                           and db_utils.chk_deleted_children(request,
                                                           Concept,
                                                           pk,
                                                           returnErrors=False,
                                                           set_history_id=concept_history_id
                                                           )
                           and not Concept.objects.get(pk=pk).is_deleted)
        user_allowed_to_create = allowed_to_create()
    else:
        can_edit = False
        user_can_export = is_published
        user_allowed_to_create = False

    publish_date = None
    if is_published:
        publish_date = PublishedConcept.objects.get(concept_id=pk, concept_history_id=concept_history_id).created

    if Concept.objects.get(pk=pk).is_deleted == True:
        messages.info(request, "This concept has been deleted.")

    is_latest_version = (int(concept_history_id) == Concept.objects.get(pk=pk).history.latest().history_id)

    # published versions
    published_historical_ids = list(PublishedConcept.objects.filter(concept_id=pk).values_list('concept_history_id', flat=True))

    # history
    other_versions = Concept.objects.get(pk=pk).history.all()
    other_historical_versions = []

    for ov in other_versions:
        ver = db_utils.getHistoryConcept(ov.history_id
                                        , highlight_result = [False, True][db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = db_utils.get_q_highlight(request, request.session.get('concept_search', ''))  
                                        )
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        if ver['modified_by_id'] is not None:
            ver['modified_by'] = User.objects.get(pk=ver['modified_by_id'])

        is_this_version_published = False
        is_this_version_published = PublishedConcept.objects.filter(concept_id=ver['id'], concept_history_id=ver['history_id']).exists()
        if is_this_version_published:
            ver['publish_date'] = PublishedConcept.objects.get(concept_id=ver['id'], concept_history_id=ver['history_id']).created
        else:
            ver['publish_date'] = None

        if request.user.is_authenticated:
            if allowed_to_edit(request, Concept, pk) or allowed_to_view(request, Concept, pk):
                other_historical_versions.append(ver)
            else:
                if is_this_version_published:
                    other_historical_versions.append(ver)
        else:
            if is_this_version_published:
                other_historical_versions.append(ver)

    # how to show codelist tab
    if request.user.is_authenticated:
        component_tab_active = "active"
        codelist_tab_active = ""
        codelist = []
        codelist_loaded = 0
    else:
        # published
        # ---------
        concept_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)
        codes_with_attributes = []
        if code_attribute_header:
            codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=pk,
                                                                                        concept_history_date=concept_history_date,
                                                                                        allCodes=concept_codes,
                                                                                        code_attribute_header=code_attribute_header)

            concept_codes = codes_with_attributes
        # ---------
        component_tab_active = ""
        codelist_tab_active = "active"
        codelist = concept_codes  # db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)
        codelist_loaded = 1

    context = {
        'concept': concept,
        'components': components,
        'tags': tags,
        'user_can_edit': can_edit,
        'allowed_to_create': user_allowed_to_create,
        'user_can_export': user_can_export,
        'history': other_historical_versions,
        'live_ver_is_deleted': Concept.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'publish_date': publish_date,
        'is_latest_version': is_latest_version,
        'current_concept_history_id': int(concept_history_id),
        'component_tab_active': component_tab_active,
        'codelist_tab_active': codelist_tab_active,
        'codelist': codelist,  # json.dumps(codelist)
        'codelist_loaded': codelist_loaded,
        'code_attribute_header': code_attribute_header,
        'page_canonical_path': get_canonical_path_by_brand(request, Concept, pk, concept_history_id),
        'q': db_utils.get_q_highlight(request, request.session.get('concept_search', '')),
        'force_highlight_result':  ['0', '1'][db_utils.is_referred_from_search_page(request)]       
    }
    if request.user.is_authenticated:
        if is_latest_version and (can_edit):
            needed_keys = [
                'user_can_view_component', 'user_can_edit_component',
                'component_error_msg_view', 'component_error_msg_edit',
                'component_concpet_version_msg', 'latest_history_id'
            ]
            context.update({k: components_permissions[k] for k in needed_keys})

    return render(request, 'clinicalcode/concept/detail_combined.html',
                  context)


class ConceptFork(LoginRequiredMixin, HasAccessToViewConceptCheckMixin,
                  HasAccessToCreateCheckMixin, TemplateResponseMixin, View):
    '''
        Fork a copy of the current version of a concept.
    '''
    model = Concept
    template_name = 'clinicalcode/concept/fork.html'

    def get(self, request, pk):
        concept = Concept.objects.get(pk=pk)
        return self.render_to_response({'pk': pk, 'name': concept.name})

    def post(self, request, pk):
        data = dict()
        try:
            # start a transaction
            with transaction.atomic():
                new_concept_id = db_utils.fork(pk, request.user)
                data['form_is_valid'] = True
                data['message'] = render_to_string(
                    'clinicalcode/concept/forked.html', {'id': new_concept_id},
                    self.request)
                db_utils.save_Entity_With_ChangeReason(
                    Concept, new_concept_id, "Forked from concept %s" % pk)
        except Exception as e:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {},
                                               self.request)
        return JsonResponse(data)


class ConceptRestore(LoginRequiredMixin, HasAccessToEditConceptCheckMixin,
                     TemplateResponseMixin, View):
    '''
        Restore a deleted concept.
    '''
    model = Concept
    success_url = reverse_lazy('concept_list')
    template_name = 'clinicalcode/concept/restore.html'

    def get_success_url(self):
        return reverse_lazy('concept_list')

    def get(self, request, pk):
        concept = Concept.objects.get(pk=pk)
        return self.render_to_response({'pk': pk, 'name': concept.name})

    def post(self, request, pk):
        with transaction.atomic():
            db_utils.restoreConcept(pk, request.user)
            db_utils.modify_Entity_ChangeReason(Concept, pk, "Concept has been restored")
        messages.success(self.request, "Concept has been successfully restored.")
        return HttpResponseRedirect(self.get_success_url())


class ConceptUpdate(LoginRequiredMixin, HasAccessToEditConceptCheckMixin,
                    UpdateView):
    '''
        Update the current concept.
    '''
    user_list = []
    model = Concept
    form_class = ConceptForm
    success_url = reverse_lazy('concept_list')
    template_name = 'clinicalcode/concept/form.html'

    # --------------------------------
    confirm_overrideVersion = 0
    is_valid1 = True

    # latest_history_id = -1
    # --------------------------------

    # Sending user object to the form, to verify which fields to display/remove (depending on group)
    def get_form_kwargs(self):
        kwargs = super(UpdateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def get_success_url(self):
        return reverse('concept_update', args=(self.object.id, ))

    def form_valid(self, form):

        # ----------------------------------------------------------
        # alert user when concurrent editing of concept
        latest_history_id = str(self.object.history.latest().history_id)
        latest_history_id_shown = str(self.request.POST.get('latest_history_id'))
        overrideVersion = self.request.POST.get('overrideVersion')

        self.confirm_overrideVersion = 0
        if latest_history_id_shown != latest_history_id and str(overrideVersion) == "0":
            self.confirm_overrideVersion = -1
            self.is_valid1 = False
            form.add_error(None, mark_safe("This concept has an updated version,<br/> Do you want to continue and override it?!<br/> To override click 'Save' again."))
            # form.non_field_errors("This concept has an updated version, Do you want to continue and override it? 11")
            form.is_valid = self.is_valid1
            return self.form_invalid(form)
            # return HttpResponseRedirect(self.get_context_data(**kwargs))
        # ----------------------------------------------------------

        with transaction.atomic():
            form.instance.modified_by = self.request.user
            form.instance.modified = datetime.datetime.now()

            code_attribute_headers = json.loads(
                self.request.POST.get('code_attribute_header'))
            form.instance.code_attribute_header = code_attribute_headers
            # -----------------------------------------------------
            # get tags
            tag_ids = self.request.POST.get('tagids')
            #             new_tag_list = []
            if tag_ids:
                # split tag ids into list
                new_tag_list = [int(i) for i in tag_ids.split(",")]
                form.instance.tags = new_tag_list

            #             #-----------------------------------------------------

            # save the concept with a change reason to reflect the update within the concept audit history
            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(Concept, self.kwargs['pk'], "Updated")
            # Get all the 'parent' concepts i.e. those that include this one,
            # and add a history entry to those that this concept has been
            # updated.
            db_utils.saveDependentConceptsChangeReason(self.kwargs['pk'], "Component concept #" + str(self.kwargs['pk']) + " was updated")
            messages.success(self.request, "Concept has been successfully updated.")

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)
        tags = Tag.objects.filter(pk=-1)
        concept_tags = self.get_object().tags
        if concept_tags:
            tags = Tag.objects.filter(pk__in=concept_tags)

        context.update(build_permitted_components_list(self.request, self.get_object().pk, check_published_child_concept=True))

        if self.get_object().is_deleted == True:
            messages.info(self.request, "This concept has been deleted.")

        context['tags'] = tags
        context['code_attribute_header'] = json.dumps(self.get_object().code_attribute_header)
        context['history'] = self.get_object().history.all()
        # user_can_export is intended to control the Export CSV button. It might
        # be better described as user can view all children, but that currently
        # seems more obscure.
        context['user_can_export'] = (allowed_to_view_children(self.request, Concept, self.get_object().id)
                                      and db_utils.chk_deleted_children(self.request,
                                                                      Concept,
                                                                      self.get_object().id,
                                                                      returnErrors=False)
                                    )
        context['allowed_to_permit'] = allowed_to_permit(self.request.user, Concept, self.get_object().id)
        # context['enable_publish'] = settings.ENABLE_PUBLISH

        # published versions
        published_historical_ids = list(PublishedConcept.objects.filter(concept_id=self.get_object().id).values_list('concept_history_id', flat=True))
        context['published_historical_ids'] = published_historical_ids

        # ------------------------------
        latest_history_id = context['concept'].history.first().history_id
        context['latest_history_id'] = latest_history_id if self.request.POST.get('latest_history_id') is None else self.request.POST.get('latest_history_id')
        context['overrideVersion'] = self.confirm_overrideVersion
        # -------------------------------

        context['current_concept_history_id'] = int(latest_history_id)

        context['is_published'] = PublishedConcept.objects.filter(concept_id=self.get_object().id, concept_history_id=context['latest_history_id']).exists()

        return context


@login_required
# not used now
def concept_components(request, pk):
    '''
        Get the components used by the Concept
        Parameters:     request    The request.
                        pk         The concept id.
        Returns:        data       Dict with the components and flags. 
        Accesses the Component table's concept_id field.
    '''
    validate_access_to_view(request, Concept, pk)

    components = Component.objects.filter(concept_id=pk)
    data = dict()
    data['form_is_valid'] = True
    data['html_component_list'] = render_to_string(
        'clinicalcode/component/partial_components_view.html',
        {'components': components})

    return JsonResponse(data)


@login_required
def concept_uniquecodes(request, pk):
    '''
        Get the unique codes of the Concept
        Parameters:     request    The request.
                        pk         The concept id.
        Returns:        data       Dict with the unique codes. 
    '''
    validate_access_to_view(request, Concept, pk)

    codes = db_utils.getGroupOfCodesByConceptId(pk)
    data = dict()
    data['form_is_valid'] = True
    codes_count = "0"
    try:
        codes_count = str(len(codes))
    except:
        codes_count = "0"
    data['codes_count'] = codes_count
    data['html_uniquecodes_list'] = render_to_string('clinicalcode/component/get_child_concept_codes.html',
                                                    {'codes': codes,
                                                     'q': request.session.get('concept_search', '')
                                                     })

    return JsonResponse(data)


@login_required
def concept_uniquecodesByVersion(request, pk, concept_history_id):
    '''
        Get the unique codes of the Concept
        for a specific version
        Parameters:     request    The request.
                        pk         The concept id.
                        concept_history_id  The version id
        Returns:        data       Dict with the unique codes. 
    '''

    validate_access_to_view(request,
                            Concept,
                            pk,
                            set_history_id=concept_history_id)

    codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)

    code_attribute_header = Concept.history.get(id=pk, history_id=concept_history_id).code_attribute_header
    concept_history_date = Concept.history.get(id=pk, history_id=concept_history_id).history_date
    codes_with_attributes = []
    if code_attribute_header:
        codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=pk,
                                                                                    concept_history_date=concept_history_date,
                                                                                    allCodes=codes,
                                                                                    code_attribute_header=code_attribute_header
                                                                                   )

        codes = codes_with_attributes

    data = dict()
    data['form_is_valid'] = True
    codes_count = "0"
    try:
        codes_count = str(len(codes))
    except:
        codes_count = "0"
    data['codes_count'] = codes_count
    data['html_uniquecodes_list'] = render_to_string('clinicalcode/component/get_child_concept_codes.html', {
                                                            'codes': codes,
                                                            'code_attribute_header': code_attribute_header,
                                                            'q': ['', request.session.get('concept_search', '')][request.GET.get('highlight','0')=='1']
                                                        })

    return JsonResponse(data)


@login_required
def concept_history_fork(request, pk, concept_history_id):
    '''
        Fork from a concept from the concept's history list.
    '''
    validate_access_to_view(request,
                            Concept,
                            pk,
                            set_history_id=concept_history_id)
    data = dict()
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # fork selected concept, returning a newly created concept id
                new_concept_id, changeReason1 = db_utils.forkHistoryConcept(request.user, concept_history_id)
                # save the concept with a change reason to reflect the fork from history within the concept audit history
                db_utils.save_Entity_With_ChangeReason(Concept, new_concept_id, changeReason1)
                data['form_is_valid'] = True
                data['message'] = render_to_string('clinicalcode/concept/history/forked.html',
                                                   {'id': new_concept_id}, request)
                return JsonResponse(data)
        except Exception as e:
            # need to log error
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/concept/history/fork.html', {}, request)
            return JsonResponse(data)
    concept = db_utils.getHistoryConcept(concept_history_id)
    return render(request, 'clinicalcode/concept/history/fork.html',
                  {'concept': concept})


@login_required
def concept_history_revert(request, pk, concept_history_id):
    ''' 
        Revert a previously saved concept from the history.
    '''
    validate_access_to_edit(request, Concept, pk)
    data = dict()
    if request.method == 'POST':
        # Don't allow revert if the active object is deleted
        if Concept.objects.get(pk=pk).is_deleted: raise PermissionDenied
        try:
            with transaction.atomic():
                db_utils.deleteConceptRelatedObjects(pk)
                db_utils.revertHistoryConcept(request.user, concept_history_id)
                db_utils.modify_Entity_ChangeReason(
                    Concept, pk,
                    "Concept reverted from version %s" % concept_history_id)

                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(
                    pk, "Component concept #" + str(pk) + " was updated")

                data['form_is_valid'] = True
                data['message'] = render_to_string(
                    'clinicalcode/concept/history/reverted.html', {'id': pk},
                    request)
                return JsonResponse(data)
        except Exception as e:
            # todo: need to log error
            data['form_is_valid'] = False
            data['message'] = render_to_string(
                'clinicalcode/concept/history/revert.html', {}, request)
            return JsonResponse(data)

    concept = db_utils.getHistoryConcept(concept_history_id)
    is_latest_version = (int(concept_history_id) == Concept.objects.get(
        pk=pk).history.latest().history_id)

    return render(request, 'clinicalcode/concept/history/revert.html', {
        'concept': concept,
        'is_latest_version': is_latest_version
    })


def concept_list(request):
    '''
        Display the list of concepts. This view can be searched and contains paging.
    '''

    search_tag_list = []
    tags = []
    
    # get page index variables from query or from session   
    expand_published_versions = 0  # disable this option    

    method = request.GET.get('filtermethod', '')

    page_size = utils.get_int_value(request.GET.get('page_size', 20), 20)
    page_size = page_size if page_size in page_size_limits else 20
    page = utils.get_int_value(request.GET.get('page', 1), 1)
    search = request.GET.get('search', '') #request.session.get('concept_search', ''))
    tag_ids = request.GET.get('tagids', '')
    owner = request.GET.get('owner', '')
    author = request.GET.get('author', '')
    coding_ids = request.GET.get('codingids', '')
    des_order = request.GET.get('order_by', '')
    concept_brand = request.GET.get('concept_brand', request.session.get('concept_brand', ''))  # request.CURRENT_BRAND
     
    show_deleted_concepts = request.GET.get('show_deleted_concepts', 0)
    show_my_concepts = request.GET.get('show_my_concepts', 0)
    show_only_validated_concepts = request.GET.get('show_only_validated_concepts', 0)   
    must_have_published_versions = request.GET.get('must_have_published_versions', 0)

    search_form = request.GET.get('search_form', 'basic-form')

    start_date_range = request.GET.get('startdate', '')
    end_date_range = request.GET.get('enddate', '')
    
    start_date_query, end_date_query = False, False
    try:
        start_date_query = make_aware(datetime.datetime.strptime(start_date_range, '%Y-%m-%d'))
        end_date_query = make_aware(datetime.datetime.strptime(end_date_range, '%Y-%m-%d'))
    except ValueError:
        start_date_query = False
        end_date_query = False
                
            


        
    # store page index variables to session
    request.session['concept_page_size'] = page_size
    request.session['concept_page'] = page
    request.session['concept_search'] = search 
    request.session['concept_tagids'] = tag_ids
    request.session['concept_brand'] = concept_brand
    request.session['concept_codingids'] = coding_ids
    request.session['concept_date_start'] = start_date_range
    request.session['concept_date_end'] = end_date_range
     
    #if search_form !='basic-form':     
    request.session['concept_owner'] = owner   
    request.session['concept_author'] = author
    request.session['concept_show_deleted_concepts'] = show_deleted_concepts   
    request.session['concept_show_my_concept'] = show_my_concepts
    request.session['show_only_validated_concepts'] = show_only_validated_concepts   
    request.session['concept_must_have_published_versions'] = must_have_published_versions
    request.session['concept_search_form'] = search_form

        
        
    # remove leading, trailing and multiple spaces from text search params
    search = re.sub(' +', ' ', search.strip())
    owner = re.sub(' +', ' ', owner.strip())
    author = re.sub(' +', ' ', author.strip())
    
    
    filter_cond = " 1=1 "
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published

    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'C' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^C\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_int_id = db_utils.chk_valid_id(request, set_class=Concept, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id =" + str(ret_int_id) + " ) "
            
            
    if tag_ids:
        # split tag ids into list
        search_tag_list = [str(i) for i in tag_ids.split(",")]
        # chk if these tags are valid, to prevent injection
        # use only those found in the DB
        tags = Tag.objects.filter(id__in=search_tag_list)
        search_tag_list = list(tags.values_list('id',  flat=True))
        search_tag_list = [str(i) for i in search_tag_list]           
        filter_cond += " AND tags && '{" + ','.join(search_tag_list) + "}' "

    if coding_ids:
        search_coding_list = [str(i) for i in coding_ids.split(',')]
        coding = CodingSystem.objects.filter(id__in=search_coding_list)
        search_coding_list = list(coding.values_list('id', flat=True))
        search_coding_list = [str(i) for i in search_coding_list]
        filter_cond += " AND coding_system_id IN (" + ','.join(search_coding_list) + ") "

    if isinstance(start_date_query, datetime.datetime) and isinstance(end_date_query, datetime.datetime):
        filter_cond += " AND (created >= '" + start_date_range + "' AND created <= '" + end_date_range + "') "
    
    # check if it is the public site or not
    if request.user.is_authenticated:
        # ensure that user is only allowed to view/edit the relevant concepts

        get_live_and_or_published_ver = 3
        if must_have_published_versions == "1":
            get_live_and_or_published_ver = 2

        # show only concepts created by the current user
        if show_my_concepts == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)

        # if show deleted concepts is 1 then show deleted concepts
        if show_deleted_concepts != "1":
            exclude_deleted = True
        else:
            exclude_deleted = False

    else:
        # show published concepts
        get_live_and_or_published_ver = 2
    #         if PublishedConcept.objects.all().count() == 0:
    #             # redirect to login page if no published concepts
    #             return HttpResponseRedirect(settings.LOGIN_URL)

    show_top_version_only = True
    if expand_published_versions == "1":
        show_top_version_only = False

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                filter_cond += " AND owner_id=" + str(owner_id)
            else:
                # username not found
                filter_cond += " AND owner_id= -1 "

    # if show_only_validated_concepts is 1 then show only concepts with validation_performed=True
    if show_only_validated_concepts == "1":
        filter_cond += " AND COALESCE(validation_performed, FALSE) IS TRUE "

    # show concepts for a specific brand
    if concept_brand != "":
        current_brand = Brand.objects.all().filter(name=concept_brand)
        group_list = list(current_brand.values_list('groups', flat=True))
        filter_cond += " AND group_id IN(" + ', '.join(map(str, group_list)) + ") "

    order_param = db_utils.get_order_from_parameter(des_order)
    concepts_srch = db_utils.get_visible_live_or_published_concept_versions(
                                                                            request,
                                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                                            search=[search, ''][search_by_id],
                                                                            author=author,
                                                                            exclude_deleted=exclude_deleted,
                                                                            filter_cond=filter_cond,
                                                                            show_top_version_only=show_top_version_only,
                                                                            search_name_only = False,
                                                                            highlight_result = True,
                                                                            order_by=order_param
                                                                            )

    # create pagination
    paginator = Paginator(concepts_srch,
                          page_size,
                          allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    p_btns = utils.get_paginator_pages(paginator, p)

    tag_ids2 = tag_ids
    tag_ids_list = []
    if tag_ids:
        tag_ids_list = [int(t) for t in tag_ids.split(',')]

    collections_excluded_from_filters = []
    if request.CURRENT_BRAND != "":
        collections_excluded_from_filters = request.BRAND_OBJECT.collections_excluded_from_filters
               
    brand_associated_collections = db_utils.get_brand_associated_collections(request, 
                                                                            concept_or_phenotype='concept',
                                                                            brand=None,
                                                                            excluded_collections=collections_excluded_from_filters
                                                                            )
    
    brand_associated_collections_ids = list(brand_associated_collections.values_list('id', flat=True))

    # Tags
    brand_associated_tags = db_utils.get_brand_associated_tags(request, 
                                                                brand=None,
                                                                excluded_tags=collections_excluded_from_filters
                                                                )

    # Coding id 
    coding_system_reference = db_utils.get_coding_system_reference(request)
    coding_system_reference_ids = list(coding_system_reference.values_list('id', flat=True))
    coding_id_list = []
    if coding_ids:
        coding_id_list = [int(id) for id in coding_ids.split(',')]

    owner = request.session.get('concept_owner')    
    author = request.session.get('concept_author') 
    show_deleted_concepts = request.session.get('concept_show_deleted_concepts')    
    show_my_concepts = request.session.get('concept_show_my_concept')
    show_only_validated_concepts = request.session.get('show_only_validated_concepts')   
    must_have_published_versions = request.session.get('concept_must_have_published_versions')
    
    context = {
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'show_my_concepts': show_my_concepts,
        'show_deleted_concepts': show_deleted_concepts,
        'tags': tags,
        'tag_ids': tag_ids2,
        'tag_ids_list': tag_ids_list,
        'owner': owner,
        'show_only_validated_concepts': show_only_validated_concepts,
        'allowed_to_create': not settings.CLL_READ_ONLY,
        'concept_brand': concept_brand,
        'must_have_published_versions': must_have_published_versions,
        'allTags': Tag.objects.all().order_by('description'),
        'search_form': search_form,
        'p_btns': p_btns,
        'brand_associated_collections': brand_associated_collections,
        'brand_associated_collections_ids': brand_associated_collections_ids,
        'all_collections_selected': all(item in tag_ids_list for item in brand_associated_collections_ids),
        'coding_system_reference': coding_system_reference,
        'coding_system_reference_ids': coding_system_reference_ids,
        'brand_associated_tags': brand_associated_tags,
        'brand_associated_tags_ids': list(brand_associated_tags.values()),
        'all_tags_selected': all(item in tag_ids_list for item in brand_associated_tags.values()),
        'coding_id_list': coding_id_list,
        'all_coding_selected':all(item in coding_id_list for item in coding_system_reference_ids),
        'ordered_by': des_order,
        'filter_start_date': start_date_range,
        'filter_end_date': end_date_range
    }

    if method == 'basic-form':
        return render(request, 'clinicalcode/concept/concept_results.html', context)
    else:
        return render(request, 'clinicalcode/concept/index.html', context)


@login_required
def concept_tree(request, pk):
    '''
        display parent and child tree views
    '''
    concept = Concept.objects.get(pk=pk)

    return render(request, 'clinicalcode/concept/tree.html', {
        'pk': pk,
        'name': concept.name
    })


@login_required
def concept_upload_codes(request, pk):
    '''
        Upload a set of codes for a concept.
    '''
    validate_access_to_edit(request, Concept, pk)
    form_class = ConceptUploadForm
    errorMsg = []

    if request.method == 'POST':

        form = form_class(request.POST, request.FILES)
        # check if a file has been uploaded
        # if not request.FILES.get('upload_concept_file'):
        #    form.add_error(None, forms.ValidationError('You must upload a file to continue'))
        if form.is_valid():
            # TODO: validate
            # a file must have been uploaded
            # it must have at least a code and a description
            # plus other validation rules
            try:
                with transaction.atomic():
                    # check if a file has been uploaded
                    if request.FILES.get('upload_concept_file'):
                        current_concept = Concept.objects.get(pk=pk)
                        concept_upload_file = request.FILES['upload_concept_file']
                        
                        delimiter = request.POST.get('specify_delimiter')
                        #codes = list(csv.reader([line.decode() for line in concept_upload_file ], delimiter=','))
                        codes = list(csv.reader([line.decode() for line in concept_upload_file ], delimiter=delimiter))
                        

                        # The posted variables:
                        upload_name = request.POST.get('upload_name')
                        logical_type = request.POST.get('logical_type')
                        concept_level_depth = utils.get_int_value(request.POST.get('concept_level_depth'), 1)
                        category_column = request.POST.get('category_column')
                        sub_category_column = request.POST.get('sub_category_column')
                        first_row_has_column_headings = request.POST.get('first_row_has_column_headings')
                        col_1 = request.POST.get('col_1')
                        col_2 = request.POST.get('col_2')
                        col_3 = request.POST.get('col_3')
                        col_4 = request.POST.get('col_4')
                        col_5 = request.POST.get('col_5')
                        col_6 = request.POST.get('col_6')
                        # get the column number for each column category
                        code_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'code')
                        code_desc_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'desc')
                        cat_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'cat')
                        cat_desc_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'cat_desc')
                        sub_cat_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'sub_cat')
                        sub_cat_desc_col = utils.get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, 'sub_cat_desc')

                        category_column_index = utils.get_column_index_by_text(code_col, code_desc_col, cat_col, cat_desc_col, sub_cat_col, sub_cat_desc_col, category_column)
                        sub_category_column_index = utils.get_column_index_by_text(code_col, code_desc_col, cat_col, cat_desc_col, sub_cat_col, sub_cat_desc_col, sub_category_column)

                        cat_lookup_field = cat_desc_col
                        sub_cat_lookup_field = sub_cat_desc_col

                        if category_column:
                            cat_lookup_field = category_column_index

                        if sub_category_column:
                            sub_cat_lookup_field = sub_category_column_index

                        # unique category
                        categories = set()
                        row_count = 0
                        # get unique set of categories
                        if cat_col:
                            for row in codes:
                                row_count += 1
                                # ignore first row as it contains header information
                                if (first_row_has_column_headings == 'on' and row_count == 1):
                                    continue
                                # Stripped whitespace from start and end of categories.
                                categories.add(row[cat_lookup_field].strip())

                        # If the concept level depth is 1 and it does not have
                        # categories, then create a single code list with the
                        # codes from the CSV file.
                        if concept_level_depth == 1 and not cat_col:
                            # Create a component, a code-list, a regex and codes.
                            component = Component.objects.create(
                                                    comment=upload_name,
                                                    component_type=Component.
                                                    COMPONENT_TYPE_EXPRESSION_SELECT,
                                                    concept=current_concept,
                                                    created_by=request.user,
                                                    logical_type=logical_type,
                                                    name=upload_name)
                            code_list = CodeList.objects.create(component=component, description=upload_name)
                            CodeRegex.objects.create(
                                                    component=component,
                                                    code_list=code_list,
                                                    regex_type=CodeRegex.SIMPLE,
                                                    regex_code='',
                                                    column_search=CodeRegex.CODE,
                                                    sql_rules='')
                            row_count = 0
                            for row in codes:
                                row_count += 1
                                # ignore the first row as it contains header information
                                if (first_row_has_column_headings == 'on' and row_count == 1):
                                    continue
                                obj, created = Code.objects.get_or_create(
                                                                        code_list=code_list,
                                                                        code=row[code_col],
                                                                        defaults={
                                                                            'description': row[code_desc_col]
                                                                        })
                            ## Now save the concept with a change reason.
                            # db_utils.save_Entity_With_ChangeReason(Concept, pk, "Created component: %s" % upload_name)

                        # if the concept level depth is 1 and it has categories,
                        # then create a code list for each category and populate
                        # each category with related codes.
                        if concept_level_depth == 1 and cat_col:
                            for cat in categories:
                                # Create a component, a code-list, a regex and codes.
                                component = Component.objects.create(
                                                                    comment=cat,
                                                                    component_type=Component.
                                                                    COMPONENT_TYPE_EXPRESSION_SELECT,
                                                                    concept=current_concept,
                                                                    created_by=request.user,
                                                                    logical_type=logical_type,
                                                                    name=cat)
                                code_list = CodeList.objects.create(component=component, description=cat)
                                CodeRegex.objects.create(
                                                                    component=component,
                                                                    code_list=code_list,
                                                                    regex_type=CodeRegex.SIMPLE,
                                                                    regex_code='',
                                                                    column_search=CodeRegex.CODE,
                                                                    sql_rules='')
                                row_count = 0
                                for row in codes:
                                    row_count += 1
                                    if (first_row_has_column_headings == 'on' and row_count == 1):
                                        continue
                                    # Check here for the category matching the stripped category,
                                    # but don't worry if the category is written to the description
                                    # with the trailing space.
                                    if row[cat_lookup_field].strip() == cat:
                                        obj, created = Code.objects.get_or_create(
                                                                                code_list=code_list,
                                                                                code=row[code_col],
                                                                                defaults={
                                                                                    'description':
                                                                                    row[code_desc_col]
                                                                                })

                        # If the concept level depth is greater than 1 and it
                        # has categories and sub-categories then create child
                        # concepts and code lists.
                        if concept_level_depth > 1 and cat_col and sub_cat_col:
                            # For each category create a concept.
                            # Then create a concept component and attach this
                            # new concept to the original concept.
                            for cat in categories:
                                # Unique sub categories per category.
                                sub_categories = set()
                                new_concept = Concept.objects.create(
                                                            name=cat,
                                                            description=cat,
                                                            author=current_concept.author,
                                                            entry_date=current_concept.entry_date,
                                                            validation_performed=current_concept.
                                                            validation_performed,
                                                            validation_description=current_concept.
                                                            validation_description,
                                                            publication_doi=current_concept.
                                                            publication_doi,
                                                            publication_link=current_concept.
                                                            publication_link,
                                                            secondary_publication_links=current_concept
                                                            .secondary_publication_links,
                                                            paper_published=current_concept.
                                                            paper_published,
                                                            source_reference=current_concept.
                                                            source_reference,
                                                            citation_requirements=current_concept.
                                                            citation_requirements,
                                                            created_by=request.user,
                                                            modified_by=request.user,
                                                            owner=request.
                                                            user,  # current_concept.owner,
                                                            group=current_concept.group,
                                                            owner_access=current_concept.owner_access,
                                                            group_access=current_concept.group_access,
                                                            world_access=current_concept.world_access,
                                                            coding_system=current_concept.
                                                            coding_system,
                                                            is_deleted=current_concept.is_deleted)

                                # to save correctly the computed friendly_id field
                                new_concept.history.latest().delete()
                                # new_concept.changeReason = "Created via upload"
                                # new_concept.save()
                                db_utils.save_Entity_With_ChangeReason(Concept, new_concept.pk, "Created via upload")

                                row_count = 0
                                # get unique set of sub categories for the current category
                                for row in codes:
                                    row_count += 1
                                    if (first_row_has_column_headings == 'on' and row_count == 1):
                                        continue
                                    # get a list of unique sub-category names
                                    # Need to check stripped category.
                                    if (row[cat_lookup_field].strip() == cat):
                                        sub_categories.add(row[sub_cat_lookup_field].strip())
                                for sub_cat in sub_categories:
                                    component = Component.objects.create(
                                                                    comment=sub_cat,
                                                                    component_type=Component.
                                                                    COMPONENT_TYPE_EXPRESSION_SELECT,
                                                                    concept=new_concept,
                                                                    created_by=request.user,
                                                                    logical_type=1,  # include
                                                                    name=sub_cat)
                                    code_list = CodeList.objects.create(component=component, description=sub_cat)
                                    codeRegex = CodeRegex.objects.create(
                                                                    component=component,
                                                                    code_list=code_list,
                                                                    regex_type=CodeRegex.SIMPLE,
                                                                    regex_code='',
                                                                    column_search=CodeRegex.CODE,
                                                                    sql_rules='')
                                    row_count = 0
                                    # create codes
                                    for row in codes:
                                        row_count += 1

                                        # ignore the first row as it contains header information
                                        if (first_row_has_column_headings == 'on' and row_count == 1):
                                            continue
                                        # Need to check stripped sub-category.
                                        if row[cat_lookup_field].strip() == cat and row[sub_cat_lookup_field].strip() == sub_cat:
                                            obj, created = Code.objects.get_or_create(
                                                                            code_list=code_list,
                                                                            code=row[code_col],
                                                                            defaults={
                                                                                'description':
                                                                                row[code_desc_col]
                                                                            })
                                    # Save the concept with a change reason to reflect the creation
                                    db_utils.save_Entity_With_ChangeReason(
                                        Concept,
                                        new_concept.pk,
                                        "Created component: %s via upload" %
                                        (component.name),
                                        modified_by_user=request.user)

                                # Create a new concept component and attach
                                # it to the original concept.
                                component_main = Component.objects.create(
                                                            comment=cat,
                                                            component_type=Component.
                                                            COMPONENT_TYPE_CONCEPT,
                                                            concept=current_concept,
                                                            concept_ref=new_concept,
                                                            created_by=request.user,
                                                            logical_type=logical_type,
                                                            name="%s component" % cat,
                                                            concept_ref_history_id=new_concept.history.
                                                            latest().pk)

                                # save child-concept codes
                                db_utils.save_child_concept_codes(
                                                                    concept_id=current_concept.pk,
                                                                    component_id=component_main.pk,
                                                                    referenced_concept_id=new_concept.pk,
                                                                    concept_ref_history_id=new_concept.history.
                                                                    latest().pk,
                                                                    insert_or_update='insert')

                    # components = Component.objects.filter(concept_id=pk)
                    # save the concept with a change reason to reflect the restore within the concept audit history
                    db_utils.save_Entity_With_ChangeReason(Concept, pk, "Codes uploaded: %s" % upload_name)

                    # Update dependent concepts & working sets
                    db_utils.saveDependentConceptsChangeReason(pk, "Component concept #" + str(pk) + " was updated")

                    data = dict()
                    data['form_is_valid'] = True

                    # refresh component list
                    data['html_component_list'] = render_to_string(
                        'clinicalcode/component/partial_component_list.html',
                        build_permitted_components_list(request, pk))

                    concept = Concept.objects.get(id=pk)

                    # update history list
                    data['html_history_list'] = render_to_string(
                        'clinicalcode/concept/partial_history_list.html', {
                            'history':
                            concept.history.all(),
                            'current_concept_history_id':
                            concept.history.latest().pk,
                            'published_historical_ids':
                            list(
                                PublishedConcept.objects.filter(
                                    concept_id=pk).values_list(
                                        'concept_history_id', flat=True))
                        },
                        request=request)

                    data['latest_history_ID'] = concept.history.latest().pk

                    # update add_menu_items to reflect latest history id
                    data['add_menu_items'] = render_to_string(
                        'clinicalcode/concept/add_menu_items.html', {
                            'pk': pk,
                            'latest_history_id': concept.history.latest().pk
                        })

                    return JsonResponse(data)
            except Exception as e:
                errorMsg = []
                errorMsg.append('Error Encountered, Code List has not Been Uploaded.')
                if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC or  request.user.is_superuser:
                    errorMsg.append(str(e))
                    
                data = dict()
                # ------------------------------
                concept = Concept.objects.get(id=pk)
                latest_history_ID = concept.history.latest().pk if request.POST.get('latest_history_id_shown') is None else request.POST.get('latest_history_id_shown')
                data['latest_history_ID'] = latest_history_ID
                # ------------------------------
                # data['exception'] = sys.exc_info()[0]
                data['form_is_valid'] = False
                data['html_form'] = render_to_string(
                    'clinicalcode/concept/upload.html', {
                        'pk': pk,
                        'form': form,
                        'latest_history_ID': latest_history_ID,
                        'errorMsg': errorMsg
                    }, request)

                return JsonResponse(data)

        else:
            data = dict()
            # ------------------------------
            concept = Concept.objects.get(id=pk)
            latest_history_ID = concept.history.latest().pk if request.POST.get('latest_history_id_shown') is None else request.POST.get('latest_history_id_shown')
            data['latest_history_ID'] = latest_history_ID
            # ------------------------------
            # data['exception'] = sys.exc_info()[0]
            data['form_is_valid'] = False
            
            # Error handling
            errorMsg = ['Form is invalid.']
            # Columns that are required or can prompt error
            upload_name = request.POST.get('upload_name')
            col_1 = request.POST.get('col_1')
            col_2 = request.POST.get('col_2')
            col_3 = request.POST.get('col_3')
            col_4 = request.POST.get('col_4')
            col_5 = request.POST.get('col_5')
            col_6 = request.POST.get('col_6')
            #filename = request.FILES.get('upload_concept_file')

            if upload_name.strip() == '':
                errorMsg.append('Please Include a Name for the Concept Upload.')
            elif col_1 == col_2 == col_3 == col_4 == col_5 == col_6 == '':
                errorMsg.append('Please Assign at least code and description Columns for the Concept Upload.')
            elif not request.FILES.get('upload_concept_file'):
                # check if a file has been uploaded
                errorMsg.append('You must upload a file to continue')
            else:
                errorMsg.append('Unspecified Error with Upload.')
                
            data['html_form'] = render_to_string(
                'clinicalcode/concept/upload.html', {
                    'pk': pk,
                    'form': form,
                    'latest_history_ID': latest_history_ID,
                    'errorMsg': errorMsg
                }, request)
            return JsonResponse(data)

    concept = Concept.objects.get(id=pk)
    return render(
        request, 'clinicalcode/concept/upload.html', {
            'pk': pk,
            'form': form_class,
            'latest_history_ID': concept.history.latest().pk,
            'errorMsg': errorMsg
        })


@login_required
def concept_codes_to_csv(request, pk):
    """
        Return a csv file of distinct codes for a concept group
    """
    db_utils.validate_access_to_view(request, Concept, pk)

    current_concept = Concept.objects.get(pk=pk)

    user_can_export = (allowed_to_view_children(request, Concept, pk)
                       and db_utils.chk_deleted_children(
                           request, Concept, pk, returnErrors=False)
                       and not current_concept.is_deleted)
    if not user_can_export:
        return HttpResponseNotFound("Not found.")
        # raise PermissionDenied

    codes = db_utils.getGroupOfCodesByConceptId(pk)

    my_params = {'id': pk, 'creation_date': time.strftime("%Y%m%dT%H%M%S")}
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="concept_C%(id)s_group_codes_%(creation_date)s.csv"'
        % my_params)

    writer = csv.writer(response)

    # ---------
    # latest concept_history_id
    latest_history_id = Concept.objects.get(id=pk).history.latest('history_id').history_id
    code_attribute_header = Concept.history.get(id=pk, history_id=latest_history_id).code_attribute_header
    concept_history_date = Concept.history.get(id=pk, history_id=latest_history_id).history_date
    codes_with_attributes = []
    if code_attribute_header:
        codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(
                                                concept_id=pk,
                                                concept_history_date=concept_history_date,
                                                allCodes=codes,
                                                code_attribute_header=code_attribute_header)

        codes = codes_with_attributes
    # ---------

    titles = [
        'code', 'description', 'coding_system', 'concept_id',
        'concept_version_id', 'concept_name'
    ]
    if code_attribute_header:
        titles = titles + code_attribute_header

    writer.writerow(titles)

    concept_coding_system = Concept.objects.get(id=pk).coding_system.name

    for c in codes:
        code_attributes = []
        if code_attribute_header:
            for a in code_attribute_header:
                code_attributes.append(c[a])

        writer.writerow([
            c['code'],  # .encode('ascii', 'ignore').decode('ascii'),
            c['description'].encode('ascii', 'ignore').decode('ascii'),
            concept_coding_system,
            current_concept.friendly_id,
            current_concept.history.latest().history_id,
            current_concept.name,
        ] + code_attributes)

    return response


def history_concept_codes_to_csv(request, pk, concept_history_id):
    """
        Return a csv file of distinct codes for a specific historical concept version
    """

    # validate access for login and public site
    db_utils.validate_access_to_view(request,
                                     Concept,
                                     pk,
                                     set_history_id=concept_history_id)

    #     if concept_history_id is None:
    #         # get the latest version
    #         concept_history_id = int(Concept.objects.get(pk=pk).history.latest().history_id)

    is_published = PublishedConcept.objects.filter(concept_id=pk, concept_history_id=concept_history_id).exists()

    # ----------------------------------------------------------------------

    # exclude(is_deleted=True)
    if Concept.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    if Concept.history.filter(id=pk, history_id=concept_history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    current_concept = Concept.objects.get(pk=pk)

    if request.user.is_authenticated:
        user_can_export = (allowed_to_view_children(request, Concept, pk, set_history_id=concept_history_id)
                           and db_utils.chk_deleted_children(request,
                                                           Concept,
                                                           pk,
                                                           returnErrors=False,
                                                           set_history_id=concept_history_id
                                                           )
                           and not current_concept.is_deleted)
    else:
        user_can_export = is_published

    if not user_can_export:
        return HttpResponseNotFound("Not found.")
        # raise PermissionDenied

    history_concept = db_utils.getHistoryConcept(concept_history_id)

    codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)

    my_params = {
        'id': pk,
        'concept_history_id': concept_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="concept_C%(id)s_ver_%(concept_history_id)s_group_codes_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    # ---------
    code_attribute_header = Concept.history.get(id=pk, history_id=concept_history_id).code_attribute_header
    concept_history_date = history_concept['history_date']  # Concept.history.get(id=pk, history_id=concept_history_id).history_date
    codes_with_attributes = []
    if code_attribute_header:
        codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=pk,
                                                                                    concept_history_date=concept_history_date,
                                                                                    allCodes=codes,
                                                                                    code_attribute_header=code_attribute_header)

        codes = codes_with_attributes
    # ---------

    titles = [
        'code', 'description', 'coding_system', 'concept_id',
        'concept_version_id', 'concept_name'
    ]
    if code_attribute_header:
        titles = titles + code_attribute_header

    writer.writerow(titles)

    concept_coding_system = Concept.history.get(id=pk, history_id=concept_history_id).coding_system.name

    for c in codes:
        code_attributes = []
        if code_attribute_header:
            for a in code_attribute_header:
                code_attributes.append(c[a])

        writer.writerow([
            c['code'],  # .encode('ascii', 'ignore').decode('ascii'),
            c['description'].encode('ascii', 'ignore').decode('ascii'),
            concept_coding_system,
            current_concept.friendly_id,
            concept_history_id,
            history_concept['name'],
        ] + code_attributes)
    return response


@login_required
def check_concurrent_concept_update(request, pk):
    # Alert user when concurrent editing of concept (components)

    latest_history_id_shown = request.GET.get('latest_history_id_shown', "").strip()
    component_id = request.GET.get('component_id', "").strip()

    noConflict = True
    confirm_overrideVersion = 0
    context = {}

    # Check if the concept is not deleted
    if (pk.strip() != ""):
        if (not Concept.objects.filter(pk=pk).exists() or not Concept.objects.filter(pk=pk).exclude(is_deleted=True).exists()):
            confirm_overrideVersion = -1
            noConflict = False
            context['errorMsg'] = [
                mark_safe(
                    "This concept is deleted,\n (maybe by another user with edit permission).\n please Cancel and Return to index page."
                )
            ]

    # Check if the component is not deleted
    if noConflict:
        if (component_id.strip() != ""):
            if not Component.objects.filter(pk=component_id).exists():
                confirm_overrideVersion = -1
                noConflict = False
                context['errorMsg'] = [
                    mark_safe(
                        "This concept component is deleted,\n (maybe by another user with edit permission).\n please Cancel and Refresh concept page."
                    )
                ]

    # Check if the concept was concurrently updated
    if noConflict:
        concept = Concept.objects.get(pk=pk)
        latest_history_id = str(concept.history.latest().history_id)

        if latest_history_id_shown != latest_history_id:
            confirm_overrideVersion = -2
            noConflict = False
            context['errorMsg'] = [
                mark_safe(
                    "This concept has an updated version,\n Do you want to continue and override it?!\n To override click OK."
                )
            ]
        else:
            context['successMsg'] = ["No Concurrent update."]

    context['noConflict'] = noConflict
    context['overrideVersion'] = confirm_overrideVersion

    return JsonResponse(context)


@login_required
def choose_concepts_to_compare(request):
    return render(request,
                  'clinicalcode/concept/choose_concepts_to_compare.html', {})


@login_required
def conceptversions(request, pk, concept_history_id, indx):
    '''
        Get the historical versions of the Concept
        Parameters:     request    The request.
                        pk         The concept id.
        Returns:        data       Dict with the versions ids. 
    '''

    validate_access_to_view(request,
                            Concept,
                            pk,
                            set_history_id=concept_history_id)

    concept = Concept.objects.get(pk=pk)
    # versions = concept.history.order_by('-history_id')
    versions = db_utils.get_visible_live_or_published_concept_versions(request, exclude_deleted=True, filter_cond=" id= " + str(pk))

    data = dict()
    data['form_is_valid'] = True

    versions_count = "0"
    try:
        versions_count = str(len(versions))
    except:
        versions_count = "0"

    data['versions_count'] = versions_count

    data['indx'] = indx

    data['html_versions_list'] = render_to_string(
        'clinicalcode/concept/get_concept_versions.html', {
            'versions': versions,
            'latest_version': concept.history.latest().history_id,
            'chosen_concept_history_id': int(concept_history_id),
            'indx': indx
        })

    return JsonResponse(data)


@login_required
def compare_concepts_codes(request, concept_id, version_id, concept_ref_id, version_ref_id):
    validate_access_to_view(request,
                            Concept,
                            concept_id,
                            set_history_id=version_id)
    validate_access_to_view(request,
                            Concept,
                            concept_ref_id,
                            set_history_id=version_ref_id)

    # checking access to child concepts is not needed here
    # allowed_to_view_children(request, Concept, pk)
    # chk_deleted_children(request, Concept, pk, returnErrors = False)

    main_concept = Concept.objects.get(pk=concept_id)
    ref_concept = Concept.objects.get(pk=concept_ref_id)

    if (main_concept.is_deleted == True or ref_concept.is_deleted == True):
        return render(request, 'custom-msg.html',
                      {'msg_title': 'Data Not found.'})

    if (main_concept.history.filter(id=concept_id, history_id=version_id).count() == 0  
            or ref_concept.history.filter(id=concept_ref_id, history_id=version_ref_id).count() == 0
        ):
        return render(request, 'custom-msg.html',
                      {'msg_title': 'Data Not found.'})

    main_concept_history_version = main_concept.history.get(id=concept_id, history_id=version_id)
    ref_concept_history_version = ref_concept.history.get(id=concept_ref_id, history_id=version_ref_id)

    main_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=concept_id, concept_history_id=version_id)

    if not main_codes:
        main_codes = [{'code': 'No CODES !!', 'description': ''}]

    # main_name = main_concept.name + " - (" + str(concept_id) + "/" + str(version_id) + ") - " + main_concept.author
    # get data from version history
    main_name = (main_concept_history_version.name + "<BR><strong>(" +
                str(main_concept_history_version.friendly_id) + "/" +
                str(version_id) + ")</strong> " +
                "<BR><strong>author:</strong> " +
                main_concept_history_version.author)

    # ----------------------------------
    ref_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=concept_ref_id, concept_history_id=version_ref_id)
    if not ref_codes:
        ref_codes = [{'code': 'No CODES !!', 'description': ''}]

    # ref_name = ref_concept.name + " - (" + str(concept_ref_id) + "/" + str(version_ref_id) + ") - " + ref_concept.author
    # get data from version history
    ref_name = (ref_concept_history_version.name + "<BR><strong>(" +
                str(ref_concept_history_version.friendly_id) + "/" +
                str(version_ref_id) + ")</strong> " +
                "<BR><strong>author:</strong> " +
                ref_concept_history_version.author)

    main_df = pd.DataFrame.from_dict(main_codes)
    ref_df = pd.DataFrame.from_dict(ref_codes)

    full_outer_join_df = pd.merge(main_df,
                                  ref_df,
                                  on="code",
                                  how="outer",
                                  indicator=True)

    full_outer_join_df = full_outer_join_df.sort_values(by=['_merge'], ascending=False)
    # replace NaN with '-'
    # full_outer_join_df['description_x'].fillna('-')
    # full_outer_join_df['description_y'].fillna('-')

    is_identical = False
    msg = "The two concepts' codes are not identical"
    merge_col_distinct = list(full_outer_join_df['_merge'].unique())
    if len(merge_col_distinct) == 1 and merge_col_distinct == ['both']:
        is_identical = True
        msg = "The two concepts' codes are identical"

    columns = ['code', 'description_x', 'description_y', 'merge']
    rows = [tuple(r) for r in full_outer_join_df.to_numpy()]
    net_comparison = [dict(list(zip(columns, row))) for row in rows]

    return render(request, 'clinicalcode/concept/compare_cocepts_codes.html', 
                    {
                        'concept_id': concept_id,
                        'version_id': version_id,
                        'concept_ref_id': concept_ref_id,
                        'version_ref_id': version_ref_id,
                        'main_name': main_name,
                        'ref_name': ref_name,
                        'is_identical': is_identical,
                        'msg': msg,
                        'net_comparison': net_comparison
                    }
                )


class ConceptPublish(LoginRequiredMixin, HasAccessToViewConceptCheckMixin,
                     TemplateResponseMixin, View):
    model = Concept
    template_name = 'clinicalcode/concept/publish.html'

    errors = {}
    allow_to_publish = True
    concept_is_deleted = False
    is_owner = True
    concept_has_codes = True
    has_child_concepts = False
    child_concepts_OK = True
    AllnotDeleted = True
    AllarePublished = True
    isAllowedtoViewChildren = True

    def checkConceptTobePublished(self, request, pk, concept_history_id):
        global errors, allow_to_publish, concept_is_deleted, is_owner
        global has_child_concepts, concept_has_codes, child_concepts_OK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        '''
            Allow to publish if:
            - Concept is not deleted
            - user is an owner
            - Concept contains codes
            - user has view access to all child concepts (level 1)
            - all child concepts TREE is publish/not deleted
        '''
        errors = {}
        allow_to_publish = True
        concept_is_deleted = False
        is_owner = True
        concept_has_codes = True
        has_child_concepts = False
        child_concepts_OK = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        if (Concept.objects.get(id=pk).is_deleted == True):
            allow_to_publish = False
            concept_is_deleted = True

        if (Concept.objects.filter(Q(id=pk), Q(owner=self.request.user)).count() == 0):
            allow_to_publish = False
            is_owner = False

        if (len(db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=pk, concept_history_id=concept_history_id)) == 0):
            allow_to_publish = False
            concept_has_codes = False

        has_child_concepts, child_concepts_OK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors = checkAllChildConcepts4Publish_Historical(
            request, pk, concept_history_id)
        if not child_concepts_OK:
            allow_to_publish = False

    def get(self, request, pk, concept_history_id):

        global errors, allow_to_publish, concept_is_deleted, is_owner, concept_has_codes
        global has_child_concepts, child_concepts_OK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        errors = {}
        allow_to_publish = True
        concept_is_deleted = False
        is_owner = True
        concept_has_codes = True
        has_child_concepts = False
        child_concepts_OK = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        concept_ver = Concept.history.get(id=pk, history_id=concept_history_id)
        is_published = checkIfPublished(Concept, pk, concept_history_id)

        if not is_published:
            self.checkConceptTobePublished(request, pk, concept_history_id)
        # --------------------------------------------

        return self.render_to_response({
                                        'pk': pk,
                                        'name': concept_ver.name,
                                        'concept_history_id': concept_history_id,
                                        'is_published': is_published,
                                        'allowed_to_publish': allow_to_publish,
                                        'is_owner': is_owner,
                                        'concept_is_deleted': concept_is_deleted,
                                        'concept_has_codes': concept_has_codes,
                                        'has_child_concepts': has_child_concepts,
                                        'child_concepts_OK': child_concepts_OK,
                                        'AllnotDeleted': AllnotDeleted,
                                        'AllarePublished': AllarePublished,
                                        'isAllowedtoViewChildren': isAllowedtoViewChildren,
                                        'errors': errors
                                    })

    def post(self, request, pk, concept_history_id):
        global errors, allow_to_publish, concept_is_deleted, is_owner, concept_has_codes
        global has_child_concepts, child_concepts_OK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren
        errors = {}
        allow_to_publish = True
        concept_is_deleted = False
        is_owner = True
        concept_has_codes = True
        has_child_concepts = False
        child_concepts_OK = True
        AllnotDeleted = True
        AllarePublished = True
        isAllowedtoViewChildren = True

        is_published = checkIfPublished(Concept, pk, concept_history_id)
        if not is_published:
            self.checkConceptTobePublished(request, pk, concept_history_id)

        data = dict()

        if not allow_to_publish or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', {},
                                               self.request)
            return JsonResponse(data)

        try:
            if allow_to_publish and not is_published:
                # start a transaction
                with transaction.atomic():
                    concept = Concept.objects.get(pk=pk)
                    published_concept = PublishedConcept(concept=concept, concept_history_id=concept_history_id, created_by=request.user)
                    published_concept.save()
                    data['form_is_valid'] = True
                    data['latest_history_ID'] = concept_history_id  # concept.history.latest().pk

                    #                     # refresh component list
                    #                     data['html_component_list'] = render_to_string(
                    #                         'clinicalcode/component/partial_component_list.html',
                    #                         build_permitted_components_list(self.request, pk)
                    #                         )

                    # update history list

                    data['html_history_list'] = render_to_string(
                                                                'clinicalcode/concept/partial_history_list.html',
                                                                {
                                                                    'history': concept.history.all(),
                                                                    'current_concept_history_id': int(concept_history_id),  # concept.history.latest().pk,
                                                                    'published_historical_ids':list(PublishedConcept.objects.filter(concept_id=pk).values_list('concept_history_id', flat=True))
                                                                },
                                                                request=self.request)

                    #                     # update add_menu_items to reflect latest history id
                    #                     data['add_menu_items'] = render_to_string(
                    #                             'clinicalcode/concept/add_menu_items.html',
                    #                             {'pk': pk,
                    #                              'latest_history_id': concept_history_id    #concept.history.latest().pk
                    #                             }
                    #                         )

                    data['message'] = render_to_string(
                                                        'clinicalcode/concept/published.html', {
                                                            'id': pk,
                                                            'concept_history_id': concept_history_id
                                                        }, self.request)

        except Exception as e:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html', 
                                               {},
                                               self.request)

        return JsonResponse(data)


# ---------------------------------------------------------------------------
def checkAllChildConcepts4Publish_Historical(request, concept_id, concept_history_id):
    # get historic tree
    child_concepts_versions = getChildConceptsTree_Historical(concept_id, concept_history_id)

    # Now check all the child Concepts for deletion(from live version) and Publish(from historical version)
    # we check access(from live version) here.

    errors = {}
    has_child_concepts = False
    if child_concepts_versions:
        has_child_concepts = True

    AllnotDeleted = True
    for concept in child_concepts_versions:
        isDeleted = False
        isDeleted = (Concept.objects.filter(Q(id=concept[0])).exclude(is_deleted=True).count() == 0)
        if (isDeleted):
            errors[concept[0]] = 'Child concept (' + str(concept[0]) + ') is deleted'
            AllnotDeleted = False

    AllarePublished = True
    for concept in child_concepts_versions:
        is_published = False
        is_published = checkIfPublished(Concept, concept[0], concept[1])
        if (not is_published):
            errors[str(concept[0]) + '/' + str(concept[1])] = 'Child concept (' + str(concept[0]) + '/' + str(concept[1]) + ') is not published'
            AllarePublished = False

    # Now check all for access.
    isAllowedtoViewChildren = True
    #     # to check view on all tree
    #     chk_view_concepts = child_concepts_versions
    # Now, with no sync propagation, we check only one level for permissions
    child_concepts_level1 = db_utils.get_history_child_concept_components(concept_id, concept_history_id=concept_history_id)
    chk_view_concepts = set()
    for concept in child_concepts_level1:
        chk_view_concepts.add((concept['concept_ref_id'], concept['concept_ref_history_id']))

    for concept in chk_view_concepts:
        permitted = False
        permitted = allowed_to_view(request,
                                    Concept,
                                    set_id=concept[0],
                                    set_history_id=concept[1])

        if (not permitted):
            errors[str(concept[0]) + '_view'] = 'Child concept (' + str(concept[0]) + ') is not permitted.'
            isAllowedtoViewChildren = False

    isOK = (AllnotDeleted and AllarePublished and isAllowedtoViewChildren)

    return has_child_concepts, isOK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors


def getChildConceptsTree_Historical(concept_id, concept_history_id):
    '''
        get all tree of child concepts/versions for a concept of a specific version id
    '''

    # get historical concept components
    childConcepts = db_utils.get_history_child_concept_components(str(concept_id), str(concept_history_id))
    # returns ('concept_ref_id' , 'concept_ref_history_id')

    child_concepts_versions = set()
    if not childConcepts:
        return child_concepts_versions

    for c in childConcepts:
        child_concepts_versions.add((c['concept_ref_id'], c['concept_ref_history_id']))
        child_concepts_versions.update(getChildConceptsTree_Historical(c['concept_ref_id'], c['concept_ref_history_id']))

    return child_concepts_versions


