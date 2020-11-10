'''
    ---------------------------------------------------------------------------
    WORKING-SET VIEW
    ---------------------------------------------------------------------------
'''
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin #, UserPassesTestMixin
from django.contrib import messages
# from django.contrib.messages import constants
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse_lazy, reverse
#from django.db.models import Q
from django.db import transaction #, models, IntegrityError
# from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect #, StreamingHttpResponse, HttpResponseForbidden
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404 
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.conf import settings
# from rest_framework.permissions import BasePermission

from ..models.Tag import Tag
from ..models.Phenotype import Phenotype
from ..models.PhenotypeTagMap import PhenotypeTagMap
from ..models.Brand import Brand
from django.contrib.auth.models import User, Group
from django.http import HttpResponseNotFound

from View import *
from .. import db_utils, utils
from ..permissions import *

import re
import json
from collections import OrderedDict
import csv
from datetime import datetime
import time

import logging
logger = logging.getLogger(__name__)


@login_required
def phenotype_list(request):
    '''
        display a list of phenotypes. This view can be searched and contains paging
    '''

    new_tag_list = []
    tags = []

    # get page index variables from query or from session
    page_size = utils.get_int_value(request.GET.get('page_size', request.session.get('phenotype_page_size', 20)), 20)
    page = utils.get_int_value(request.GET.get('page', request.session.get('phenotype_page', 1)), 1)
    search = request.GET.get('search', request.session.get('phenotype_search', ''))
    show_my_phenotypes = request.GET.get('show_my_phenotypes',
                                          request.session.get('phenotype_show_my_phenotype', 0))
    show_deleted_phenotypes = request.GET.get('show_deleted_phenotypes',
                                               request.session.get('phenotype_show_deleted_phenotypes', 0))
    tag_ids = request.GET.get('tagids', request.session.get('phenotype_tagids', ''))
    owner = request.GET.get('owner', request.session.get('phenotype_owner', ''))
    author = request.GET.get('author', request.session.get('phenotype_author', ''))
    ws_brand = request.GET.get('ws_brand', request.session.get('ws_brand', request.CURRENT_BRAND))

    if request.method == 'POST':
        # get posted parameters
        search = request.POST.get('search', '')
        page_size = request.POST.get('page_size')
        page = request.POST.get('page', page)
        show_my_phenotypes = request.POST.get('show_my_phenotypes', 0)
        show_deleted_phenotypes = request.POST.get('show_deleted_phenotypes', 0)
        author = request.POST.get('author', '')
        tag_ids = request.POST.get('tagids', '')
        owner = request.POST.get('owner', '')
        ws_brand = request.POST.get('ws_brand', request.CURRENT_BRAND)

    # store page index variables to session
    request.session['phenotype_page_size'] = page_size
    request.session['phenotype_page'] = page
    request.session['phenotype_search'] = search
    request.session['phenotype_show_my_phenotype'] = show_my_phenotypes
    request.session['phenotype_show_deleted_phenotypes'] = show_deleted_phenotypes
    request.session['phenotype_author'] = author
    request.session['phenotype_tagids'] = tag_ids
    request.session['phenotype_owner'] = owner
    request.session['ws_brand'] = ws_brand

    # Ensure that user is only allowed to view the relevant phenotypes.
    phenotypes = get_visible_phenotypes(request.user)

    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            phenotypes = phenotypes.filter(name__icontains=search)

    if tag_ids:
        # split tag ids into list
        new_tag_list = [int(i) for i in tag_ids.split(",")]
        phenotypes = phenotypes.filter(phenotypetagmap__tag__id__in=new_tag_list)
        tags = Tag.objects.filter(id__in=new_tag_list)

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                phenotypes = phenotypes.filter(owner_id=owner_id)
            else:
                phenotypes = phenotypes.filter(owner_id=-1)

    if author is not None:
        if author != '':
            phenotypes = phenotypes.filter(author__icontains=author)

    # show only phenotypes created by the current user
    if show_my_phenotypes == "1":
        phenotypes = phenotypes.filter(owner_id=request.user.id)

    # if show deleted phenotypes is 1 then show deleted phenotypes
    if show_deleted_phenotypes != "1":
        phenotypes = phenotypes.exclude(is_deleted=True)

    # show phenotypes for a specific brand
    if ws_brand != "":
        current_brand = Brand.objects.all().filter(name=ws_brand)
        phenotypes = phenotypes.filter(group__id__in=list(current_brand.values_list('groups', flat=True)))

    # order by id
    phenotypes = phenotypes.order_by('id')

    # Run through the phenotypes and add a 'can edit this phenotype' field.
    for phenotype in phenotypes:
        phenotype.can_edit = False # allowed_to_edit(request.user, phenotype, phenotype.id)

    # create pagination
    paginator = Paginator(phenotypes, page_size, allow_empty_first_page=True)

    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    return render(request, 'clinicalcode/phenotype/index.html', {
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'show_my_phenotypes': show_my_phenotypes,
        'tags': tags,
        'owner': owner,
        'show_deleted_phenotypes': show_deleted_phenotypes,
        'allowed_to_create': allowed_to_create(),
        'ws_brand': ws_brand
    })


