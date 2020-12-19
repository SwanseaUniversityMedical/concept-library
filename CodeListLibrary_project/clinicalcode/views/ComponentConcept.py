'''
    ---------------------------------------------------------------------------
    COMPONENT CONCEPT VIEW

    View-handling for the Concept Component pop-ups.
    ---------------------------------------------------------------------------
'''

import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.http.response import JsonResponse
from django.db.models import Q

from .. import db_utils
from .. import utils

from ..forms.ComponentForms import ComponentForm

#from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.Component import Component
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept

from ..views.View import build_permitted_components_list
from ..permissions import *

from django.core.exceptions import  PermissionDenied

import json
logger = logging.getLogger(__name__)


class ComponentConceptCreate(LoginRequiredMixin,
                             HasAccessToEditParentConceptCheckMixin,
                             CreateView):
    '''
        Create a concept component for a concept.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/concept/create.html'


    def get_initial(self):
        initials = CreateView.get_initial(self)
        try:
            initials['concept'] = Concept.objects.get(id=self.kwargs['concept_id'])
        except ObjectDoesNotExist:
            print('Concept does not exist')
        initials['component_type'] = '%s' % (Component.COMPONENT_TYPE_CONCEPT)
        return initials


    def form_invalid(self, form):
        data = dict()
        if form.cleaned_data['concept_ref'] is None:
            form.add_error(None, forms.ValidationError('Concept is required'))
           
        if db_utils.hasCircularReference (child_concept_id=form.cleaned_data['concept_ref'].pk, parent_concept_id=form.instance.concept_id):
            form.add_error(None, forms.ValidationError('Circular Reference: this concept is a parent of the main concept(id='+str(form.instance.concept_id)+')'))
            
        if db_utils.hasConcurrentUdates(concept_id=form.instance.concept_id, shown_version_id=0):
            form.add_error(None, forms.ValidationError('This concept  (id='+str(form.instance.concept_id)+') has an updated version, Do you want to continue and override it?!'))
                
        #------------------------------
        concept = Concept.objects.get(pk=form.instance.concept_id)
        context = self.get_context_data(form=form)
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID 
        context['latest_history_ID'] = latest_history_ID if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #-------------------------------
        
        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/concept/create.html',
            context=context,   #self.get_context_data(form=form),
            request=self.request)
        return JsonResponse(data)


    def form_valid(self, form):
        data = dict()
        
        isValidForm = True
        if form.cleaned_data['concept_ref'] is None:
            form.add_error(None, forms.ValidationError('Concept is required'))
            isValidForm = False

        if db_utils.hasCircularReference (child_concept_id=form.cleaned_data['concept_ref'].pk, parent_concept_id=form.instance.concept_id):
            form.add_error(None, forms.ValidationError('Circular Reference: this concept is a parent of the main concept(id='+str(form.instance.concept_id)+')'))
            isValidForm = False
                
        if db_utils.hasConcurrentUdates(concept_id=form.instance.concept_id, shown_version_id=0):
            form.add_error(None, forms.ValidationError('This concept  (id='+str(form.instance.concept_id)+') has an updated version, Do you want to continue and override it?!'))
            isValidForm = False
            
        #------------------------------
        concept = Concept.objects.get(pk=form.instance.concept_id)
        context = self.get_context_data(form=form)
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID 
        context['latest_history_ID'] = latest_history_ID if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #-------------------------------
            
        if not isValidForm:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/concept/create.html',
                context=context,   #self.get_context_data(form=form),
                request=self.request)
            return JsonResponse(data)
        
        
        referenced_concept = form.cleaned_data['concept_ref']
        #form.instance.concept_ref_history = referenced_concept.history.latest() #?? need to be feeded
        form.instance.concept_ref_history = Concept.history.get(id=referenced_concept.pk, history_id=self.request.POST.get('child_history_id'))
        with transaction.atomic():
            form.instance.created_by = self.request.user
            # Save the component.
            #form.save()
            self.object = form.save()
            # save codelist/codes under the child concept component directly
            db_utils.save_child_concept_codes(concept_id = self.kwargs['concept_id'], 
                                    component_id = self.object.pk,
                                    referenced_concept_id = referenced_concept.pk, 
                                    concept_ref_history_id = form.instance.concept_ref_history.pk,
                                    insert_or_update = 'insert' )
            
            # Save the concept containing this component with new history.
            db_utils.saveConceptWithChangeReason(self.kwargs['concept_id'],
                "Created component %s" % (form.instance.name) , modified_by_user=self.request.user)
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(form.instance.concept_id, "Component concept #" + str(form.instance.concept_id) + " was updated")
            
        data['form_is_valid'] = True
        
        # refresh component list
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(self.request.user, self.kwargs['concept_id']))
        
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        
        # update history list
        data['html_history_list'] = render_to_string(
            'clinicalcode/concept/partial_history_list.html',
            {'history': concept.history.all(),
             'current_concept_history_id': concept.history.latest().pk,
             'published_historical_ids': list(PublishedConcept.objects.filter(concept_id=self.kwargs['concept_id']).values_list('concept_history_id', flat=True))             
            },
            request=self.request
            )
        
        data['latest_history_ID'] = concept.history.latest().pk
        
        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html',
            {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})
            
            
        return JsonResponse(data)


class ComponentConceptDelete(LoginRequiredMixin,
                             HasAccessToEditParentConceptCheckMixin,
                             DeleteView):
    '''
        Delete a concept component from a concept.
    '''
    model = Component
    template_name = 'clinicalcode/component/concept/delete.html'

    def post(self, request, *args, **kwargs):
        '''
            kwargs - a dict with {'pk': value, 'concept_id': value}.
        '''
        data = dict()
        with transaction.atomic():
            component = get_object_or_404(Component, id=kwargs['pk'])
            component_name = component.name
            component.delete()
            # Save the *concept* with a change reason to note the component
            # deletion in its history.
            db_utils.saveConceptWithChangeReason(kwargs['concept_id'],
                "Deleted component: %s" % (component_name) , modified_by_user=self.request.user)
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(kwargs['concept_id'], "Component concept #" + str(kwargs['concept_id']) + " was updated")
            
        data['form_is_valid'] = True
        
        # refresh component list
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(request.user, kwargs['concept_id']))
        
        concept = Concept.objects.get(id=kwargs['concept_id'])
        
        # update history list
        data['html_history_list'] = render_to_string(
            'clinicalcode/concept/partial_history_list.html',
            {'history': concept.history.all(),
             'current_concept_history_id': concept.history.latest().pk,
             'published_historical_ids': list(PublishedConcept.objects.filter(concept_id=self.kwargs['concept_id']).values_list('concept_history_id', flat=True))             
            },
            request=self.request
            )
        
        data['latest_history_ID'] = concept.history.latest().pk

        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html',
            {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})
            
        return JsonResponse(data)


class ComponentConceptUpdate(LoginRequiredMixin,
                             HasAccessToEditParentConceptCheckMixin,
                             UpdateView):
    '''
        Update a concept component for a concept.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/concept/update.html'

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)
        component = Component.objects.get(pk=self.kwargs['pk'])
        context.update(build_permitted_components_list(self.request.user, component.concept_id))
