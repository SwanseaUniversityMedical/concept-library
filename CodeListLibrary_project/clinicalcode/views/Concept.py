'''
    ---------------------------------------------------------------------------
    CONCEPT VIEW
    
    View-handling for the Concepts.
    ---------------------------------------------------------------------------
'''
import csv
import sys
from django.contrib.auth.mixins import LoginRequiredMixin #, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse_lazy, reverse
from django.db import transaction #, models, IntegrityError
from django.http import HttpResponseRedirect #, StreamingHttpResponse, HttpResponseForbidden
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView #, DeleteView
from django.db.models.aggregates import Max
# from django.contrib.auth.models import User
from django.conf import settings
from simple_history.models import HistoricalRecords
import time

from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.CodeRegex import CodeRegex
from ..models.ConceptTagMap import ConceptTagMap
from ..models.Tag import Tag
from ..models.Brand import Brand
from ..models.PublishedConcept import PublishedConcept

    
from View import *
from .. import db_utils
from .. import utils
from ..permissions import *

from django.utils.timezone import now
from datetime import datetime
from clinicalcode.models.CodingSystem import CodingSystem
from django.views.defaults import permission_denied
from django.http import HttpResponseNotFound, response
from django.http.response import Http404
from _ast import Or
from django.template.context_processors import request


logger = logging.getLogger(__name__)

from django.core.exceptions import  PermissionDenied
from django.utils.safestring import mark_safe #, SafeData, SafeString

from collections import OrderedDict
import numpy as np
import pandas as pd
import json

'''
COM_TYPE_CONCEPT_DESC = 'Concept'
COM_TYPE_QUERY_BUILDER_DESC = 'Query builder'
COM_TYPE_EXPRESSION_DESC = 'Match code with expression'
COM_TYPE_EXPRESSION_SELECT_DESC = 'Select codes individually + import codes'
'''

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
    
    
class ConceptCreate(LoginRequiredMixin, HasAccessToCreateCheckMixin, MessageMixin, CreateView):
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
        if allowed_to_edit(self.request.user, Concept, self.object.id):
            return reverse('concept_update', args=(self.object.id,))
        elif allowed_to_view(self.request.user, Concept, self.object.id):
            return reverse('concept_detail', args=(self.object.id,))
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

           
            #form.changeReason = "Created"   
            #self.object = form.save()
            self.object = form.save()
            db_utils.modifyConceptChangeReason(self.object.pk, "Created")
            concept = Concept.objects.get(pk=self.object.pk)
            concept.history.latest().delete() 

            # add tags that have not been stored in db
            if tag_ids:
                for tag_id_to_add in new_tag_list:
                    ConceptTagMap.objects.get_or_create(concept=self.object, tag=Tag.objects.get(id=tag_id_to_add), created_by=self.request.user)

            concept.changeReason = "Created"
            concept.save()   

            
            messages.success(self.request, "Concept has been successfully created.")

        return HttpResponseRedirect(self.get_success_url())
    


class ConceptDelete(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, TemplateResponseMixin, View):
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
            db_utils.modifyConceptChangeReason(pk, "Concept has been deleted")
        messages.success(self.request, "Concept has been successfully deleted.")
        return HttpResponseRedirect(self.get_success_url())
   

def ConceptDetail_combined(request, pk, concept_history_id=None):
    ''' 
        Display the detail of a concept at a point in time.
    '''
    # validate access for login and public site
    if request.user.is_authenticated():
        validate_access_to_view(request.user, Concept, pk)
    else:
        if not Concept.objects.filter(id=pk).exists(): 
            raise PermissionDenied


    if concept_history_id is not None:
        if not Concept.history.filter(id=pk, history_id=concept_history_id).exists():
            raise PermissionDenied

        
    if concept_history_id is None:
        # get the latest version
        concept_history_id = int(Concept.objects.get(pk=pk).history.latest().history_id) 
        
    is_published = PublishedConcept.objects.filter(concept_id=pk, concept_history_id=concept_history_id).exists()
    if not request.user.is_authenticated():
        # check if the concept version is published
        if not is_published: 
            raise PermissionDenied 
    
    #----------------------------------------------------------------------
  
    concept = db_utils.getHistoryConcept(concept_history_id)
    # The history concept contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the concept.
    if concept['owner_id'] is not None:
        concept['owner'] =  User.objects.get(id = int(concept['owner_id']))

    if concept['group_id'] is not None: 
        concept['group'] = Group.objects.get(id = int(concept['group_id']))

    concept_history_date = concept['history_date']
    components = db_utils.getHistoryComponents(pk, concept_history_date)
    
    tags =  Tag.objects.filter(pk=-1)
    tags_comp = db_utils.getHistoryTags(pk, concept_history_date)
    if tags_comp:
        tag_list = [i['tag_id'] for i in tags_comp if 'tag_id' in i]
        tags = Tag.objects.filter(pk__in=tag_list)
    #----------------------------------------------------------------------
    
    if request.user.is_authenticated():
        components_permissions = build_permitted_components_list(request.user, pk)

        can_edit = (not Concept.objects.get(pk=pk).is_deleted) and allowed_to_edit(request.user, Concept, pk)
        
        user_can_export = (allowed_to_view_children(request.user, Concept, pk, set_history_id=concept_history_id)
                          and
                          db_utils.chk_deleted_children(request.user, Concept, pk, returnErrors = False, set_history_id=concept_history_id)
                          and 
                          not Concept.objects.get(pk=pk).is_deleted
                          )
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
    other_versions = Concept.objects.get(pk=pk).history.all()#.exclude(history_id=concept_history_id)
    other_historical_versions = []

    for ov in other_versions:
        ver = db_utils.getHistoryConcept(ov.history_id)
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id = int(ver['owner_id']))
            
        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id = int(ver['created_by_id']))
                
        if ver['modified_by_id'] is not None:
            ver['modified_by'] = User.objects.get(pk=ver['modified_by_id'])

        is_this_version_published = False
        is_this_version_published = PublishedConcept.objects.filter(concept_id=ver['id'], concept_history_id=ver['history_id']).exists()
        if is_this_version_published:
            ver['publish_date'] = PublishedConcept.objects.get(concept_id=ver['id'], concept_history_id=ver['history_id']).created
        else:
            ver['publish_date'] = None
            
        if request.user.is_authenticated(): 
            other_historical_versions.append(ver)
        else:
            if is_this_version_published:
                other_historical_versions.append(ver)
           
    # how to show codelist tab
    if request.user.is_authenticated():        
        component_tab_active = "active"
        codelist_tab_active = ""
        codelist = []
        codelist_loaded = 0
    else:
        # published
        component_tab_active = "" 
        codelist_tab_active = "active"
        codelist = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)
        codelist_loaded = 1
         
    context = { 'concept': concept, 
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
                   'is_latest_version':is_latest_version,
                   'current_concept_history_id': int(concept_history_id),
                   'component_tab_active': component_tab_active,
                   'codelist_tab_active': codelist_tab_active,
                   'codelist': codelist, #json.dumps(codelist)
                   'codelist_loaded': codelist_loaded 
                }
    if request.user.is_authenticated():
        if is_latest_version and (can_edit):
            needed_keys = ['user_can_view_component', 'user_can_edit_component','component_error_msg_view',
                           'component_error_msg_edit', 'component_concpet_version_msg', 'latest_history_id']
            context.update({k: components_permissions[k] for k in needed_keys})
    

        
    return render(request, 'clinicalcode/concept/detail_combined.html',
                context
                )
    
        
