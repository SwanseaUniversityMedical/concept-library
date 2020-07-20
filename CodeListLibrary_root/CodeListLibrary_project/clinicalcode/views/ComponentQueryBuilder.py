'''
    ---------------------------------------------------------------------------
    COMPONENT QUERY BUILDER VIEW

    View-handling for the Queru Builder Component pop-ups.
    ---------------------------------------------------------------------------
'''

# import csv
# import binascii
import json
import logging
# from datetime import datetime
# from rest_framework.permissions import BasePermission
# from simple_history.models import HistoricalRecords
# from StringIO import StringIO
# import time
# import code
# import clinicalcode
# from pyasn1.compat.octets import null
# from collections import OrderedDict

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin #, UserPassesTestMixin
# from django.contrib import messages
# from django.contrib.messages import constants
# from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist #, PermissionDenied
# from django.core.paginator import Paginator, EmptyPage
# from django.core.urlresolvers import reverse_lazy, reverse
# from django.db.models import Q
from django.db import transaction #, models, IntegrityError
# from django.forms.models import model_to_dict
# from django.http import HttpResponseRedirect #, StreamingHttpResponse, HttpResponseForbidden
from django.http.response import JsonResponse #, HttpResponse
from django.shortcuts import get_object_or_404, render #, redirect, render_to_response
# from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic import DetailView
# from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from ..views.View import build_permitted_components_list
# from clinicalcode.views.View import *
from ..permissions import (
    validate_access_to_edit,
    HasAccessToViewParentConceptCheckMixin,
    HasAccessToEditParentConceptCheckMixin)

from .. import db_utils
from .. import utils

from ..constants import (
    REGEX_TYPE_SIMPLE
)

from ..forms.CodeForms import CodeListFormSet #, CodeRegexFormSet, CodeForm
from ..forms.ComponentForms import ComponentForm
# from ..forms.ConceptForms import ConceptForm, ConceptUploadForm

#from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.CodeRegex import CodeRegex
from ..models.CodingSystemFilter import CodingSystemFilter
from ..models.Component import Component
from ..models.Concept import Concept
# from ..models.ConceptTagMap import ConceptTagMap
# from ..models.Tag import Tag
# from ..models.WorkingSet import WorkingSet
# from ..models.WorkingSetTagMap import WorkingSetTagMap

logger = logging.getLogger(__name__)

'''
COM_TYPE_CONCEPT_DESC = 'Concept'
COM_TYPE_QUERY_BUILDER_DESC = 'Query builder'
COM_TYPE_EXPRESSION_DESC = 'Match code with expression'
COM_TYPE_EXPRESSION_SELECT_DESC = 'Select codes individually + import codes'
'''