@login_required
def phenotype_create(request):
    # TODO: implement this

    # new_phenotype = Phenotype()
    # new_phenotype.phenotype_id = "854857"
    # new_phenotype.title = "tite 33"
    # new_phenotype.name = "request.data.get('name')"
    # new_phenotype.author = "request.data.get('author')"
    # new_phenotype.layout = "request.data.get('layout')"
    # new_phenotype.type = "2"
    # new_phenotype.validation = "True"
    # new_phenotype.valid_event_data_range_start = datetime.now()
    # new_phenotype.valid_event_data_range_end = datetime.now()
    # new_phenotype.sex = "M"
    # new_phenotype.status = "9"
    # new_phenotype.hdr_created_date = datetime.now()
    # new_phenotype.hdr_modified_date = datetime.now()
    # new_phenotype.publications = "request.data.get('publications')"
    # new_phenotype.publication_doi = ""
    # new_phenotype.publication_link = ""
    # new_phenotype.secondary_publication_links = z""
    # new_phenotype.source_reference = ""
    # new_phenotype.citation_requirements = ""
    # new_phenotype.concept_informations = "\"[{\"concept_version_id\": 12870, \"concept_id\": 3790, \"attributes\": []}, {\"concept_version_id\": 12872, \"concept_id\": 3791, \"attributes\": []}]\""
    #
    # new_phenotype.created_by = request.user
    # new_phenotype.owner_access = Permissions.EDIT
    # new_phenotype.owner_id = request.user.id
    #
    # new_phenotype.group_id = None
    # new_phenotype.group_access = 1
    # new_phenotype.world_access = 1
    #
    # new_phenotype.save()

    return redirect('phenotype_list')