#         # Set up the components element again (already done in buildPermittedComponentList)
#         # as we want the components not for this concept but for the referenced concept.
#         context['components'] = list(Component.objects.filter(concept=component.concept_ref_id))
        
        # get the saved codes
        existing_codes = []
        code_list = CodeList.objects.get(component=component)
        if code_list is not None:
            existing_codes = code_list.codes.order_by('code')           
        
        codes = existing_codes
        codes_count = "0"
        try:
            codes_count = str(len(codes))
        except:
            codes_count = "0"
        context['codes_count'] = codes_count
        context['codes'] = codes
        
        # show latest version of the child concept for comparison
        context['concept_ref_lates_version_id'] = Concept.objects.get(pk=component.concept_ref_id).history.latest().pk
        context['concept_ref_deleted'] = Concept.objects.get(pk=component.concept_ref_id).is_deleted
        context['concept_ref_is_accessible'] = allowed_to_view(self.request.user, Concept, component.concept_ref_id, set_history_id=component.concept_ref_history.pk)

        context['child_history_id'] = component.concept_ref_history.pk
        #------------------------------
        concept = Concept.objects.get(id=component.concept_id) # id=self.kwargs['concept_id']
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID 
        context['latest_history_ID'] = latest_history_ID if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #-------------------------------

        return context


    def form_invalid(self, form):
        data = dict()
        if form.cleaned_data['concept_ref'] is None:
            form.add_error(None, forms.ValidationError('Concept is required'))
        data['form_is_valid'] = False
        data['html_form'] = render_to_string('clinicalcode/component/concept/update.html',
            context=self.get_context_data(form=form),
            request=self.request)
        
        #------------------------------ ???      
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest().pk if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #------------------------------
        
        return JsonResponse(data)


    def form_valid(self, form):
        data = dict()
        
        if form.cleaned_data['concept_ref'] is None:
            form.add_error(None, forms.ValidationError('Concept is required'))

            data['form_is_valid'] = False
            data['html_form'] = render_to_string('clinicalcode/component/concept/update.html',
                context=self.get_context_data(form=form),
                request=self.request)
            return JsonResponse(data)
        

        update_to_latest_version = utils.get_int_value(self.kwargs.get('update_to_latest_version', 0), 0)

        referenced_concept = form.cleaned_data['concept_ref']
        
        if update_to_latest_version == 1:
            form.instance.concept_ref_history = referenced_concept.history.latest()
            
        with transaction.atomic():
            form.instance.modified_by = self.request.user
            # Save the component.
            form.save()           
            
            #---------------------kwargs.get----------------
            if update_to_latest_version == 1:
                # save codelist/codes under the child concept component directly
                db_utils.save_child_concept_codes(concept_id = self.kwargs['concept_id'], 
                                    component_id = self.object.pk,
                                    referenced_concept_id = referenced_concept.pk, 
                                    concept_ref_history_id = form.instance.concept_ref_history.pk,
                                    insert_or_update = 'update' )
            #-------------------------------------
            
            # Save the concept that contains this component with new history.
            db_utils.saveConceptWithChangeReason(self.kwargs['concept_id'],
                "Updated component %s" % (form.instance.name) , modified_by_user=self.request.user)
            
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(form.instance.concept_id, "Component concept #" + str(form.instance.concept_id) + " was updated")
        #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
       
        data['form_is_valid'] = True
        
        # refresh component list
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(self.request.user, self.kwargs['concept_id'])
            )
        
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        
        # update history list
        data['html_history_list'] = render_to_string(
            'clinicalcode/concept/partial_history_list.html',
            {'history': concept.history.all(),
             'current_concept_history_id': concept.history.latest().pk,
             'published_historical_ids': list(PublishedConcept.objects.filter(concept_id=self.kwargs['concept_id']).values_list('concept_history_id', flat=True))             
            },
            request=self.request
            )
        
        data['latest_history_ID'] = concept.history.latest().pk

        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html',
            {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})
            
        return JsonResponse(data)