class ComponentQueryBuilderCreate(LoginRequiredMixin,
                                  HasAccessToEditParentConceptCheckMixin,
                                  CreateView):
    '''
        Create a query builder component.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/querybuilder/create.html'

    def get_context_data(self, **kwargs):
        context = super(ComponentQueryBuilderCreate, self).get_context_data(**kwargs)

        if self.request.POST:
            context['codelist_formset'] = CodeListFormSet(self.request.POST)
        else:
            context['codelist_formset'] = CodeListFormSet()

        concept = Concept.objects.get(id=self.kwargs['concept_id'])

        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID 
        context['latest_history_ID'] = latest_history_ID if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #-------------------------------
        
        return context

    def get_initial(self):
        initials = CreateView.get_initial(self)

        try:
            initials['concept'] = Concept.objects.get(id=self.kwargs['concept_id'])
        except ObjectDoesNotExist:
            print('Concept for the component does not exist')

        initials['component_type'] = '%s' % (Component.COMPONENT_TYPE_QUERY_BUILDER)

        return initials

    def form_invalid(self, form):
        data = dict()

        # validate for sql injection
        if utils.has_sql_injection(self.request.POST.get('search_params')):
            form.add_error(None, forms.ValidationError(
                'The system has identified a potential security issue with your query.'))

        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/querybuilder/create.html',
            context=self.get_context_data(form=form),
            request=self.request)

        #------------------------------       
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest().pk if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #------------------------------
        
        return JsonResponse(data)

    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['codelist_formset']

        # validate for sql injection
        if utils.has_sql_injection(self.request.POST.get('search_params')):
            form.add_error(None, forms.ValidationError(
                'The system has identified a potential security issue with your query.'))

        if form.is_valid() and formset.is_valid():

            with transaction.atomic():
                form.instance.created_by = self.request.user
                # !!! object not needed?
                # self.object = form.save()
                # formset.instance = self.object
                formset.instance = form.save()
                code_lists = formset.save()
                code_list = code_lists[0]

                concept = Concept.objects.get(pk=self.kwargs['concept_id'])
                coding_system = concept.coding_system

                if self.request.POST.get('search_params') is not None:
                    search_params = json.loads(self.request.POST.get('search_params'))
                else:
                    search_params = JsonResponse([], safe=False)

                # get where query
                db_utils.create_codelist_codes(
                    Component.COMPONENT_TYPE_QUERY_BUILDER,
                    coding_system.database_connection_name,
                    coding_system.table_name,
                    coding_system.code_column_name,
                    coding_system.desc_column_name,
                    self.request.POST.get('search_text'),
                    search_params,
                    '',
                    CodeRegex.SIMPLE,
                    '',
                    code_list.id,
                    self.request.user.id,
                    coding_system.filter,
                    case_sensitive_search = False)

                # save the concept with a change reason to reflect the code
                # list addition within the concept audit history
                db_utils.saveConceptWithChangeReason(self.kwargs['concept_id'],
                    "Created component: %s" % (form.instance.name) , modified_by_user=self.request.user)
                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(self.kwargs['concept_id'], "Component concept #" + str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
            data['form_is_valid'] = True

            # update component list
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                #{'components': components}
                build_permitted_components_list(self.request.user, self.kwargs['concept_id'])
                )

            concept = Concept.objects.get(pk=self.kwargs['concept_id'])

            # update history list
            data['html_history_list'] = render_to_string(
                'clinicalcode/concept/partial_history_list.html',
                {'history': concept.history.all()})
            
            data['latest_history_ID'] = concept.history.latest().pk
            
             # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html',
                {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})

        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/querybuilder/create.html',
                context=self.get_context_data(form=form),
                request=self.request)

        return JsonResponse(data)


class ComponentQueryBuilderDelete(LoginRequiredMixin,
                                  HasAccessToEditParentConceptCheckMixin,
                                  DeleteView):
    '''
        Delete a query builder component.
    '''
    model = Component
    template_name = 'clinicalcode/component/querybuilder/delete.html'

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
                
        #components = Component.objects.filter(concept_id=component.concept_id)
        data['form_is_valid'] = True
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            #{'components': components}
            build_permitted_components_list(self.request.user, self.kwargs['concept_id'])
            )
        concept = Concept.objects.get(id=component.concept_id)
        data['html_history_list'] = render_to_string(
            'clinicalcode/concept/partial_history_list.html',
            {'history': concept.history.all()})
        
        data['latest_history_ID'] = concept.history.latest().pk
        
        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html',
            {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})

        return JsonResponse(data)


class ComponentQueryBuilderDetail(LoginRequiredMixin,
                                  HasAccessToViewParentConceptCheckMixin,
                                  DetailView):
    '''
        Produce a query builder component detail page.
        This is used in the pop-up displays in the concept components views.
    '''
    model = Component
    template_name = 'clinicalcode/component/querybuilder/detail.html'

    def get_context_data(self, **kwargs):
        context = DetailView.get_context_data(self, **kwargs)
        codelist = CodeList.objects.get(component=self.object)
        codes = codelist.codes.order_by('code')
        context['codes'] = json.dumps(list(codes.values('code', 'description')))
        context['codelist'] = codelist
        return context


class ComponentQueryBuilderUpdate(LoginRequiredMixin,
                                  HasAccessToEditParentConceptCheckMixin,
                                  UpdateView):
    '''
        Update a query builder component.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/querybuilder/update.html'

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)

        if self.request.POST:
            context['codelist_formset'] = CodeListFormSet(self.request.POST, instance=self.object)
            context['codelist_formset'].full_clean()
        else:
            context['codelist_formset'] = CodeListFormSet(instance=self.object)

        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID 
        context['latest_history_ID'] = latest_history_ID if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #-------------------------------
        
        return context

    def form_invalid(self, form):
        data = dict()

        if utils.has_sql_injection(self.request.POST.get('search_params')):
            form.add_error(None, forms.ValidationError(
                'The system has identified a potential security issue with your query.'))

        data['form_is_valid'] = False
        data['html_form'] = render_to_string('clinicalcode/component/querybuilder/update.html',
                                             context=self.get_context_data(form=form),
                                             request=self.request)
        
        #------------------------------       
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest().pk if self.request.POST.get('latest_history_id_shown') is None else self.request.POST.get('latest_history_id_shown')
        #------------------------------
        
        return JsonResponse(data)

    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['codelist_formset']

        if formset.is_valid():

            if utils.has_sql_injection(self.request.POST.get('search_params')):
                form.add_error(None, forms.ValidationError(
                    'The system has identified a potential security issue with your query.'))

                data['form_is_valid'] = False
                data['html_form'] = render_to_string(
                    'clinicalcode/component/querybuilder/update.html',
                    context=self.get_context_data(form=form),
                    request=self.request)

                return JsonResponse(data)

            with transaction.atomic():
                code_list_id = form.data['codelist-0-id']

                form.instance.modified_by = self.request.user

                # !!! Unnecessary object creation.
                # self.object = form.save()
                # formset.instance = self.object
                formset.instance = form.save()

                concept = Concept.objects.get(pk=self.kwargs['concept_id'])
                coding_system = concept.coding_system

                formset.save()

                if self.request.POST.get('search_params') is not None:
                    search_params = json.loads(self.request.POST.get('search_params'))
                else:
                    search_params = JsonResponse([], safe=False)

                # get where query
                db_utils.update_codelist_codes(
                    Component.COMPONENT_TYPE_QUERY_BUILDER,
                    coding_system.database_connection_name,
                    coding_system.table_name,
                    coding_system.code_column_name,
                    coding_system.desc_column_name,
                    self.request.POST.get('search_text'),
                    search_params,
                    '',
                    CodeRegex.SIMPLE,
                    '',
                    code_list_id,
                    self.request.user.id,
                    coding_system.filter,
                    case_sensitive_search = False)

                # save the concept with a change reason to reflect the update
                # within the concept audit history
                db_utils.saveConceptWithChangeReason(self.kwargs['concept_id'],
                    "Updated component: %s" % (form.instance.name) , modified_by_user=self.request.user)
                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(self.kwargs['concept_id'], "Component concept #" + str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
            data['form_is_valid'] = True
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                #{'components': components}
                build_permitted_components_list(self.request.user, self.kwargs['concept_id'])
                )

            concept = Concept.objects.get(pk=self.kwargs['concept_id'])

            # update history list
            data['html_history_list'] = render_to_string(
                'clinicalcode/concept/partial_history_list.html',
                {'history': concept.history.all()})
            
            data['latest_history_ID'] = concept.history.latest().pk

            # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html',
                {'pk': self.kwargs['concept_id'], 'latest_history_id': concept.history.latest().pk})


            if self.request.POST.get('action') == 'SaveContinue':
                data['html_form'] = render_to_string(
                    'clinicalcode/component/querybuilder/update.html',
                    context=self.get_context_data(form=form),
                    request=self.request)
        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/querybuilder/update.html',
                context=self.get_context_data(form=form),
                request=self.request)
        return JsonResponse(data)