class ConceptFork(LoginRequiredMixin, HasAccessToViewConceptCheckMixin, HasAccessToCreateCheckMixin, TemplateResponseMixin, View):
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
                data['message'] = render_to_string('clinicalcode/concept/forked.html',
                                                   {'id': new_concept_id}, self.request)
                db_utils.saveConceptWithChangeReason(new_concept_id,
                    "Forked from concept %s" % pk
                    )
        except Exception as e:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {}, self.request)
        return JsonResponse(data)


class ConceptRestore(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, TemplateResponseMixin, View):
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
            db_utils.modifyConceptChangeReason(pk, "Concept has been restored")
        messages.success(self.request, "Concept has been successfully restored.")
        return HttpResponseRedirect(self.get_success_url())


class ConceptUpdate(LoginRequiredMixin, HasAccessToEditConceptCheckMixin, UpdateView):
    '''
        Update the current concept.
    '''
    user_list = []
    model = Concept
    form_class = ConceptForm
    success_url = reverse_lazy('concept_list')
    template_name = 'clinicalcode/concept/form.html'

    #--------------------------------
    confirm_overrideVersion = 0
    is_valid1 = True
    #latest_history_id = -1
    #--------------------------------

    
        
    # Sending user object to the form, to verify which fields to display/remove (depending on group)
    def get_form_kwargs(self):
        kwargs = super(UpdateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def get_success_url(self):
        return reverse('concept_update', args=(self.object.id,))


    
    def form_valid(self, form):

        #----------------------------------------------------------
        # alert user when concurrent editing of concept
        latest_history_id = str(self.object.history.latest().history_id)
        latest_history_id_shown = str(self.request.POST.get('latest_history_id'))
        overrideVersion = self.request.POST.get('overrideVersion')
       
        self.confirm_overrideVersion = 0
        if latest_history_id_shown != latest_history_id and str(overrideVersion)=="0":
            self.confirm_overrideVersion = -1
            self.is_valid1 = False
            form.add_error(None, mark_safe("This concept has an updated version,<br/> Do you want to continue and override it?!<br/> To override click 'Save' again."))
            #form.non_field_errors("This concept has an updated version, Do you want to continue and override it? 11")
            form.is_valid = self.is_valid1
            return self.form_invalid(form)
            #return HttpResponseRedirect(self.get_context_data(**kwargs))
        #----------------------------------------------------------
      
        with transaction.atomic():
            form.instance.modified_by = self.request.user
            form.instance.modified = datetime.now()
            #-----------------------------------------------------
            # get tags
            tag_ids = self.request.POST.get('tagids')
            new_tag_list = []
            if tag_ids:
                # split tag ids into list
                new_tag_list = [int(i) for i in tag_ids.split(",")]
            # save the tag ids
            old_tag_list = list(ConceptTagMap.objects.filter(concept=self.get_object()).values_list('tag', flat=True))
            # detect tags to add
            tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))
            # detect tags to remove
            tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))
            # add tags that have not been stored in db
            for tag_id_to_add in tag_ids_to_add:
                ConceptTagMap.objects.get_or_create(concept=self.object, tag=Tag.objects.get(id=tag_id_to_add), created_by=self.request.user)
            # remove tags no longer required in db
            for tag_id_to_remove in tag_ids_to_remove:
                tag_to_remove = ConceptTagMap.objects.filter(concept=self.object, tag=Tag.objects.get(id=tag_id_to_remove))
                tag_to_remove.delete()
            #-----------------------------------------------------

            # save the concept with a change reason to reflect the update within the concept audit history
            self.object = form.save()
            db_utils.modifyConceptChangeReason(self.kwargs['pk'], "Updated")
            # Get all the 'parent' concepts i.e. those that include this one,
            # and add a history entry to those that this concept has been
            # updated.
            db_utils.saveDependentConceptsChangeReason(self.kwargs['pk'], "Component concept #" + str(self.kwargs['pk']) + " was updated")
            messages.success(self.request, "Concept has been successfully updated.")

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)
        tags = ConceptTagMap.objects.filter(concept=self.get_object())
        context.update(build_permitted_components_list(self.request.user, self.get_object().pk))
        
        if self.get_object().is_deleted == True:
            messages.info(self.request, "This concept has been deleted.")
            
        context['tags'] = tags
        context['history'] = self.get_object().history.all()
        # user_can_export is intended to control the Export CSV button. It might
        # be better described as user can view all children, but that currently
        # seems more obscure.    
        context['user_can_export'] = (allowed_to_view_children(self.request.user, Concept, self.get_object().id)
                                      and
                                      db_utils.chk_deleted_children(self.request.user, Concept, self.get_object().id, returnErrors = False)
                                      )
        context['allowed_to_permit'] = allowed_to_permit(self.request.user, Concept, self.get_object().id)
        #context['enable_publish'] = settings.ENABLE_PUBLISH

        # published versions
        published_historical_ids = list(PublishedConcept.objects.filter(concept_id=self.get_object().id).values_list('concept_history_id', flat=True))
        context['published_historical_ids'] = published_historical_ids

        #------------------------------
        latest_history_id = context['concept'].history.first().history_id
        context['latest_history_id'] = latest_history_id if self.request.POST.get('latest_history_id') is None else self.request.POST.get('latest_history_id')
        context['overrideVersion'] = self.confirm_overrideVersion
        #-------------------------------
        
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
    validate_access_to_view(request.user, Concept, pk)

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
    validate_access_to_view(request.user, Concept, pk)

    codes = db_utils.getGroupOfCodesByConceptId(pk)
    data = dict()
    data['form_is_valid'] = True
    codes_count = "0"
    try:
        codes_count = str(len(codes))
    except:
        codes_count = "0"
    data['codes_count'] = codes_count
    data['html_uniquecodes_list'] = render_to_string(
        'clinicalcode/component/get_child_concept_codes.html',
        {'codes': codes})

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
    
    if not Concept.objects.filter(id=pk).exists(): 
            raise PermissionDenied


    if not Concept.history.filter(id=pk, history_id=concept_history_id).exists():
        raise PermissionDenied
        
    validate_access_to_view(request.user, Concept, pk)

         
    codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)
    
    data = dict()
    data['form_is_valid'] = True
    codes_count = "0"
    try:
        codes_count = str(len(codes))
    except:
        codes_count = "0"
    data['codes_count'] = codes_count
    data['html_uniquecodes_list'] = render_to_string(
        'clinicalcode/component/get_child_concept_codes.html',
        {'codes': codes})

    return JsonResponse(data)    
    
    
    

