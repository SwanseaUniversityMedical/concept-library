'''
    ---------------------------------------------------------------------------
    WORKING-SET VIEW
    ---------------------------------------------------------------------------
'''
import csv
import json
import logging
import re
import time
from collections import OrderedDict
import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import \
    LoginRequiredMixin  # , UserPassesTestMixin
from django.contrib.auth.models import Group, User
# from django.contrib.messages import constants
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import EmptyPage, Paginator
#from django.db.models import Q
from django.db import transaction  # , models, IntegrityError
# from django.forms.models import model_to_dict
from django.http import \
    HttpResponseRedirect  # , StreamingHttpResponse, HttpResponseForbidden
from django.http import HttpResponseNotFound
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import RequestContext
from django.template.loader import render_to_string
#from django.core.urlresolvers import reverse_lazy, reverse
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .. import db_utils, utils
from ..models.Brand import Brand
from ..models.Tag import Tag
from ..models.WorkingSet import WorkingSet
from ..models.WorkingSetTagMap import WorkingSetTagMap
from ..permissions import *
from .View import *

# from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


@login_required
def workingset_create(request):

    validate_access_to_create()

    users = User.objects.all()
    groups = getGroups(request.user)

    if request.method == 'GET':
        # Set up the initial form data.
        workingset = WorkingSet()
        workingset.owner_id = request.user.id
        workingset.owner_access = Permissions.EDIT
        return render(
            request, 'clinicalcode/workingset/form.html', {
                'users': users,
                'groups': groups,
                'workingset': workingset,
                'allowed_to_permit': True,
                'are_concepts_latest_version': True
            })

    elif request.method == 'POST':
        new_workingset = WorkingSet()
        new_workingset.name = request.POST.get('name')
        new_workingset.author = request.POST.get('author')
        new_workingset.publication = request.POST.get('publication')
        new_workingset.description = request.POST.get('description')
        new_workingset.publication_doi = request.POST.get('publication_doi')
        new_workingset.publication_link = request.POST.get('publication_link')
        new_workingset.secondary_publication_links = request.POST.get(
            'secondary_publication_links')
        new_workingset.source_reference = request.POST.get('source_reference')
        new_workingset.citation_requirements = request.POST.get(
            'citation_requirements')
        new_workingset.concept_informations = request.POST.get('concepts_json')
        new_workingset.concept_version = db_utils.getWSConceptsHistoryIDs(
            request.POST.get('concepts_json'))
        new_workingset.created_by = request.user
        new_workingset.owner_access = Permissions.EDIT  #int(request.POST.get('ownerAccess'))
        new_workingset.group_access = int(request.POST.get('groupAccess'))
        new_workingset.world_access = int(request.POST.get('worldAccess'))
        new_workingset.owner_id = int(request.POST.get('owner_id'))
        new_workingset.group_id = int(request.POST.get('group_id'))
        # If group_is is zero, we have the none placeholder, '---', change
        # this to None or the DB will complain that group #0 doesn't exist.
        if new_workingset.group_id == 0:
            new_workingset.group_id = None

        # Validation
        is_valid = True
        errors = {}
        is_valid, errors = db_utils.isValidWorkingSet(request, new_workingset)

        #-----------------------------------------------------------
        if not is_valid:  # pop the form with data to correct and submit

            tags = request.POST.get('tagids')
            new_tag_list = []
            if tags:
                new_tag_list = [int(i) for i in tags.split(",")]

            if tags:
                tags = []
                for tag_id in new_tag_list:
                    tags.append(Tag.objects.get(id=tag_id))

            concept_ids = db_utils.getConceptsFromJSON(
                concepts_json=new_workingset.concept_informations)
            concepts = Concept.objects.filter(id__in=concept_ids)
            context = {}
            #messages.error(request, errors.values())
            context['errorMsg'] = errors

            return render(
                request, 'clinicalcode/workingset/form.html', {
                    'errorMsg': context['errorMsg'],
                    'workingset': new_workingset,
                    'concepts': concepts,
                    'tags': tags,
                    'users': users,
                    'groups': groups,
                    'allowed_to_permit': True,
                    'are_concepts_latest_version': True
                })

        #-----------------------------------------------------------
        else:
            if new_workingset.group_access == 1:
                new_workingset.group_id = None

            new_workingset.save()
            created_WS = WorkingSet.objects.get(pk=new_workingset.pk)
            created_WS.history.latest().delete()

            tag_ids = request.POST.get('tagids')

            # split tag ids into list
            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids.split(",")]

            # add tags that have not been stored in db
            if tag_ids:
                for tag_id_to_add in new_tag_list:
                    WorkingSetTagMap.objects.get_or_create(
                        workingset=new_workingset,
                        tag=Tag.objects.get(id=tag_id_to_add),
                        created_by=request.user)

            db_utils.save_Entity_With_ChangeReason(WorkingSet, created_WS.pk,
                                                   "Created")
            # created_WS.changeReason = "Created"
            # created_WS.save()

            messages.success(request, "Workingset created successfully")
            #return redirect('workingset_list')
            return redirect('workingset_update', pk=new_workingset.id)