class PhenotypeUpdate(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, UpdateView):
    '''
        Update the current working set.
    '''
    model = Phenotype
    success_url = reverse_lazy('phenotype_list')
    template_name = 'clinicalcode/phenotype/form.html'

    def get_success_url(self):
        return reverse('phenotype_update', args=(self.object.phenotype_id,))

    def has_access_to_edit_phenotype(self, user):
        return allowed_to_edit(user, Phenotype, self.kwargs['pk'])

    def get(self, request, pk):
        return redirect('phenotype_list')

        # TODO: implement this.
        # phenotype = Phenotype.objects.get(pk=pk)
        # latest_history_id = str(phenotype.history.latest().history_id)
        # tags = PhenotypeTagMap.objects.filter(phenotype=phenotype)
        # tags = Tag.objects.filter(id__in=list(tags.values_list('tag_id', flat=True)))
        # concept_list = db_utils.getConceptsFromJSON(pk=pk)
        # concepts = Concept.objects.filter(id__in=concept_list)
        # users = User.objects.all()
        # groups = getGroups(request.user)
        # # ----------------------------------------------------------
        # children_permitted_and_not_deleted = True
        # error_dic = {}
        # children_permitted_and_not_deleted, error_dic2 = db_utils.chk_children_permission_and_deletion(
        #     self.request.user, Phenotype, pk)
        # if not children_permitted_and_not_deleted:
        #     error_dic['children'] = error_dic2
        # # -----------------------------------------------------------
        # are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(pk)
        #
        # return render(request, self.template_name, {
        #     'pk': pk,
        #     'phenotype': phenotype,
        #     'concepts': concepts,
        #     'tags': tags,
        #     'users': users, 'groups': groups,
        #     'errorMsg': error_dic,
        #     'allowed_to_permit': allowed_to_permit(self.request.user, Phenotype, pk),
        #     'history': self.get_object().history.all(),
        #     'latest_history_id': latest_history_id,
        #     'overrideVersion': 0,
        #     'concepts_id_versionID': json.dumps(phenotype.concept_version),
        #     'are_concepts_latest_version': are_concepts_latest_version,
        #     'version_alerts': version_alerts
        # })

    def post(self, request, pk):
        return redirect('phenotype_list')

        # TODO: implement this.
        # phenotype = Phenotype.objects.get(pk=pk)
        # latest_history_id = str(phenotype.history.latest().history_id)
        #
        # tag_ids = request.POST.get('tagids')
        # new_tag_list = []
        # if tag_ids:
        #     # split tag ids into list
        #     new_tag_list = [int(i) for i in tag_ids.split(",")]
        #
        # tags = Tag.objects.filter(id__in=new_tag_list)
        #
        # concepts = []
        # concept_list = db_utils.getConceptsFromJSON(pk=pk)
        # concepts = Concept.objects.filter(id__in=concept_list)
        #
        # users = User.objects.all()
        # groups = getGroups(request.user)
        #
        # is_allowed_to_permit = allowed_to_permit(self.request.user, Phenotype, pk)
        #
        # # ----------- update object -------------------------------------------------
        # phenotype.name = request.POST.get('name')
        # phenotype.author = request.POST.get('author')
        # phenotype.publication = request.POST.get('publication')
        # phenotype.description = request.POST.get('description')
        # phenotype.publication_doi = request.POST.get('publication_doi')
        # phenotype.publication_link = request.POST.get('publication_link')
        # phenotype.secondary_publication_links = request.POST.get('secondary_publication_links')
        # phenotype.source_reference = request.POST.get('source_reference')
        # phenotype.citation_requirements = request.POST.get('citation_requirements')
        # phenotype.concept_informations = request.POST.get('concepts_json')
        #
        # # phenotype.concept_version = db_utils.getWSConceptsHistoryIDs(request.POST.get('concepts_json'))
        # # save concepts versions as shown in form
        # phenotype.concept_version = db_utils.getWSConceptsVersionsData(
        #     concept_informations=phenotype.concept_informations,
        #     submitted_concept_version=json.loads(request.POST.get('concepts_id_versionID'))
        # )
        #
        # if is_allowed_to_permit:
        #     phenotype.owner_access = Permissions.EDIT  # int(request.POST.get('ownerAccess'))
        #     phenotype.group_access = int(request.POST.get('groupAccess'))
        #     phenotype.world_access = int(request.POST.get('worldAccess'))
        #     phenotype.owner_id = int(request.POST.get('owner_id'))
        #     phenotype.group_id = int(request.POST.get('group_id'))
        # latest_history_id_shown = request.POST.get('latest_history_id')
        # overrideVersion = request.POST.get('overrideVersion')
        # # If group_is is zero, we have the none placeholder, '---', change
        # # this to None or the DB will complain that group #0 doesn't exist.
        # if phenotype.group_id == 0:
        #     phenotype.group_id = None
        # # decoded_concepts = json.loads(phenotype.concept_informations)
        #
        # are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(pk)
        #
        # # Validation
        # is_valid = True
        # errors = {}
        # is_valid, errors = db_utils.isValidPhenotype(request, phenotype)
        #
        # # ----------------------------------------------------------
        # # alert user when concurrent editing of ws
        # confirm_overrideVersion = 0
        # warnings = []
        # if latest_history_id_shown != latest_history_id and str(overrideVersion) == "0":
        #     confirm_overrideVersion = -1
        #     is_valid = False
        #     warnings.append("This working set has an updated version, Do you want to continue and override it? ")
        # # ----------------------------------------------------------
        # children_permitted_and_not_deleted = True
        # children_permitted_and_not_deleted, error_dic2 = db_utils.chk_children_permission_and_deletion(
        #     self.request.user, Phenotype, pk, WS_concepts_json=phenotype.concept_informations)
        # if not children_permitted_and_not_deleted:
        #     errors['children'] = error_dic2
        #
        # is_valid = (is_valid & children_permitted_and_not_deleted)
        # # -----------------------------------------------------------
        # if not is_valid:  # pop the form with data to correct and submit
        #     return render(request,
        #                   'clinicalcode/phenotype/form.html',
        #                   {
        #                       'pk': pk,
        #                       'phenotype': phenotype,
        #                       'concepts': concepts,
        #                       'tags': tags,
        #                       'users': users, 'groups': groups,
        #                       'errorMsg': errors,
        #                       'allowed_to_permit': is_allowed_to_permit,
        #                       # allowed_to_permit(self.request.user, Phenotype, pk),
        #                       'history': self.get_object().history.all(),
        #                       'latest_history_id': latest_history_id_shown,
        #                       'overrideVersion': confirm_overrideVersion,
        #                       'warningsMsg': warnings,
        #                       'concepts_id_versionID': json.dumps(phenotype.concept_version),
        #                       'are_concepts_latest_version': are_concepts_latest_version,
        #                       'version_alerts': version_alerts
        #                   }
        #                   )
        # else:
        #     if phenotype.group_access == 1:
        #         phenotype.group_id = None
        #
        #     # Have a valid working set, save it and deal with tags.
        #     # start a transaction
        #     with transaction.atomic():
        #         phenotype.updated_by = request.user
        #         phenotype.modified = datetime.now()
        #
        #         # -----------------------------------------------------
        #         # get tags
        #         tag_ids = request.POST.get('tagids')
        #
        #         new_tag_list = []
        #
        #         if tag_ids:
        #             # split tag ids into list
        #             new_tag_list = [int(i) for i in tag_ids.split(",")]
        #
        #         # save the tag ids
        #         old_tag_list = list(
        #             PhenotypeTagMap.objects.filter(phenotype=phenotype).values_list('tag', flat=True))
        #
        #         # detect tags to add
        #         tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))
        #
        #         # detect tags to remove
        #         tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))
        #
        #         # add tags that have not been stored in db
        #         for tag_id_to_add in tag_ids_to_add:
        #             PhenotypeTagMap.objects.get_or_create(phenotype=phenotype, tag=Tag.objects.get(id=tag_id_to_add),
        #                                                    created_by=self.request.user)
        #
        #         # remove tags no longer required in db
        #         for tag_id_to_remove in tag_ids_to_remove:
        #             tag_to_remove = PhenotypeTagMap.objects.filter(phenotype=phenotype,
        #                                                             tag=Tag.objects.get(id=tag_id_to_remove))
        #             tag_to_remove.delete()
        #
        #         # -----------------------------------------------------
        #
        #         phenotype.changeReason = db_utils.standardiseChangeReason("Updated")
        #         phenotype.save()
        #
        #     # db_utils.savePhenotypeChangeReason(pk, "Working set has been updated")
        #     messages.success(self.request, "Working set has been successfully updated.")
        #
        # # return HttpResponseRedirect(self.get_success_url())
        # # return redirect('phenotype_list')
        # return redirect('phenotype_update', pk=pk)