@login_required
def conceptversions(request, pk, indx):
    '''
        Get the historical versions of the Concept
        Parameters:     request    The request.
                        pk         The concept id.
        Returns:        data       Dict with the versions ids. 
    '''
    validate_access_to_view(request.user, Concept, pk)
    
    concept = Concept.objects.get(pk=pk)
    versions = concept.history.order_by('-history_id')
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
        'clinicalcode/concept/get_concept_versions.html',
        {'versions': versions,
        'latest_version': concept.history.latest().history_id,
        'indx': indx
        })

    return JsonResponse(data)

@login_required
def concept_history_fork(request, pk, concept_history_id):
    '''
        Fork from a concept from the concept's history list.
    '''
    validate_access_to_view(request.user, Concept, pk)
    data = dict()
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # fork selected concept, returning a newly created concept id
                new_concept_id, changeReason1 = db_utils.forkHistoryConcept(request.user, concept_history_id)
                # save the concept with a change reason to reflect the fork from history within the concept audit history
                db_utils.saveConceptWithChangeReason(new_concept_id, changeReason1)
                data['form_is_valid'] = True
                data['message'] = render_to_string(
                    'clinicalcode/concept/history/forked.html',
                    {'id': new_concept_id}, request)
                return JsonResponse(data)
        except Exception as e:
            # need to log error
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/concept/history/fork.html',
                                               {}, request)
            return JsonResponse(data)
    concept = db_utils.getHistoryConcept(concept_history_id)
    return render(request,
                  'clinicalcode/concept/history/fork.html',
                  {'concept': concept})


@login_required
def concept_history_revert(request, pk, concept_history_id):
    ''' 
        Revert a previously saved concept from the history.
    '''
    validate_access_to_edit(request.user, Concept, pk)
    data = dict()
    if request.method == 'POST':
        # Don't allow revert if the active object is deleted
        if Concept.objects.get(pk=pk).is_deleted:  raise PermissionDenied 
        try:
            with transaction.atomic():
                db_utils.deleteConceptRelatedObjects(pk)
                db_utils.revertHistoryConcept(request.user, concept_history_id)
                db_utils.modifyConceptChangeReason(pk,
                    "Concept reverted from version %s" % concept_history_id)
                
                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(pk, "Component concept #" + str(pk) + " was updated")
                     
                data['form_is_valid'] = True
                data['message'] = render_to_string(
                    'clinicalcode/concept/history/reverted.html',
                    {'id': pk},
                    request)
                return JsonResponse(data)
        except Exception as e:
            # todo: need to log error
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/concept/history/revert.html',
                                               {},
                                               request)
            return JsonResponse(data)
        
    concept = db_utils.getHistoryConcept(concept_history_id)
    is_latest_version = (int(concept_history_id) == Concept.objects.get(pk=pk).history.latest().history_id)

    return render(request, 'clinicalcode/concept/history/revert.html',
                  {'concept': concept,
                   'is_latest_version': is_latest_version
                   })