class WorkingSetUpdate(LoginRequiredMixin, HasAccessToEditWorkingsetCheckMixin,
                       UpdateView):
    '''
        Update the current working set.
    '''
    model = WorkingSet
    success_url = reverse_lazy('workingset_list')
    template_name = 'clinicalcode/workingset/form.html'

    def get_success_url(self):
        return reverse('workingset_update', args=(self.object.workingset_id, ))

    def has_access_to_edit_workingset(self, user):
        return allowed_to_edit(self.request, WorkingSet, self.kwargs['pk'])

    def get(self, request, pk):
        workingset = WorkingSet.objects.get(pk=pk)
        latest_history_id = str(workingset.history.latest().history_id)
        tags = WorkingSetTagMap.objects.filter(workingset=workingset)
        tags = Tag.objects.filter(
            id__in=list(tags.values_list('tag_id', flat=True)))
        concept_list = db_utils.getConceptsFromJSON(pk=pk)
        concepts = Concept.objects.filter(id__in=concept_list)
        users = User.objects.all()
        groups = getGroups(request.user)
        #----------------------------------------------------------
        children_permitted_and_not_deleted = True
        error_dic = {}
        children_permitted_and_not_deleted, error_dic2 = db_utils.chk_children_permission_and_deletion(
            self.request, WorkingSet, pk)
        if not children_permitted_and_not_deleted:
            error_dic['children'] = error_dic2
        #-----------------------------------------------------------
        are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(
            pk)

        return render(
            request, self.template_name, {
                'pk':
                pk,
                'workingset':
                workingset,
                'concepts':
                concepts,
                'tags':
                tags,
                'users':
                users,
                'groups':
                groups,
                'errorMsg':
                error_dic,
                'allowed_to_permit':
                allowed_to_permit(self.request.user, WorkingSet, pk),
                'history':
                self.get_object().history.all(),
                'latest_history_id':
                latest_history_id,
                'overrideVersion':
                0,
                'concepts_id_versionID':
                json.dumps(workingset.concept_version),
                'are_concepts_latest_version':
                are_concepts_latest_version,
                'version_alerts':
                version_alerts,
                'current_workingset_history_id':
                int(WorkingSet.objects.get(pk=pk).history.latest().history_id)
            })

    def post(self, request, pk):
        workingset = WorkingSet.objects.get(pk=pk)
        latest_history_id = str(workingset.history.latest().history_id)

        tag_ids = request.POST.get('tagids')
        new_tag_list = []
        if tag_ids:
            # split tag ids into list
            new_tag_list = [int(i) for i in tag_ids.split(",")]

        tags = Tag.objects.filter(id__in=new_tag_list)

        concepts = []
        concept_list = db_utils.getConceptsFromJSON(pk=pk)
        concepts = Concept.objects.filter(id__in=concept_list)

        users = User.objects.all()
        groups = getGroups(request.user)

        is_allowed_to_permit = allowed_to_permit(self.request.user, WorkingSet,
                                                 pk)

        #----------- update object -------------------------------------------------
        workingset.name = request.POST.get('name')
        workingset.author = request.POST.get('author')
        workingset.publication = request.POST.get('publication')
        workingset.description = request.POST.get('description')
        workingset.publication_doi = request.POST.get('publication_doi')
        workingset.publication_link = request.POST.get('publication_link')
        workingset.secondary_publication_links = request.POST.get(
            'secondary_publication_links')
        workingset.source_reference = request.POST.get('source_reference')
        workingset.citation_requirements = request.POST.get(
            'citation_requirements')
        workingset.concept_informations = request.POST.get('concepts_json')

        #workingset.concept_version = db_utils.getWSConceptsHistoryIDs(request.POST.get('concepts_json'))
        # save concepts versions as shown in form
        workingset.concept_version = db_utils.getWSConceptsVersionsData(
            concept_informations=workingset.concept_informations,
            submitted_concept_version=json.loads(
                request.POST.get('concepts_id_versionID')))

        if is_allowed_to_permit:
            workingset.owner_access = Permissions.EDIT  #int(request.POST.get('ownerAccess'))
            workingset.group_access = int(request.POST.get('groupAccess'))
            workingset.world_access = int(request.POST.get('worldAccess'))
            workingset.owner_id = int(request.POST.get('owner_id'))
            workingset.group_id = int(request.POST.get('group_id'))
        latest_history_id_shown = request.POST.get('latest_history_id')
        overrideVersion = request.POST.get('overrideVersion')
        # If group_is is zero, we have the none placeholder, '---', change
        # this to None or the DB will complain that group #0 doesn't exist.
        if workingset.group_id == 0:
            workingset.group_id = None
        #decoded_concepts = json.loads(workingset.concept_informations)

        are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(
            pk)

        # Validation
        is_valid = True
        errors = {}
        is_valid, errors = db_utils.isValidWorkingSet(request, workingset)

        #----------------------------------------------------------
        # alert user when concurrent editing of ws
        confirm_overrideVersion = 0
        warnings = []
        if latest_history_id_shown != latest_history_id and str(
                overrideVersion) == "0":
            confirm_overrideVersion = -1
            is_valid = False
            warnings.append(
                "This working set has an updated version, Do you want to continue and override it? "
            )
        #----------------------------------------------------------
        children_permitted_and_not_deleted = True
        children_permitted_and_not_deleted, error_dic2 = db_utils.chk_children_permission_and_deletion(
            self.request,
            WorkingSet,
            pk,
            WS_concepts_json=workingset.concept_informations,
            submitted_concept_version=workingset.concept_version)
        if not children_permitted_and_not_deleted:
            errors['children'] = error_dic2

        is_valid = (is_valid & children_permitted_and_not_deleted)
        #-----------------------------------------------------------
        if not is_valid:  # pop the form with data to correct and submit
            return render(
                request,
                'clinicalcode/workingset/form.html',
                {
                    'pk':
                    pk,
                    'workingset':
                    workingset,
                    'concepts':
                    concepts,
                    'tags':
                    tags,
                    'users':
                    users,
                    'groups':
                    groups,
                    'errorMsg':
                    errors,
                    'allowed_to_permit':
                    is_allowed_to_permit,  #allowed_to_permit(self.request.user, WorkingSet, pk),
                    'history':
                    self.get_object().history.all(),
                    'latest_history_id':
                    latest_history_id_shown,
                    'overrideVersion':
                    confirm_overrideVersion,
                    'warningsMsg':
                    warnings,
                    'concepts_id_versionID':
                    json.dumps(workingset.concept_version),
                    'are_concepts_latest_version':
                    are_concepts_latest_version,
                    'version_alerts':
                    version_alerts,
                    'current_workingset_history_id':
                    int(
                        WorkingSet.objects.get(
                            pk=pk).history.latest().history_id)
                })
        else:
            if workingset.group_access == 1:
                workingset.group_id = None