class PhenotypeDelete(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, TemplateResponseMixin, View):
    """
        Delete a working set.
    """
    model = Phenotype
    success_url = reverse_lazy('phenotype_list')
    template_name = 'clinicalcode/phenotype/delete.html'

    def get_success_url(self):
        return reverse_lazy('phenotype_list')

    def has_access_to_edit_phenotype(self, user):
        return allowed_to_edit(user, Phenotype, self.kwargs['pk'])

    def get(self, request, pk):
        return redirect('phenotype_list')

        # TODO: implement this.
        # 
        # phenotype = Phenotype.objects.get(pk=pk)
        # return render(request, self.template_name, {'pk': pk, 'name': phenotype.name})

    def post(self, request, pk):
        return redirect('phenotype_list')

        # TODO: implement this.
        # with transaction.atomic():
        #     db_utils.deletePhenotype(pk, request.user)
        # messages.success(self.request, "Working Set has been deleted.")
        # return HttpResponseRedirect(self.get_success_url())


class PhenotypeDetail(LoginRequiredMixin, HasAccessToViewPhenotypeCheckMixin, DetailView):
    """
    Display a detailed view of a phenotype.
    """
    model = Phenotype
    template_name = 'clinicalcode/phenotype/detail.html'

    def has_access_to_view_Phenotype(self, user, Phenotype_id):
        phenotype = Phenotype.objects.get(pk=Phenotype_id)
        if phenotype.is_deleted is True:
            messages.info(self.request, "Phenotype has been deleted.")
        # permitted = allowed_to_view_children(user, Phenotype, self.kwargs['pk'])
        return allowed_to_view(user, phenotype, self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = DetailView.get_context_data(self, **kwargs)
        phenotype = Phenotype.objects.get(pk=self.kwargs['pk'])
        tags = PhenotypeTagMap.objects.filter(phenotype=self.get_object())
        context['tags'] = tags
        concept_list = [x['concept_id'] for x in json.loads(self.get_object().concept_informations)] #db_utils.getConceptsFromJSON(concepts_json=self.get_object().concept_informations)
        concepts = Concept.objects.filter(id__in=concept_list).values('id', 'name', 'group')
        #        concepts = Concept.history.all().filter(id__in=concept_list, history_id__in=Phenotype['concept_version'].values()).values('id','name', 'group')
        context['concepts_id_name'] = json.dumps(list(concepts))
        context['user_can_edit'] = (
            not phenotype.is_deleted and allowed_to_edit(self.request.user, Phenotype, self.get_object().id))
        context['history'] = self.get_object().history.all()

        children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(self.request.user,
                                                                                                      Phenotype,
                                                                                                      self.kwargs['pk'])
        are_concepts_latest_version, version_alerts = checkConceptVersionIsTheLatest(self.kwargs['pk'])

        context['user_can_export'] = (children_permitted_and_not_deleted and not phenotype.is_deleted)
        context['is_permitted_to_all'] = children_permitted_and_not_deleted
        context['error_dic'] = error_dic
        context['are_concepts_latest_version'] = are_concepts_latest_version
        context['version_alerts'] = version_alerts
        context['allowed_to_create'] = not settings.CLL_READ_ONLY
        context['conceptBrands'] = json.dumps(db_utils.getConceptBrands(self.request, concept_list))
        return context


@login_required
def phenotype_history_detail(request, pk, phenotype_history_id):
    '''
        Display the detail of a phenotype at a point in time.
    '''
    validate_access_to_view(request.user, Phenotype, pk)
    phenotype = db_utils.getHistoryWorkingset(phenotype_history_id)
    # Get the owner and group data from the IDs stored in the DB and add to the
    # page data.
    owner_id = phenotype['owner_id']
    query_set = User.objects.filter(id__exact=owner_id)
    owner = query_set[0] if query_set.count() > 0 else None
    phenotype['owner'] = owner
    group_id = phenotype['group_id']
    query_set = Group.objects.filter(id__exact=group_id)
    group = query_set[0] if query_set.count() > 0 else None
    phenotype['group'] = group

    phenotype_history_date = phenotype['history_date']

    tags = Tag.objects.filter(pk=-1)
    tags_comp = db_utils.getHistoryTags_Phenotype(pk, phenotype_history_date)
    if tags_comp:
        tag_list = [i['tag_id'] for i in tags_comp if 'tag_id' in i]
        tags = Tag.objects.filter(pk__in=tag_list)

    concept_list = db_utils.getConceptsFromJSON(concepts_json=phenotype['concept_informations'])
    # concepts = Concept.objects.filter(id__in=concept_list).values('id','name', 'group')
    concepts = Concept.history.all().filter(id__in=concept_list,
                                            history_id__in=phenotype['concept_version'].values()).values('id', 'name',
                                                                                                          'group')
    concepts_id_name = json.dumps(list(concepts))

    phenotype_live = Phenotype.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request.user,
                                                                                                  Phenotype, pk,
                                                                                                  set_history_id=phenotype_history_id)
    user_can_export = (children_permitted_and_not_deleted and not phenotype_live.is_deleted)

    conceptBrands = json.dumps(db_utils.getConceptBrands(request, concept_list))

    return render(request, 'clinicalcode/phenotype/history/detail.html',
                  {'phenotype': phenotype,
                   'tags': tags,
                   'concepts_id_name': concepts_id_name,
                   'concepts_id_versionID': json.dumps(phenotype['concept_version']),
                   'user_can_edit': (not phenotype_live.is_deleted and allowed_to_edit(request.user, Phenotype, pk)),
                   'allowed_to_create': allowed_to_create(),
                   'user_can_export': user_can_export,
                   'conceptBrands': conceptBrands
                   })