def concept_list(request):
    '''
        Display a list of concepts. This view can be searched and contains paging.
    '''
        
    search_tag_list = []
    tags = []
    
    # get page index variables from query or from session
    page_size = utils.get_int_value(request.GET.get('page_size', request.session.get('concept_page_size', 20)), 20)
    page = utils.get_int_value(request.GET.get('page', request.session.get('concept_page', 1)), 1)
    search = request.GET.get('search', request.session.get('concept_search', ''))
    show_my_concepts = request.GET.get('show_my_concepts', request.session.get('concept_show_my_concept', 0))
    show_deleted_concepts = request.GET.get('show_deleted_concepts', request.session.get('concept_show_deleted_concepts', 0))
    tag_ids = request.GET.get('tagids', request.session.get('tagids', ''))
    owner = request.GET.get('owner', request.session.get('owner', ''))
    author = request.GET.get('author', request.session.get('author', ''))
    show_only_validated_concepts = request.GET.get('show_only_validated_concepts', request.session.get('show_only_validated_concepts', 0))
    concept_brand = request.GET.get('concept_brand', request.session.get('concept_brand', request.CURRENT_BRAND))

    if request.method == 'POST':
        # get posted parameters
        search = request.POST.get('search', '')
        page_size = request.POST.get('page_size')
        page = request.POST.get('page', page)
        show_my_concepts = request.POST.get('show_my_concepts', 0)
        show_deleted_concepts = request.POST.get('show_deleted_concepts', 0)
        author = request.POST.get('author', '')
        tag_ids = request.POST.get('tagids', '')
        owner = request.POST.get('owner', '')
        show_only_validated_concepts = request.POST.get('show_only_validated_concepts', 0)
        concept_brand = request.POST.get('concept_brand', request.CURRENT_BRAND)


    # store page index variables to session
    request.session['concept_page_size'] = page_size
    request.session['concept_page'] = page
    request.session['concept_search'] = search
    request.session['concept_show_my_concept'] = show_my_concepts
    request.session['concept_show_deleted_concepts'] = show_deleted_concepts
    request.session['author'] = author
    request.session['tagids'] = tag_ids
    request.session['owner'] = owner
    request.session['show_only_validated_concepts'] = show_only_validated_concepts
    request.session['concept_brand'] = concept_brand

    
    if tag_ids:
        # split tag ids into list
        search_tag_list = [int(i) for i in tag_ids.split(",")]
        tags = Tag.objects.filter(id__in=search_tag_list)
        
    # check if it is the public site or not
    if request.user.is_authenticated():
        # ensure that user is only allowed to view/edit the relevant concepts
        concepts = get_visible_concepts(request.user)
           
        # show only concepts created by the current user
        if show_my_concepts == "1":
            concepts = concepts.filter(owner_id=request.user.id)
    
        # if show deleted concepts is 1 then show deleted concepts
        if show_deleted_concepts != "1":
            concepts = concepts.exclude(is_deleted=True)          
        
        # apply tags
        if tag_ids: 
            concepts = concepts.filter(concepttagmap__tag__id__in=search_tag_list)
        
    else:
        # published concepts
        # show published concepts
        # work on concept.history and make sure it is in published concept
        all_published_history_id = list(PublishedConcept.objects.all().values_list('concept_history_id', flat=True))
        published_concepts = Concept.history.filter(history_id__in = all_published_history_id)
        if published_concepts.count() == 0:
            # redirect to login page if no published concepts
            return HttpResponseRedirect(settings.LOGIN_URL)

        concepts = published_concepts
        

    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            concepts = concepts.filter(name__icontains=search)


    if owner is not None:
        if owner !='':
            if User.objects.filter(username__iexact = owner.strip()).exists():
                owner_id = User.objects.get(username__iexact = owner.strip()).id
                concepts = concepts.filter(owner_id = owner_id)
            else:
                concepts = concepts.filter(owner_id = -1)
        
    if author is not None:
        if author != '':
            concepts = concepts.filter(author__icontains=author)
                    


    # if show_only_validated_concepts is 1 then show only concepts with validation_performed=True
    if show_only_validated_concepts == "1":
        concepts = concepts.filter(validation_performed=True)

    # show concepts for a specific brand
    if concept_brand != "":
        current_brand = Brand.objects.all().filter(name = concept_brand)
        concepts = concepts.filter(group__id__in = list(current_brand.values_list('groups', flat=True)))


    if request.user.is_authenticated():    
        # order by id
        concepts = concepts.order_by('id')
        
        # Run through the concepts and add a 'can edit this concept' field, etc.
        for concept in concepts:
            concept.can_edit = allowed_to_edit(request.user, Concept, concept.id)
            concept.publish_date = None
            concept.history_id = Concept.objects.get(pk=concept.id).history.latest().history_id
    else:
        # published concepts
        
        # apply tags
        # I don't like this way, maybe remove search by tags from public site
        if tag_ids:
            for concept in concepts:
                concept_tags_history = db_utils.getHistoryTags(concept.id, concept.history_date)
                if concept_tags_history:
                    concept_tag_list = [i['tag_id'] for i in concept_tags_history if 'tag_id' in i]
                    if not any(t in set(search_tag_list) for t in set(concept_tag_list)):
                        concepts = concepts.exclude(id=concept.id, history_id=concept.history_id)             
                else:
                    concepts = concepts.exclude(id=concept.id, history_id=concept.history_id)    
                    
        
        # for each concept_id get max historical_id
        published_concepts_ids = list(concepts.all().values_list('id', flat=True).distinct().order_by())
        published_concepts_history_ids = list(concepts.all().values_list('history_id', flat=True).distinct().order_by())
        max_historical_ids = list(PublishedConcept.objects.all().filter(concept_id__in = published_concepts_ids 
                                                                        , concept_history_id__in = published_concepts_history_ids
                                                                        ).values('concept_id').annotate(max_id=Max('concept_history_id')
                                                                                                        ).values_list('max_id', flat=True)
                                )

        # get the latest version for each published concept (with search criteria)
        concepts = concepts.filter(history_id__in=max_historical_ids).order_by('id')
    
        # publish_date
        for concept in concepts:
            concept.publish_date = PublishedConcept.objects.get(concept_id=concept.id, concept_history_id=concept.history_id).created
            concept.can_edit = False
       
       
        
    # create pagination
    paginator = Paginator(concepts, page_size, allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    return render(request, 'clinicalcode/concept/index.html', {
        'page': page,
        'page_size': str(page_size),
        'page_obj': p,
        'search': search,
        'author': author,
        'show_my_concepts': show_my_concepts,
        'show_deleted_concepts': show_deleted_concepts,
        'tags': tags,
        'owner': owner,
        'show_only_validated_concepts': show_only_validated_concepts,
        'allowed_to_create': not settings.CLL_READ_ONLY,
        'concept_brand': concept_brand
    })


@login_required
def concept_tree(request, pk):
    '''
        display parent and child tree views
    '''
    concept = Concept.objects.get(pk=pk)

    return render(request, 'clinicalcode/concept/tree.html', {'pk': pk, 'name': concept.name })


@login_required
def concept_upload_codes(request, pk):
    '''
        Upload a set of codes for a concept.
    '''
    validate_access_to_edit(request.user, Concept, pk)
    form_class = ConceptUploadForm
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
                        codes = list(csv.reader(concept_upload_file, delimiter=','))
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
                                if(first_row_has_column_headings == 'on'
                                   and row_count == 1):
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
                                component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT,
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
                                if(first_row_has_column_headings == 'on'
                                   and row_count == 1):
                                    continue
                                obj, created = Code.objects.get_or_create(
                                    code_list=code_list,
                                    code=row[code_col],
                                    defaults={
                                            'description': row[code_desc_col]
                                        }
                                    )
                            ## Now save the concept with a change reason.
                            #db_utils.saveConceptWithChangeReason(pk, "Created component: %s" % upload_name)
                            

                        # if the concept level depth is 1 and it has categories,
                        # then create a code list for each category and populate
                        # each category with related codes.
                        if concept_level_depth == 1 and cat_col:
                            for cat in categories:
                                # Create a component, a code-list, a regex and codes.
                                component = Component.objects.create(
                                    comment=cat,
                                    component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT,
                                    concept=current_concept,
                                    created_by=request.user,
                                    logical_type=logical_type,
                                    name=cat)
                                code_list = CodeList.objects.create(
                                    component=component,
                                    description=cat)
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
                                    if (first_row_has_column_headings == 'on'
                                       and row_count == 1):
                                        continue
                                    # Check here for the category matching the stripped category,
                                    # but don't worry if the category is written to the description
                                    # with the trailing space.
                                    if row[cat_lookup_field].strip() == cat:
                                        obj, created = Code.objects.get_or_create(
                                            code_list=code_list,
                                            code=row[code_col],
                                            defaults={
                                                    'description': row[code_desc_col]
                                                }
                                            )

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
                                    validation_performed=current_concept.validation_performed,
                                    validation_description=current_concept.validation_description,
                                    publication_doi=current_concept.publication_doi,
                                    publication_link=current_concept.publication_link,
                                    secondary_publication_links=current_concept.secondary_publication_links,
                                    paper_published=current_concept.paper_published,
                                    source_reference=current_concept.source_reference,
                                    citation_requirements=current_concept.citation_requirements,
                                    created_by=request.user,
                                    modified_by=request.user,
                                    owner=request.user,     #current_concept.owner,
                                    group=current_concept.group,
                                    owner_access=current_concept.owner_access,
                                    group_access=current_concept.group_access,
                                    world_access=current_concept.world_access,
                                    coding_system=current_concept.coding_system,
                                    is_deleted=current_concept.is_deleted)
                                # Create a new concept component and attach
                                # it to the original concept.
                                component_main = Component.objects.create(
                                            comment=cat,
                                            component_type=Component.COMPONENT_TYPE_CONCEPT,
                                            concept=current_concept,
                                            concept_ref=new_concept,
                                            created_by=request.user,
                                            logical_type=1,
                                            name="%s component" % cat,
                                            concept_ref_history_id = new_concept.history.latest().pk 
                                            )
                                row_count = 0
                                # get unique set of sub categories for the current category
                                for row in codes:
                                    row_count += 1
                                    if (first_row_has_column_headings == 'on'
                                       and row_count == 1):
                                        continue
                                    # get a list of unique sub-category names
                                    # Need to check stripped category.
                                    if(row[cat_lookup_field].strip() == cat):
                                        sub_categories.add(row[sub_cat_lookup_field].strip())
                                for sub_cat in sub_categories:
                                    component = Component.objects.create(
                                        comment=sub_cat,
                                        component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT,
                                        concept=new_concept,
                                        created_by=request.user,
                                        logical_type=logical_type,
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
                                        if(first_row_has_column_headings == 'on'
                                           and row_count == 1):
                                            continue
                                        # Need to check stripped sub-category.
                                        if row[cat_lookup_field].strip() == cat and row[sub_cat_lookup_field].strip() == sub_cat:
                                            obj, created = Code.objects.get_or_create(
                                                code_list=code_list,
                                                code=row[code_col],
                                                defaults={
                                                        'description': row[code_desc_col]
                                                    }
                                                )
                                # save child-concept codes
                                db_utils.save_child_concept_codes(concept_id = current_concept.pk,
                                                                component_id = component_main.pk,
                                                                referenced_concept_id = new_concept.pk,
                                                                concept_ref_history_id = new_concept.history.latest().pk,
                                                                insert_or_update = 'insert'
                                                                )
                                
                    #components = Component.objects.filter(concept_id=pk)
                    # save the concept with a change reason to reflect the restore within the concept audit history
                    db_utils.saveConceptWithChangeReason(pk,
                        "Codes uploaded: %s" % upload_name)
                    # Update dependent concepts & working sets
                    db_utils.saveDependentConceptsChangeReason(pk, "Component concept #" + str(pk) + " was updated")
                            
                    data = dict()
                    data['form_is_valid'] = True
                    
                    # refresh component list
                    data['html_component_list'] = render_to_string(
                        'clinicalcode/component/partial_component_list.html',
                        build_permitted_components_list(request.user, pk)
                        )
                    
                    concept = Concept.objects.get(id=pk)
                    
                    # update history list
                    data['html_history_list'] = render_to_string(
                            'clinicalcode/concept/partial_history_list.html',
                            {'history': concept.history.all(),
                             'current_concept_history_id': concept.history.latest().pk,
                             'published_historical_ids': list(PublishedConcept.objects.filter(concept_id=pk).values_list('concept_history_id', flat=True))
                            },
                            request=request
                            )
                    
                    data['latest_history_ID'] = concept.history.latest().pk
                    
                    # update add_menu_items to reflect latest history id
                    data['add_menu_items'] = render_to_string(
                        'clinicalcode/concept/add_menu_items.html',
                        {'pk': pk, 'latest_history_id': concept.history.latest().pk})
                    
                    return JsonResponse(data)
            except Exception as e:
                data = dict()
                data['exception'] = sys.exc_info()[0]
                data['form_is_valid'] = False
                data['html_form'] = render_to_string('clinicalcode/concept/upload.html',
                                                     {'pk': pk, 'form': form_class},
                                                     request)
                
                #------------------------------       
                concept = Concept.objects.get(id=pk)
                data['latest_history_ID'] = concept.history.latest().pk if request.POST.get('latest_history_id_shown') is None else request.POST.get('latest_history_id_shown')
                #------------------------------
        
                return JsonResponse(data)
            
            

    concept = Concept.objects.get(id=pk)
    return render(request,
                  'clinicalcode/concept/upload.html',
                  {'pk': pk,
                   'form': form_class,
                   'latest_history_ID': concept.history.latest().pk
                   })

@login_required
def concept_codes_to_csv(request, pk):
    """
        Return a csv file of distinct codes for a concept group
    """     
    db_utils.validate_access_to_view(request.user, Concept, pk)
    
    #exclude(is_deleted=True)
    if Concept.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")          
        #raise permission_denied # although 404 is more relevant
        
    current_concept = Concept.objects.get(pk=pk)
        
    user_can_export = (allowed_to_view_children(request.user, Concept, pk)
                        and
                        db_utils.chk_deleted_children(request.user, Concept, pk, returnErrors = False)
                        and 
                        not current_concept.is_deleted 
                      )
    if not user_can_export:
        return HttpResponseNotFound("Not found.") 
        #raise PermissionDenied
    
    
    rows = db_utils.getGroupOfCodesByConceptId(pk)

    my_params = {
        'id': pk,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="concept_%(id)s_group_codes_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)
    titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']
    writer.writerow(titles)
    
    for row in rows:
        writer.writerow([
            row['code'], #.encode('ascii', 'ignore').decode('ascii'),
            row['description'].encode('ascii', 'ignore').decode('ascii'),
            pk,
            current_concept.history.latest().history_id,
            current_concept.name,
        ])
    return response


def history_concept_codes_to_csv(request, pk, concept_history_id):
    """
        Return a csv file of distinct codes for a specific historical concept version
    """     

    # validate access for login and public site
    if request.user.is_authenticated():
        db_utils.validate_access_to_view(request.user, Concept, pk)
    else:
        if not Concept.objects.filter(id=pk).exists(): 
            raise PermissionDenied


    if concept_history_id is not None:
        if not Concept.history.filter(id=pk, history_id=concept_history_id).exists():
            raise PermissionDenied

        
#     if concept_history_id is None:
#         # get the latest version
#         concept_history_id = int(Concept.objects.get(pk=pk).history.latest().history_id) 
        
    is_published = PublishedConcept.objects.filter(concept_id=pk, concept_history_id=concept_history_id).exists()
    if not request.user.is_authenticated():
        # check if the concept version is published
        if not is_published: 
            raise PermissionDenied 
    
    #----------------------------------------------------------------------
    
    #exclude(is_deleted=True)
    if Concept.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")          
        #raise permission_denied # although 404 is more relevant
        
    if Concept.history.filter(id=pk , history_id=concept_history_id).count() == 0:
        return HttpResponseNotFound("Not found.")          
        #raise permission_denied # although 404 is more relevant
        
    current_concept = Concept.objects.get(pk=pk)
        
    if request.user.is_authenticated():
        user_can_export = (allowed_to_view_children(request.user, Concept, pk, set_history_id=concept_history_id)
                            and
                            db_utils.chk_deleted_children(request.user, Concept, pk, returnErrors = False, set_history_id=concept_history_id)
                            and 
                            not current_concept.is_deleted 
                          )
    else:
        user_can_export = is_published
        
    if not user_can_export:
        return HttpResponseNotFound("Not found.") 
        #raise PermissionDenied
    
    history_concept = db_utils.getHistoryConcept(concept_history_id)
    
    rows = db_utils.getGroupOfCodesByConceptId_HISTORICAL(pk, concept_history_id)

    my_params = {
        'id': pk,
        'concept_history_id': concept_history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="concept_%(id)s_ver_%(concept_history_id)s_group_codes_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)
    titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']
    writer.writerow(titles)
    
    for row in rows:
        writer.writerow([
            row['code'], #.encode('ascii', 'ignore').decode('ascii'),
            row['description'].encode('ascii', 'ignore').decode('ascii'),
            pk,
            concept_history_id,
            history_concept['name'],
        ])
    return response


@login_required
def check_concurrent_concept_update(request, pk):
    # Alert user when concurrent editing of concept (components)

    latest_history_id_shown = request.GET.get('latest_history_id_shown' , "").strip()
    component_id = request.GET.get('component_id' , "").strip()
    
    noConflict = True
    confirm_overrideVersion = 0
    context = {}
    
    # Check if the concept is not deleted 
    if(pk.strip() != ""):
        if (not Concept.objects.filter(pk = pk).exists()
           or not Concept.objects.filter(pk = pk).exclude(is_deleted=True).exists()):
            confirm_overrideVersion = -1
            noConflict = False
            context['errorMsg'] = [mark_safe("This concept is deleted,\n (maybe by another user with edit permission).\n please Cancel and Return to index page.")]
    
    
    # Check if the component is not deleted 
    if noConflict:
        if(component_id.strip() != ""):
            if not Component.objects.filter(pk = component_id).exists():
                confirm_overrideVersion = -1
                noConflict = False
                context['errorMsg'] = [mark_safe("This concept component is deleted,\n (maybe by another user with edit permission).\n please Cancel and Refresh concept page.")]

    # Check if the concept was concurrently updated
    if noConflict:
        concept = Concept.objects.get(pk=pk)
        latest_history_id = str(concept.history.latest().history_id)
           
        if latest_history_id_shown != latest_history_id: 
            confirm_overrideVersion = -2
            noConflict = False
            context['errorMsg'] = [mark_safe("This concept has an updated version,\n Do you want to continue and override it?!\n To override click OK.")]
        else:
            context['successMsg'] = ["No Concurrent update."]
           
    context['noConflict'] = noConflict
    context['overrideVersion'] = confirm_overrideVersion

    return JsonResponse(context)

@login_required
def choose_concepts_to_compare(request):
   
    return render(request, 'clinicalcode/concept/choose_concepts_to_compare.html',
                  {
                  }
                )
    
@login_required
def compare_concepts_codes(request, concept_id, version_id, concept_ref_id, version_ref_id):
    
    validate_access_to_view(request.user, Concept, concept_id)
    validate_access_to_view(request.user, Concept, concept_ref_id)
    
    # checking access to child concepts is not needed here
    # allowed_to_view_children(request.user, Concept, pk)
    # chk_deleted_children(request.user, Concept, pk, returnErrors = False)

    
    
    
    main_concept = Concept.objects.get(pk=concept_id)
    ref_concept = Concept.objects.get(pk=concept_ref_id)
    
    if (main_concept.is_deleted==True or ref_concept.is_deleted==True): 
        return render(request, 'custom-msg.html', {'msg_title': 'Data Not found.'} )
    
    if (main_concept.history.filter(id=concept_id, history_id=version_id).count()==0 #.exclude(is_deleted=True)
        or
        ref_concept.history.filter(id=concept_ref_id, history_id=version_ref_id).count()==0 #.exclude(is_deleted=True)
        ):
        return render(request, 'custom-msg.html', {'msg_title': 'Data Not found.'} )
    
    
    main_concept_history_version = main_concept.history.get(id=concept_id, history_id=version_id)
    ref_concept_history_version = ref_concept.history.get(id=concept_ref_id, history_id=version_ref_id)
    
    
        
    main_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id = concept_id,
                                                       concept_history_id = version_id)
    
    if not main_codes:
        main_codes = [{'code': 'No CODES !!' , 'description': ''}]
        
    #main_name = main_concept.name + " - (" + str(concept_id) + "/" + str(version_id) + ") - " + main_concept.author
    # get data from version history
    main_name = (main_concept_history_version.name 
                 + "<BR>(" + str(concept_id) + "/" + str(version_id) + ") " 
                 + "<BR>author: " + main_concept_history_version.author)
    
    
    #----------------------------------
    ref_codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id = concept_ref_id,
                                                       concept_history_id = version_ref_id)
    if not ref_codes:
        ref_codes = [{'code': 'No CODES !!' , 'description': ''}]
        
    #ref_name = ref_concept.name + " - (" + str(concept_ref_id) + "/" + str(version_ref_id) + ") - " + ref_concept.author
    # get data from version history
    ref_name = (ref_concept_history_version.name 
                + "<BR>(" + str(concept_ref_id) + "/" + str(version_ref_id) + ") " 
                + "<BR>author: " + ref_concept_history_version.author)
              


    main_df = pd.DataFrame.from_dict(main_codes)
    ref_df = pd.DataFrame.from_dict(ref_codes)
         
    full_outer_join_df = pd.merge(main_df,
                                  ref_df,
                                  on="code",
                                  how="outer",
                                  indicator=True)
    
    full_outer_join_df = full_outer_join_df.sort_values(by=['_merge'], ascending=False)  
    # replace NaN with '-'
    #full_outer_join_df['description_x'].fillna('-')
    #full_outer_join_df['description_y'].fillna('-')
    
    is_identical = False
    msg = "The two concepts' codes are not identical"
    merge_col_distinct = list(full_outer_join_df['_merge'].unique())
    if len(merge_col_distinct) == 1 and merge_col_distinct == ['both']:
        is_identical = True
        msg = "The two concepts' codes are identical"
    
    
    columns = ['code' , 'description_x', 'description_y', 'merge']
    rows = [tuple(r) for r in full_outer_join_df.to_numpy()] 
    net_comparison = [
            dict(zip(columns, row))
            for row in rows
        ]
              
            
    return render(request,
                    'clinicalcode/concept/compare_cocepts_codes.html', 
                    {'concept_id': concept_id, 
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
    


class ConceptPublish(LoginRequiredMixin, HasAccessToViewConceptCheckMixin, TemplateResponseMixin, View):
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
    
        if(Concept.objects.get(id=pk).is_deleted == True): 
            allow_to_publish = False
            concept_is_deleted = True
        
        if(Concept.objects.filter(Q(id=pk), Q(owner=self.request.user)).count() == 0):
            allow_to_publish = False
            is_owner = False
            
        if(len(db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=pk, concept_history_id=concept_history_id)) == 0):
            allow_to_publish = False
            concept_has_codes = False
        
        has_child_concepts, child_concepts_OK, AllnotDeleted, AllarePublished, isAllowedtoViewChildren, errors = checkAllChildConcepts4Publish_Historical(request, pk, concept_history_id)
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
        is_published = db_utils.checkIfPublished(pk, concept_history_id)
        
        if not is_published:
            self.checkConceptTobePublished(request, pk, concept_history_id)
        #--------------------------------------------

        
        return self.render_to_response({'pk': pk, 
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
        
        is_published = db_utils.checkIfPublished(pk, concept_history_id)
        if not is_published:
            self.checkConceptTobePublished(request, pk, concept_history_id)

        data = dict()
        
        if not allow_to_publish or is_published:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {}, self.request)            
            return JsonResponse(data)
        
        try:
            if allow_to_publish and not is_published:
                # start a transaction
                with transaction.atomic():
                    concept = Concept.objects.get(pk=pk)
                    published_concept = PublishedConcept(concept=concept, 
                                                        concept_history_id=concept_history_id, 
                                                        created_by=request.user)
                    published_concept.save()
                    data['form_is_valid'] = True
                    data['latest_history_ID'] = concept_history_id  #concept.history.latest().pk

#                     # refresh component list
#                     data['html_component_list'] = render_to_string(
#                         'clinicalcode/component/partial_component_list.html',
#                         build_permitted_components_list(self.request.user, pk)
#                         )
        
        
                    # update history list

                    data['html_history_list'] = render_to_string(
                            'clinicalcode/concept/partial_history_list.html',
                            {'history': concept.history.all(),
                             'current_concept_history_id': int(concept_history_id),  #concept.history.latest().pk,
                             'published_historical_ids': list(PublishedConcept.objects.filter(concept_id=pk).values_list('concept_history_id', flat=True))
                            },
                            request=self.request
                        )
                                        
#                     # update add_menu_items to reflect latest history id
#                     data['add_menu_items'] = render_to_string(
#                             'clinicalcode/concept/add_menu_items.html',
#                             {'pk': pk, 
#                              'latest_history_id': concept_history_id    #concept.history.latest().pk
#                             }
#                         )
            
                    data['message'] = render_to_string('clinicalcode/concept/published.html',
                                                       {'id': pk, 'concept_history_id': concept_history_id}
                                                       , self.request)
                    
        except Exception as e:
            data['form_is_valid'] = False
            data['message'] = render_to_string('clinicalcode/error.html',
                                               {}, self.request)
        
        return JsonResponse(data)

#---------------------------------------------------------------------------
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
        if(isDeleted):
            errors[concept[0]] = 'Child concept ('+str(concept[0])+') is deleted'
            AllnotDeleted = False
            
    AllarePublished = True
    for concept in child_concepts_versions:
        is_published = False         
        is_published = db_utils.checkIfPublished(concept[0], concept[1])
        if(not is_published):
            errors[str(concept[0])+'/'+str(concept[1])] = 'Child concept ('+str(concept[0])+'/'+str(concept[1])+') is not published'
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
        if request.user.is_superuser:
            permitted = True
        else:
            permitted |= Concept.objects.filter(Q(id=concept[0]), Q(world_access=Permissions.VIEW)).count() > 0
            permitted |= Concept.objects.filter(Q(id=concept[0]), Q(world_access=Permissions.EDIT)).count() > 0
            permitted |= Concept.objects.filter(Q(id=concept[0]), Q(owner_access=Permissions.VIEW, owner=request.user)).count() > 0
            permitted |= Concept.objects.filter(Q(id=concept[0]), Q(owner_access=Permissions.EDIT, owner=request.user)).count() > 0
            for group in request.user.groups.all() :
                permitted |= Concept.objects.filter(Q(id=concept[0]), Q(group_access=Permissions.VIEW, group_id=group)).count() > 0
                permitted |= Concept.objects.filter(Q(id=concept[0]), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0
            if (not permitted):
                errors[str(concept[0])+'_view'] = 'Child concept ('+str(concept[0])+') is not permitted.'             
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
 