# Have a valid working set, save it and deal with tags.
# start a transaction
            with transaction.atomic():
                workingset.updated_by = request.user
                workingset.modified = datetime.datetime.now()

                #-----------------------------------------------------
                # get tags
                tag_ids = request.POST.get('tagids')

                new_tag_list = []

                if tag_ids:
                    # split tag ids into list
                    new_tag_list = [int(i) for i in tag_ids.split(",")]

                # save the tag ids
                old_tag_list = list(
                    WorkingSetTagMap.objects.filter(
                        workingset=workingset).values_list('tag', flat=True))

                # detect tags to add
                tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))

                # detect tags to remove
                tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))

                # add tags that have not been stored in db
                for tag_id_to_add in tag_ids_to_add:
                    WorkingSetTagMap.objects.get_or_create(
                        workingset=workingset,
                        tag=Tag.objects.get(id=tag_id_to_add),
                        created_by=self.request.user)

                # remove tags no longer required in db
                for tag_id_to_remove in tag_ids_to_remove:
                    tag_to_remove = WorkingSetTagMap.objects.filter(
                        workingset=workingset,
                        tag=Tag.objects.get(id=tag_id_to_remove))
                    tag_to_remove.delete()

                #-----------------------------------------------------
                # workingset.changeReason = db_utils.standardiseChangeReason("Updated")
                workingset.save()
                db_utils.modify_Entity_ChangeReason(WorkingSet, workingset.pk, "Updated")

            #db_utils.saveWorkingsetChangeReason(pk, "Working set has been updated")
            messages.success(self.request,
                             "Working set has been successfully updated.")

        #return HttpResponseRedirect(self.get_success_url())
        #return redirect('workingset_list')
        return redirect('workingset_update', pk=pk)