@login_required
def phenotype_to_csv(request, pk):
    """
        Return a csv file of codes+attributes for a phenotype (live-latest version).
    """
    validate_access_to_view(request.user, Phenotype, pk)

    # exclude(is_deleted=True)
    if Phenotype.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    current_phenotype = Phenotype.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request.user,
                                                                                                  Phenotype, pk)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_phenotype.is_deleted == True:
        raise PermissionDenied

    # make all export csv work on historical data
    latest_history_id = current_phenotype.history.latest().history_id
    return history_phenotype_to_csv(request, pk, latest_history_id)


@login_required
def history_phenotype_to_csv(request, pk, phenotype_history_id):
    """
        Return a csv file of codes+attributes for a working set for a specific historical version.
    """
    validate_access_to_view(request.user, Phenotype, pk)

    # exclude(is_deleted=True)
    if Phenotype.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # exclude(is_deleted=True)
    if Phenotype.history.filter(id=pk, history_id=phenotype_history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # here, check live version
    current_ws = Phenotype.objects.get(pk=pk)

    children_permitted_and_not_deleted, error_dic = db_utils.chk_children_permission_and_deletion(request.user,
                                                                                                  Phenotype, pk,
                                                                                                  set_history_id=phenotype_history_id)
    if not children_permitted_and_not_deleted:
        raise PermissionDenied

    if current_ws.is_deleted == True:
        raise PermissionDenied

    current_ws_version = Phenotype.history.get(id=pk, history_id=phenotype_history_id)

    show_version_number = True

    # Get the list of concepts in the working set data (this is listed in the
    # concept_informations field with additional, user specified columns. Each
    # row is a concept ID and the column data for these extra columns.
    rows = db_utils.getGroupOfConceptsByWorkingsetId_historical(pk, phenotype_history_id)

    my_params = {
        'phenotype_id': pk,
        'phenotype_history_id': phenotype_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
                'attachment; filename="phenotype_%(phenotype_id)s_ver_%(phenotype_history_id)s_concepts_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    done = False
    concept_data = OrderedDict([])
    title_row = []
    final_titles = []

    # Run through the concept_informations rows = one concept at a time.
    # for row in rows:
    # for key, value in row.iteritems():
    for concept_id, columns in rows.iteritems():
        concept_data[concept_id] = []
        # data = json.loads(columns, object_pairs_hook=OrderedDict)
        for column_name, column_data in columns.iteritems():
            if concept_id in concept_data:
                concept_data[concept_id].append(column_data)
            else:
                concept_data[concept_id] = [column_data]

            if column_name.strip() != "":
                if not column_name.split('|')[0] in title_row:
                    title_row.append(column_name.split('|')[0])

    final_titles = (['code', 'description', 'concept_id']
                    + [[], ['concept_version_id']][show_version_number]
                    + ['concept_name']
                    + ['working_set_id', 'working_set_version_id', 'working_set_name']
                    + title_row
                    )

    writer.writerow(final_titles)

    concept_version = Phenotype.history.get(id=pk, history_id=phenotype_history_id).concept_version

    for concept_id, data in concept_data.iteritems():
        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version[concept_id])
        # Allow Working sets with zero attributes
        if title_row == [] and data == ['']:
            data = []
        for cc in codes:
            rows_no += 1
            writer.writerow([
                                cc['code'],
                                cc['description'].encode('ascii', 'ignore').decode('ascii'),
                                concept_id
                            ]
                            + [[], [concept_version[concept_id]]][show_version_number]
                            + [Concept.history.get(id=concept_id, history_id=concept_version[concept_id]).name]
                            + [current_ws_version.id, current_ws_version.history_id, current_ws_version.name]
                            + data)

        if rows_no == 0:
            writer.writerow([
                                '',
                                '',
                                concept_id
                            ]
                            + [[], [concept_version[concept_id]]][show_version_number]
                            + [Concept.history.get(id=concept_id, history_id=concept_version[concept_id]).name]
                            + [current_ws_version.id, current_ws_version.history_id, current_ws_version.name]
                            + data)

    return response


def checkConceptVersionIsTheLatest(phenotypeID):
    return True, {}

    # phenotype = Phenotype.objects.get(pk=phenotypeID)
    # concepts_id_versionID = phenotype.concept_version
    #
    # is_ok = True
    #
    # version_alerts = {}
    #
    # # loop for concept versions
    # for c_id0, c_ver in concepts_id_versionID.iteritems():
    #     c_id = int(c_id0)
    #     latest_history_id = Concept.objects.get(pk=c_id).history.latest('history_id').history_id
    #     if latest_history_id != int(c_ver):
    #         version_alerts[c_id] = "newer version available"
    #         is_ok = False
    # #         else:
    # #             version_alerts[c_id] = ""
    # return is_ok, version_alerts
    #