@login_required
def component_querybuilder_search(request, concept_id):
    '''
        Return a list of codes based on search_text
    '''
    data = dict()
    is_valid = True

    concept = Concept.objects.get(pk=concept_id)
    coding_system = concept.coding_system

    # validate for sql injection
    try:
        if utils.has_sql_injection(request.POST.get('search_params')):
            is_valid = False
            data['error_message'] = 'The system has identified a potential security issue with your query.'
    # !!! Should we be catching a specific exception here?
    except Exception as e:
        is_valid = False
        data['error_message'] = 'Parameters error (' + str(e).replace("'", "\'") + ').'

    if request.POST.get('search_params') is not None:
        search_params = json.loads(request.POST.get('search_params'))
    else:
        is_valid = False
        data['error_message'] = 'No parameters have been specified.'

    if is_valid:
        try:
            data['codes'] = db_utils.search_codes(
                Component.COMPONENT_TYPE_QUERY_BUILDER,
                coding_system.database_connection_name,
                coding_system.table_name,
                coding_system.code_column_name,
                coding_system.desc_column_name,
                request.POST.get('search_text'),
                search_params,
                -1,
                utils.get_int_value(request.POST.get('logical_type'), -1),
                REGEX_TYPE_SIMPLE,
                '',
                coding_system.filter)
        # !!! Should we be catching a specific exception here?
        except Exception as e:
            is_valid = False
            data['error_message'] = 'Parameters error (' + str(e).replace("'", "\'") + ').'

    data['is_valid'] = is_valid

    #------------------------------       
    concept = Concept.objects.get(id=concept_id)
    latest_history_id_shown = str(request.POST.get('latest_history_id_shown'))
    data['latest_history_id_shown'] = concept.history.latest().pk if latest_history_id_shown.strip() == "" else latest_history_id_shown
    #------------------------------
        
    return JsonResponse(data, safe=False)

@login_required
def component_history_querybuilder_detail(request,
                                          pk,
                                          concept_id,
                                          concept_history_id,
                                          component_history_id):
    '''
        Display the detail of a query builder component at a point in time.

        The parameters are returned from the URL.
        pk - The id of the component to be detailed.
        concept_id - The concept.
        concept_history_id - The historical version of the concept.
        component_history_id - The historical version of the component.
    '''
    validate_access_to_edit(request.user, Concept, concept_id)

    concept = db_utils.getHistoryConcept(concept_history_id)
    concept_history_date = concept['history_date']

    component = db_utils.getHistoryComponentByHistoryId(component_history_id)
    codelist = db_utils.getHistoryCodeListByComponentId(component['id'], concept_history_date)

    if codelist is not None:
        codes = db_utils.getHistoryCodes(codelist['id'], concept_history_date)
    else:
        codes = []

    return render(request,
                  'clinicalcode/component/querybuilder/history/detail.html',
                  {'component': component, 'codelist': codelist,
                   'codes': json.dumps(codes)}
                 )