class WorkingSetDelete(LoginRequiredMixin, HasAccessToEditWorkingsetCheckMixin,
                       TemplateResponseMixin, View):
    '''
        Delete a working set.
    '''
    model = WorkingSet
    success_url = reverse_lazy('workingset_list')
    template_name = 'clinicalcode/workingset/delete.html'

    def get_success_url(self):
        return reverse_lazy('workingset_list')

    def has_access_to_edit_workingset(self, user):
        return allowed_to_edit(self.request, WorkingSet, self.kwargs['pk'])

    def get(self, request, pk):
        workingset = WorkingSet.objects.get(pk=pk)
        return render(request, self.template_name, {
            'pk': pk,
            'name': workingset.name
        })

    def post(self, request, pk):
        with transaction.atomic():
            db_utils.deleteWorkingset(pk, request.user)
            db_utils.modify_Entity_ChangeReason(
                WorkingSet, pk, "Working set has been deleted")
        messages.success(self.request, "Working Set has been deleted")
        return HttpResponseRedirect(self.get_success_url())


class WorkingSetDetail(LoginRequiredMixin, HasAccessToViewWorkingsetCheckMixin,
                       DetailView):
    ''' display a detailed view of a working set '''
    model = WorkingSet
    template_name = 'clinicalcode/workingset/detail.html'

    def has_access_to_view_workingset(self, user, workingset_id):
        workingset = WorkingSet.objects.get(pk=workingset_id)
        if workingset.is_deleted == True:
            messages.info(self.request, "Workingset has been deleted.")
        #permitted = allowed_to_view_children(self.request, WorkingSet, self.kwargs['pk'])

        return allowed_to_view(self.request, WorkingSet, self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = DetailView.get_context_data(self, **kwargs)
        workingset = WorkingSet.objects.get(pk=self.kwargs['pk'])
        tags = WorkingSetTagMap.objects.filter(workingset=self.get_object())
        context['tags'] = tags
        concept_list = db_utils.getConceptsFromJSON(
            concepts_json=self.get_object().concept_informations)
        concepts = Concept.objects.filter(id__in=concept_list).values(
            'id', 'name', 'group')
        #        concepts = Concept.history.all().filter(id__in=concept_list, history_id__in=workingset['concept_version'].values()).values('id','name', 'group')
        context['concepts_id_name'] = json.dumps(list(concepts))
        context['concepts_id_versionID'] = json.dumps(
            self.get_object().concept_version)
        context['user_can_edit'] = (not workingset.is_deleted
                                    and allowed_to_edit(
                                        self.request, WorkingSet,
                                        self.get_object().id))
        context['history'] = self.get_object().history.all()

        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(
            self.request, WorkingSet, self.kwargs['pk'])
        are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(
            self.kwargs['pk'])

        context['user_can_export'] = (children_permitted_and_not_deleted
                                      and not workingset.is_deleted)
        context['is_permitted_to_all'] = children_permitted_and_not_deleted
        context['error_dic'] = error_dic
        context['are_concepts_latest_version'] = are_concepts_latest_version
        context['version_alerts'] = version_alerts
        context['allowed_to_create'] = not settings.CLL_READ_ONLY
        context['conceptBrands'] = json.dumps(
            db_utils.getConceptBrands(self.request, concept_list))

        context['is_latest_version'] = True
        context['current_workingset_history_id'] = int(
            WorkingSet.objects.get(
                pk=self.kwargs['pk']).history.latest().history_id)
        return context


def checkConceptVersionIsTheLatest(workingsetID):

    workingset = WorkingSet.objects.get(pk=workingsetID)
    concepts_id_versionID = workingset.concept_version

    is_ok = True

    version_alerts = {}

    # loop for concept versions
    for c_id0, c_ver in concepts_id_versionID.items():
        c_id = int(c_id0)
        latest_history_id = Concept.objects.get(
            pk=c_id).history.latest('history_id').history_id
        if latest_history_id != int(c_ver):
            version_alerts[c_id] = "newer version available"
            is_ok = False


#         else:
#             version_alerts[c_id] = ""
    return is_ok, version_alerts


class WorkingSetRestore(LoginRequiredMixin,
                        HasAccessToEditWorkingsetCheckMixin,
                        TemplateResponseMixin, View):
    '''
        Restore a deleted working set.
    '''
    model = WorkingSet
    success_url = reverse_lazy('workingset_list')
    template_name = 'clinicalcode/workingset/restore.html'

    def get_success_url(self):
        return reverse_lazy('workingset_list')

    def has_access_to_edit_workingset(self, user):
        return allowed_to_edit(self.request, WorkingSet, self.kwargs['pk'])

    def get(self, request, pk):
        workingset = WorkingSet.objects.get(pk=pk)
        return render(request, self.template_name, {
            'pk': pk,
            'name': workingset.name
        })

    def post(self, request, pk):
        with transaction.atomic():
            db_utils.restoreWorkingset(pk, request.user)
            db_utils.modify_Entity_ChangeReason(
                WorkingSet, pk, "Working set has been restored")
        messages.success(self.request, "Working set has been restored")
        return HttpResponseRedirect(self.get_success_url())


@login_required
def workingset_history_detail(request, pk, workingset_history_id):
    '''
        Display the detail of a workingset at a point in time.
    '''
    validate_access_to_view(request, WorkingSet, pk, workingset_history_id)

    workingset = db_utils.getHistoryWorkingset(workingset_history_id)
    # Get the owner and group data from the IDs stored in the DB and add to the
    # page data.
    owner_id = workingset['owner_id']
    query_set = User.objects.filter(id__exact=owner_id)
    owner = query_set[0] if query_set.count() > 0 else None
    workingset['owner'] = owner
    group_id = workingset['group_id']
    query_set = Group.objects.filter(id__exact=group_id)
    group = query_set[0] if query_set.count() > 0 else None
    workingset['group'] = group

    workingset_history_date = workingset['history_date']

    tags = Tag.objects.filter(pk=-1)
    tags_comp = db_utils.getHistoryTags_Workingset(pk, workingset_history_date)
    if tags_comp:
        tag_list = [i['tag_id'] for i in tags_comp if 'tag_id' in i]
        tags = Tag.objects.filter(pk__in=tag_list)

    concept_list = db_utils.getConceptsFromJSON(
        concepts_json=workingset['concept_informations'])
    #concepts = Concept.objects.filter(id__in=concept_list).values('id','name', 'group')
    concepts = Concept.history.all().filter(
        id__in=concept_list,
        history_id__in=list(workingset['concept_version'].values())).values(
            'id', 'name', 'group')
    concepts_id_name = json.dumps(list(concepts))

    workingset_live = WorkingSet.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(
        request, WorkingSet, pk, set_history_id=workingset_history_id)
    user_can_export = (children_permitted_and_not_deleted
                       and not workingset_live.is_deleted)

    conceptBrands = json.dumps(db_utils.getConceptBrands(
        request, concept_list))

    is_latest_version = (int(workingset_history_id) == WorkingSet.objects.get(
        pk=pk).history.latest().history_id)

    return render(
        request, 'clinicalcode/workingset/history/detail.html', {
            'workingset':
            workingset,
            'tags':
            tags,
            'concepts_id_name':
            concepts_id_name,
            'concepts_id_versionID':
            json.dumps(workingset['concept_version']),
            'user_can_edit': (not workingset_live.is_deleted
                              and allowed_to_edit(request, WorkingSet, pk)),
            'allowed_to_create':
            allowed_to_create(),
            'user_can_export':
            user_can_export,
            'conceptBrands':
            conceptBrands,
            'is_latest_version':
            is_latest_version
        })


@login_required
def workingset_history_revert(request, pk, workingset_history_id):
    '''
        Revert to a previously saved historical version of the working set.
    '''
    validate_access_to_edit(request, WorkingSet, pk)
    data = dict()
    if request.method == 'POST':
        # Don't allow revert if the active object is deleted
        if WorkingSet.objects.get(pk=pk).is_deleted: raise PermissionDenied
        try:
            with transaction.atomic():
                db_utils.deleteWorkingsetRelatedObjects(pk)
                db_utils.revertHistoryWorkingset(request.user,
                                                 workingset_history_id)

                data['form_is_valid'] = True
                data['message'] = render_to_string(
                    'clinicalcode/workingset/history/reverted.html',
                    {'id': pk}, request)
                return JsonResponse(data)
        except Exception as e:
            # todo: need to log error
            data['form_is_valid'] = False
            data['message'] = render_to_string(
                'clinicalcode/workingset/history/revert.html', {}, request)
            return JsonResponse(data)

    workingset = db_utils.getHistoryWorkingset(workingset_history_id)
    return render(request, 'clinicalcode/workingset/history/revert.html',
                  {'workingset': workingset})


@login_required
def workingset_to_csv(request, pk):
    """
        Return a csv file of codes+attributes for a working set (live-latest version).
    """
    validate_access_to_view(request, WorkingSet, pk)

    current_ws = WorkingSet.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(
        request, WorkingSet, pk)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied

    #make all export csv work on historical data
    latest_history_id = current_ws.history.latest().history_id
    return history_workingset_to_csv(request, pk, latest_history_id)


@login_required
def history_workingset_to_csv(request, pk, workingset_history_id):
    """
        Return a csv file of codes+attributes for a working set for a specific historical version.
    """
    validate_access_to_view(request, WorkingSet, pk)

    # here, check live version
    current_ws = WorkingSet.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(
        request, WorkingSet, pk, set_history_id=workingset_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied

    current_ws_version = WorkingSet.history.get(
        id=pk, history_id=workingset_history_id)

    # Get the list of concepts in the working set data (this is listed in the
    # concept_informations field with additional, user specified columns. Each
    # row is a concept ID and the column data for these extra columns.
    rows = db_utils.getGroupOfConceptsByWorkingsetId_historical(
        pk, workingset_history_id)

    my_params = {
        'workingset_id': pk,
        'workingset_history_id': workingset_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        'attachment; filename="workingset_WS%(workingset_id)s_ver_%(workingset_history_id)s_concepts_%(creation_date)s.csv"'
        % my_params)

    writer = csv.writer(response)

    done = False
    concept_data = OrderedDict([])
    title_row = []
    final_titles = []

    # Run through the concept_informations rows = one concept at a time.
    #for row in rows:
    #for key, value in row.iteritems():
    for concept_id, columns in rows.items():
        concept_data[concept_id] = []
        #data = json.loads(columns, object_pairs_hook=OrderedDict)
        for column_name, column_data in columns.items():
            if concept_id in concept_data:
                concept_data[concept_id].append(column_data)
            else:
                concept_data[concept_id] = [column_data]

            if column_name.strip() != "":
                if not column_name.split('|')[0] in title_row:
                    title_row.append(column_name.split('|')[0])

    final_titles = (
        [
            'code', 'description', 'coding_system', 'concept_id',
            'concept_version_id'
        ] + ['concept_name'] +
        ['working_set_id', 'working_set_version_id', 'working_set_name'] +
        title_row)

    writer.writerow(final_titles)

    concept_version = WorkingSet.history.get(
        id=pk, history_id=workingset_history_id).concept_version

    for concept_id, data in concept_data.items():
        concept_coding_system = Concept.history.get(
            id=concept_id,
            history_id=concept_version[concept_id]).coding_system.name
        concept_name = Concept.history.get(
            id=concept_id, history_id=concept_version[concept_id]).name

        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(
            concept_id, concept_version[concept_id])
        #Allow Working sets with zero attributes
        if title_row == [] and data == ['']:
            data = []
        for cc in codes:
            rows_no += 1
            writer.writerow([
                cc['code'], cc['description'].encode('ascii', 'ignore').decode(
                    'ascii'), concept_coding_system, 'C' +
                str(concept_id), concept_version[concept_id], concept_name,
                current_ws_version.friendly_id, current_ws_version.history_id,
                current_ws_version.name
            ] + data)

        if rows_no == 0:
            writer.writerow([
                '', '', concept_coding_system, 'C' +
                str(concept_id), concept_version[concept_id], concept_name,
                current_ws_version.friendly_id, current_ws_version.history_id,
                current_ws_version.name
            ] + data)

    return response


@login_required
def workingset_list(request):
    '''
        display the list of working sets. This view can be searched and contains paging
    '''

    new_tag_list = []
    tags = []

    # get page index variables from query or from session
    page_size = utils.get_int_value(
        request.GET.get('page_size',
                        request.session.get('workingset_page_size', 20)), 20)
    page = utils.get_int_value(
        request.GET.get('page', request.session.get('workingset_page', 1)), 1)
    search = request.GET.get('search',
                             request.session.get('workingset_search', ''))
    show_my_workingsets = request.GET.get(
        'show_my_workingsets',
        request.session.get('workingset_show_my_workingset', 0))
    show_deleted_workingsets = request.GET.get(
        'show_deleted_workingsets',
        request.session.get('workingset_show_deleted_workingsets', 0))
    tag_ids = request.GET.get('tagids',
                              request.session.get('workingset_tagids', ''))
    owner = request.GET.get('owner',
                            request.session.get('workingset_owner', ''))
    author = request.GET.get('author',
                             request.session.get('workingset_author', ''))
    ws_brand = request.GET.get(
        'ws_brand', request.session.get('workingset_brand',
                                        ''))  # request.CURRENT_BRAND

    if request.method == 'POST':
        # get posted parameters
        search = request.POST.get('search', '')
        page_size = request.POST.get('page_size')
        page = request.POST.get('page', page)
        show_my_workingsets = request.POST.get('show_my_workingsets', 0)
        show_deleted_workingsets = request.POST.get('show_deleted_workingsets',
                                                    0)
        author = request.POST.get('author', '')
        tag_ids = request.POST.get('tagids', '')
        owner = request.POST.get('owner', '')
        ws_brand = request.POST.get('ws_brand', '')  #    request.CURRENT_BRAND

    # store page index variables to session
    request.session['workingset_page_size'] = page_size
    request.session['workingset_page'] = page
    request.session['workingset_search'] = search
    request.session['workingset_show_my_workingset'] = show_my_workingsets
    request.session[
        'workingset_show_deleted_workingsets'] = show_deleted_workingsets
    request.session['workingset_author'] = author
    request.session['workingset_tagids'] = tag_ids
    request.session['workingset_owner'] = owner
    request.session['workingset_brand'] = ws_brand

    # Ensure that user is only allowed to view the relevant workingsets.
    workingsets = get_visible_workingsets(request.user)

    # When in a brand, show only this brand's data ----------------
    brand = request.CURRENT_BRAND
    if brand != "":
        brand_collection_ids = db_utils.get_brand_collection_ids(brand)
        if brand_collection_ids:
            workingsets = workingsets.filter(
                workingsettagmap__tag__id__in=brand_collection_ids)
    #--------------------------------------------------------------

    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            workingsets = workingsets.filter(name__icontains=search)

    if tag_ids:
        # split tag ids into list
        new_tag_list = [int(i) for i in tag_ids.split(",")]
        workingsets = workingsets.filter(
            workingsettagmap__tag__id__in=new_tag_list)
        tags = Tag.objects.filter(id__in=new_tag_list)

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                workingsets = workingsets.filter(owner_id=owner_id)
            else:
                workingsets = workingsets.filter(owner_id=-1)

    if author is not None:
        if author != '':
            workingsets = workingsets.filter(author__icontains=author)

    # show only workingsets created by the current user
    if show_my_workingsets == "1":
        workingsets = workingsets.filter(owner_id=request.user.id)

    # if show deleted concepts is 1 then show deleted concepts
    if show_deleted_workingsets != "1":
        workingsets = workingsets.exclude(is_deleted=True)

    # show workingsets for a specific brand
    if ws_brand != "":
        current_brand = Brand.objects.all().filter(name=ws_brand)
        workingsets = workingsets.filter(
            group__id__in=list(current_brand.values_list('groups', flat=True)))

    # order by id
    workingsets = workingsets.order_by('id')

    # Run through the workingsets and add a 'can edit this workingset' field, etc.
    for workingset in workingsets:
        workingset.can_edit = allowed_to_edit(request, WorkingSet,
                                              workingset.id)
        workingset.history_id = WorkingSet.objects.get(
            pk=workingset.id).history.latest().history_id

    # create pagination
    paginator = Paginator(workingsets, page_size, allow_empty_first_page=True)

    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    p_btns = utils.get_paginator_pages(paginator, p)
    return render(
        request, 'clinicalcode/workingset/index.html', {
            'page': page,
            'page_size': str(page_size),
            'page_obj': p,
            'search': search,
            'author': author,
            'show_my_workingsets': show_my_workingsets,
            'tags': tags,
            'owner': owner,
            'show_deleted_workingsets': show_deleted_workingsets,
            'allowed_to_create': allowed_to_create(),
            'ws_brand': ws_brand,
            'p_btns': p_btns
        })