def component_history_concept_detail_combined(request,
                                             pk,
                                             concept_id,
                                             concept_history_id,
                                             component_history_id):
    '''
        Display the detail of a concept component at a point in time.
        (both for public and app pages)
        
        The parameters are returned from the URL.
        pk - The id of the component to be detailed.
        concept_id - The concept.
        concept_history_id - The historical version of the concept.
        component_history_id - The historical version of the component.
    '''
    # validate access for login and public site
    if request.user.is_authenticated():
        validate_access_to_view(request.user, Concept, concept_id, set_history_id=concept_history_id)
    else:
        if not Concept.objects.filter(id=concept_id).exists(): 
            raise PermissionDenied
    
    if not Concept.history.filter(id=concept_id, history_id=concept_history_id).exists():
        raise PermissionDenied
        
    if not Component.history.filter(Q(id=pk), Q(history_id=component_history_id), Q(concept_id=concept_id), ~Q(history_type = '-')).exists(): 
            raise PermissionDenied
        
    is_published = PublishedConcept.objects.filter(concept_id=concept_id, concept_history_id=concept_history_id).exists()
    if not request.user.is_authenticated():
        # check if the concept version is published
        if not is_published: 
            raise PermissionDenied 
    
    #----------------------------------------------------------------------
    is_latest_version = (int(concept_history_id) == Concept.objects.get(pk=concept_id).history.latest().history_id)

    if request.user.is_authenticated():
        components_permissions = build_permitted_components_list(request.user, concept_id)
        can_edit = (not Concept.objects.get(pk=concept_id).is_deleted) and allowed_to_edit(request.user, Concept, concept_id)
        
    else:
        can_edit = False        
    #----------------------------------------------------------------------
    concept = db_utils.getHistoryConcept(concept_history_id)
    concept_history_date = concept['history_date']

    component = db_utils.getHistoryComponentByHistoryId(component_history_id)

    codelist = db_utils.getHistoryCodeListByComponentId(component['id'], concept_history_date)

    if codelist is not None:
        codes = db_utils.getHistoryCodes(codelist['id'], concept_history_date)
    else:
        codes = []
        
    context = {'component': component, 
               'codelist': codelist,
               'codes': json.dumps(codes)
               }
    
    if request.user.is_authenticated():
        if is_latest_version and (can_edit):
            needed_keys = ['user_can_view_component', 'user_can_edit_component','component_error_msg_view',
                           'component_error_msg_edit', 'component_concpet_version_msg', 'latest_history_id']
            context.update({k: components_permissions[k] for k in needed_keys})
    
            
    return render(request,
                  'clinicalcode/component/concept/detail_combined.html',
                  context
                 )


