'''
    ---------------------------------------------------------------------------
    COMPONENT EXPRESSION VIEW

    View-handling for the Expression Component pop-ups.
    ---------------------------------------------------------------------------
'''

import csv
import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .. import db_utils, utils
from ..forms.CodeForms import CodeRegexFormSet
from ..forms.ComponentForms import ComponentForm
from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.CodeRegex import CodeRegex
from ..models.CodingSystemFilter import CodingSystemFilter
from ..models.Component import Component
from ..models.Concept import Concept
from ..models.PublishedConcept import PublishedConcept
from ..permissions import *
from ..views.View import build_permitted_components_list

logger = logging.getLogger(__name__)


class ComponentExpressionCreate(LoginRequiredMixin,
                                HasAccessToEditParentConceptCheckMixin,
                                CreateView):
    '''
        Create a expression component.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/expression/create.html'

    def dispatch(self, request, *args, **kwargs):
        '''
            kwargs - a dict with {'concept_id': value}.
        '''
        return CreateView.dispatch(self, request, kwargs['concept_id'])

    def get_context_data(self, **kwargs):
        context = CreateView.get_context_data(self, **kwargs)

        if self.request.POST:
            context['coderegex_formset'] = CodeRegexFormSet(self.request.POST)
        else:
            context['coderegex_formset'] = CodeRegexFormSet()

        concept = Concept.objects.get(id=self.kwargs['concept_id'])

        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID
        context[
            'latest_history_ID'] = latest_history_ID if self.request.POST.get(
                'latest_history_id_shown') is None else self.request.POST.get(
                    'latest_history_id_shown')
        #-------------------------------

        return context

    def get_initial(self):
        initials = CreateView.get_initial(self)
        try:
            initials['concept'] = Concept.objects.get(
                id=self.kwargs['concept_id'])
        except ObjectDoesNotExist:
            # no concept found, todo: need to log errors
            print('does not exist')

        initials['component_type'] = '%s' % (
            Component.COMPONENT_TYPE_EXPRESSION)

        return initials

    def form_invalid(self, form):
        data = dict()

        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/expression/create.html',
            context=self.get_context_data(form=form),
            request=self.request)

        #------------------------------
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest(
        ).pk if self.request.POST.get(
            'latest_history_id_shown') is None else self.request.POST.get(
                'latest_history_id_shown')
        #------------------------------

        return JsonResponse(data)

    @transaction.atomic
    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['coderegex_formset']

        if formset.is_valid():
            form.instance.created_by = self.request.user
            # !!! Can we do this in one step?
            # !!! self.object = form.save()
            # !!! formset.instance = self.object
            formset.instance = form.save()

            concept = Concept.objects.get(pk=self.kwargs['concept_id'])
            coding_system = concept.coding_system

            # save code regex
            code_regex = formset.save()

            # save the code list
            code_list = CodeList(component=form.instance)
            code_list.save()

            # apply the code list reference to the code regex
            code_regex[0].code_list = code_list
            code_regex[0].save()

            # get where query
            db_utils.create_expression_codes(
                Component.COMPONENT_TYPE_EXPRESSION,
                coding_system.database_connection_name,
                coding_system.table_name, coding_system.code_column_name,
                coding_system.desc_column_name, '', '',
                formset.instance.coderegex.column_search,
                formset.instance.coderegex.regex_type,
                formset.instance.coderegex.regex_code, code_list.id,
                self.request.user.id, coding_system.filter,
                formset.instance.coderegex.case_sensitive_search)

            # Save the concept with a change reason to reflect the creation
            # within the concept audit history.
            db_utils.save_Entity_With_ChangeReason(
                Concept,
                self.kwargs['concept_id'],
                "Created component: %s" % (form.instance.name),
                modified_by_user=self.request.user)
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(
                self.kwargs['concept_id'], "Component concept #" +
                str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
            data['form_is_valid'] = True

            concept = Concept.objects.get(pk=self.kwargs['concept_id'])

            # refresh component list
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                build_permitted_components_list(self.request,
                                                self.kwargs['concept_id']))

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
                            concept_id=self.kwargs['concept_id']).values_list(
                                'concept_history_id', flat=True))
                },
                request=self.request)

            data['latest_history_ID'] = concept.history.latest().pk

            # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html', {
                    'pk': self.kwargs['concept_id'],
                    'latest_history_id': concept.history.latest().pk
                })

        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/expression/create.html',
                context=self.get_context_data(form=form),
                request=self.request)

        return JsonResponse(data)


class ComponentExpressionDelete(LoginRequiredMixin,
                                HasAccessToEditParentConceptCheckMixin,
                                DeleteView):
    '''
        Delete an expression component.
    '''
    model = Component
    template_name = 'clinicalcode/component/expression/delete.html'

    def post(self, request, *args, **kwargs):
        '''
            kwargs - a dict with {'pk': value, 'concept_id': value}.
        '''
        with transaction.atomic():
            data = dict()
            component = get_object_or_404(Component, id=kwargs['pk'])
            component_name = component.name
            component.delete()
        #components = Component.objects.filter(concept_id=component.concept_id)
        # Save the *concept* with a change reason to note the component
        # deletion in its history.
        db_utils.save_Entity_With_ChangeReason(
            Concept,
            kwargs['concept_id'],
            "Deleted component: %s" % (component_name),
            modified_by_user=self.request.user)
        # Update dependent concepts & working sets
        db_utils.saveDependentConceptsChangeReason(
            kwargs['concept_id'],
            "Component concept #" + str(kwargs['concept_id']) + " was updated")

        data['form_is_valid'] = True

        # refresh component list
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(self.request,
                                            self.kwargs['concept_id']))

        concept = Concept.objects.get(id=kwargs['concept_id'])

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
                        concept_id=self.kwargs['concept_id']).values_list(
                            'concept_history_id', flat=True))
            },
            request=self.request)

        data['latest_history_ID'] = concept.history.latest().pk

        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html', {
                'pk': self.kwargs['concept_id'],
                'latest_history_id': concept.history.latest().pk
            })

        return JsonResponse(data)


class ComponentExpressionUpdate(LoginRequiredMixin,
                                HasAccessToEditParentConceptCheckMixin,
                                UpdateView):
    '''
        Update match code with expression component.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/expression/update.html'

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)

        if self.request.POST:
            context['coderegex_formset'] = CodeRegexFormSet(
                self.request.POST, instance=self.object)
            context['coderegex_formset'].full_clean()
        else:
            context['coderegex_formset'] = CodeRegexFormSet(
                instance=self.object)

        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID
        context[
            'latest_history_ID'] = latest_history_ID if self.request.POST.get(
                'latest_history_id_shown') is None else self.request.POST.get(
                    'latest_history_id_shown')
        #-------------------------------

        return context

    def form_invalid(self, form):
        data = dict()
        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/expression/update.html',
            context=self.get_context_data(form=form),
            request=self.request)

        #------------------------------
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest(
        ).pk if self.request.POST.get(
            'latest_history_id_shown') is None else self.request.POST.get(
                'latest_history_id_shown')
        #------------------------------

        return JsonResponse(data)

    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['coderegex_formset']
        if formset.is_valid():
            with transaction.atomic():
                form.instance.modified_by = self.request.user
                # !!! See asame code above.
                #     self.object = form.save()
                #     formset.instance = self.object
                formset.instance = form.save()
                code_list_id = self.request.POST.get('coderegex-0-code_list')

                concept = Concept.objects.get(id=self.kwargs['concept_id'])
                coding_system = concept.coding_system

                formset.save()

                db_utils.update_expression_codes(
                    Component.COMPONENT_TYPE_EXPRESSION,
                    coding_system.database_connection_name,
                    coding_system.table_name, coding_system.code_column_name,
                    coding_system.desc_column_name, '', '',
                    formset.instance.coderegex.column_search,
                    formset.instance.coderegex.regex_type,
                    formset.instance.coderegex.regex_code, code_list_id,
                    self.request.user.id, coding_system.filter,
                    formset.instance.coderegex.case_sensitive_search)

                # Save the concept with a change reason to reflect the update
                # within the concept audit history.
                db_utils.save_Entity_With_ChangeReason(
                    Concept,
                    self.kwargs['concept_id'],
                    "Updated component: %s" % (form.instance.name),
                    modified_by_user=self.request.user)
                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(
                    self.kwargs['concept_id'], "Component concept #" +
                    str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])

            data['form_is_valid'] = True

            concept = Concept.objects.get(id=self.kwargs['concept_id'])

            # refresh component list
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                build_permitted_components_list(self.request,
                                                self.kwargs['concept_id']))

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
                            concept_id=self.kwargs['concept_id']).values_list(
                                'concept_history_id', flat=True))
                },
                request=self.request)

            data['latest_history_ID'] = concept.history.latest().pk

            # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html', {
                    'pk': self.kwargs['concept_id'],
                    'latest_history_id': concept.history.latest().pk
                })

        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/expression/update.html',
                context=self.get_context_data(form=form),
                request=self.request)

        return JsonResponse(data)


"""
    !!! Not currently used.
        -------------------
class ComponentExpressionSelectCodeCreate(LoginRequiredMixin,
                                          HasAccessToEditParentConceptCheckMixin,
                                          CreateView):
    '''
        Create an expression-select code component.
    '''
    model = Code
    form_class = CodeForm
    template_name = 'clinicalcode/component/expressionselect/code/create.html'

    def get_initial(self):
        initials = CreateView.get_initial(self)
        try:
            initials['code_list'] = CodeList.objects.get(id=self.kwargs['code_list_id'])
        except ObjectDoesNotExist:
            # no code list found, todo: need to log errors
            print('does not exist')

        return initials

    def get_context_data(self, **kwargs):
        context = CreateView.get_context_data(self, **kwargs)

        context['concept_id'] = self.kwargs.get('concept_id')
        context['code_list_id'] = self.kwargs.get('code_list_id')

        return context

    def form_invalid(self, form):
        data = dict()
        # check if code has already been used
        if Code.objects.filter(
            Q(code=form.cleaned_data['code'],
              code_list_id=self.kwargs['code_list_id'])).count() > 0:
            form.add_error(None, forms.ValidationError('Code is already used'))

        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/expressionselect/code/create.html',
            context=self.get_context_data(form=form),
            request=self.request)
        return JsonResponse(data)

    def form_valid(self, form):
        data = dict()

        # check if code has already been used
        if Code.objects.filter(
            Q(code=form.cleaned_data['code'],
              code_list_id=self.kwargs['code_list_id'])).count() > 0:
            form.add_error(None, forms.ValidationError('Code is already used'))

            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/expressionselect/code/create.html',
                context=self.get_context_data(form=form),
                request=self.request)
            return JsonResponse(data)

        with transaction.atomic():
            form.save()

            code_list = CodeList.objects.get(id=self.kwargs['code_list_id'])

            # get and process any uploaded files
            if self.request.FILES.get('upload_file'):
                csv_file = self.request.FILES['upload_file']
                #file_reader = csv.reader(csv_file, delimiter=',')
                file_reader = csv.reader([line.decode() for line in csv_file], delimiter=',')

                row_count = 0

                for row in file_reader:
                    row_count += 1

                    # check if first row contains column headings or not
                    if (self.request.POST.get('first_row_contains_column_headings_checkbox') == '1'
                        and row_count == 1):
                        continue
                    # !!! obj is not used?
                    obj = Code.objects.create(code_list=code_list,
                                              code=row[0],
                                              description=row[1])

            # save the concept with a change reason to reflect the creation
            # within the concept audit history
            db_utils.save_Entity_With_ChangeReason(Concept, self.kwargs['concept_id'],
                "Created code %s for component: %s" %
                (form.instance.code, code_list.component.name) , modified_by_user=self.request.user)
                
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(self.kwargs['concept_id'], "Component concept #" + str(self.kwargs['concept_id']) + " was updated")

        #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
        data['form_is_valid'] = True
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(self.request, self.kwargs['concept_id'])
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

        return JsonResponse(data)
"""


class ComponentExpressionSelectCreate(LoginRequiredMixin,
                                      HasAccessToEditParentConceptCheckMixin,
                                      CreateView):
    '''
        Create a expression select component.
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/expressionselect/create.html'

    def dispatch(self, request, *args, **kwargs):
        '''
            kwargs - a dict with {'concept_id': value}.
        '''
        return CreateView.dispatch(self, request, kwargs['concept_id'])

    def get_context_data(self, **kwargs):
        context = CreateView.get_context_data(self, **kwargs)

        if self.request.POST:
            context['coderegex_formset'] = CodeRegexFormSet(self.request.POST)
        else:
            context['coderegex_formset'] = CodeRegexFormSet()

        concept = Concept.objects.get(id=self.kwargs['concept_id'])

        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID
        context[
            'latest_history_ID'] = latest_history_ID if self.request.POST.get(
                'latest_history_id_shown') is None else self.request.POST.get(
                    'latest_history_id_shown')
        #-------------------------------

        return context

    def get_initial(self):
        initials = CreateView.get_initial(self)
        try:
            initials['concept'] = Concept.objects.get(
                id=self.kwargs['concept_id'])
        except ObjectDoesNotExist:
            # no concept found, todo: need to log errors
            print('does not exist')

        initials['component_type'] = '%s' % (
            Component.COMPONENT_TYPE_EXPRESSION_SELECT)

        return initials

    def form_invalid(self, form):
        data = dict()

        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/expressionselect/create.html',
            context=self.get_context_data(form=form),
            request=self.request)

        #------------------------------
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest(
        ).pk if self.request.POST.get(
            'latest_history_id_shown') is None else self.request.POST.get(
                'latest_history_id_shown')
        #------------------------------

        return JsonResponse(data)

    @transaction.atomic
    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['coderegex_formset']

        if formset.is_valid():
            form.instance.created_by = self.request.user
            # !!! self.object appears unnecessary, as above.
            # self.object = form.save()
            # formset.instance = self.object
            formset.instance = form.save()

            # save code regex
            code_regex = formset.save()

            # save the code list
            code_list = CodeList(component=form.instance)
            code_list.save()

            # apply the code list reference to the code regex
            code_regex[0].code_list = code_list
            code_regex[0].save()

            # process any uploaded files
            if self.request.FILES.get('upload_file'):
                csv_file = self.request.FILES['upload_file']
                #file_reader = csv.reader(csv_file, delimiter=',')
                file_reader = csv.reader([line.decode() for line in csv_file],
                                         delimiter=',')

                row_count = 0
                for row in file_reader:
                    row_count += 1

                    # check if first row contains column headings or not
                    if (self.request.POST.get(
                            'first_row_contains_column_headings_checkbox')
                            == '1' and row_count == 1):
                        continue

                    # !!! Do we need to assign these: obj, created =
                    Code.objects.get_or_create(
                        code_list=code_list,
                        code=row[0],
                        defaults={'description': row[1]})

            # get codes to be saved
            codes = json.loads(self.request.POST.get('added_codes'))

            # create codes
            for val in codes:
                # !!! Do we need to assign this: obj =
                Code.objects.create(code_list=code_list,
                                    code=val['code'],
                                    description=val['description'])

            # save the concept with a change reason to reflect the creation
            # within the concept audit history
            db_utils.save_Entity_With_ChangeReason(
                Concept,
                self.kwargs['concept_id'],
                "Created component: %s" % (form.instance.name),
                modified_by_user=self.request.user)
            # Update dependent concepts & working sets
            db_utils.saveDependentConceptsChangeReason(
                self.kwargs['concept_id'], "Component concept #" +
                str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])
            data['form_is_valid'] = True

            # refresh component list
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                build_permitted_components_list(self.request,
                                                self.kwargs['concept_id']))

            concept = Concept.objects.get(id=self.kwargs['concept_id'])

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
                            concept_id=self.kwargs['concept_id']).values_list(
                                'concept_history_id', flat=True))
                },
                request=self.request)

            data['latest_history_ID'] = concept.history.latest().pk

            # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html', {
                    'pk': self.kwargs['concept_id'],
                    'latest_history_id': concept.history.latest().pk
                })

        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/expressionselect/create.html',
                context=self.get_context_data(form=form),
                request=self.request)

        return JsonResponse(data)


class ComponentExpressionSelectDelete(LoginRequiredMixin,
                                      HasAccessToEditParentConceptCheckMixin,
                                      DeleteView):
    '''
        Delete an expression select component.
    '''
    model = Component
    template_name = 'clinicalcode/component/expressionselect/delete.html'

    def post(self, request, *args, **kwargs):
        '''
            kwargs - a dict with {'pk': value, 'concept_id': value}.
        '''
        with transaction.atomic():
            data = dict()
            component = get_object_or_404(Component, id=kwargs['pk'])
            component_name = component.name
            component.delete()
        #components = Component.objects.filter(concept_id=component.concept_id)
        # Save the *concept* with a change reason to note the component
        # deletion in its history.
        db_utils.save_Entity_With_ChangeReason(
            Concept,
            kwargs['concept_id'],
            "Deleted component: %s" % (component_name),
            modified_by_user=self.request.user)
        # Update dependent concepts & working sets
        db_utils.saveDependentConceptsChangeReason(
            kwargs['concept_id'],
            "Component concept #" + str(kwargs['concept_id']) + " was updated")

        data['form_is_valid'] = True

        # refresh component list
        data['html_component_list'] = render_to_string(
            'clinicalcode/component/partial_component_list.html',
            build_permitted_components_list(self.request,
                                            self.kwargs['concept_id']))

        concept = Concept.objects.get(id=component.concept_id)

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
                        concept_id=component.concept_id).values_list(
                            'concept_history_id', flat=True))
            },
            request=self.request)

        data['latest_history_ID'] = concept.history.latest().pk

        # update add_menu_items to reflect latest history id
        data['add_menu_items'] = render_to_string(
            'clinicalcode/concept/add_menu_items.html', {
                'pk': self.kwargs['concept_id'],
                'latest_history_id': concept.history.latest().pk
            })

        return JsonResponse(data)


class ComponentExpressionSelectUpdate(LoginRequiredMixin,
                                      HasAccessToEditParentConceptCheckMixin,
                                      UpdateView):
    '''
        Update a expression select component
    '''
    model = Component
    form_class = ComponentForm
    template_name = 'clinicalcode/component/expressionselect/update.html'

    def get_context_data(self, **kwargs):
        context = UpdateView.get_context_data(self, **kwargs)
        if self.request.POST:
            context['coderegex_formset'] = CodeRegexFormSet(
                self.request.POST, instance=self.object)
            context['coderegex_formset'].full_clean()
        else:
            context['coderegex_formset'] = CodeRegexFormSet(
                instance=self.object)
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        context['coding_system_filter'] = CodingSystemFilter.objects.filter(
            coding_system_id=concept.coding_system_id)

        #------------------------------
        latest_history_ID = concept.history.latest().pk
        #context['latest_history_ID'] = latest_history_ID
        context[
            'latest_history_ID'] = latest_history_ID if self.request.POST.get(
                'latest_history_id_shown') is None else self.request.POST.get(
                    'latest_history_id_shown')
        #-------------------------------

        return context

    def form_invalid(self, form):
        data = dict()
        data['form_is_valid'] = False
        data['html_form'] = render_to_string(
            'clinicalcode/component/expressionselect/update.html',
            context=self.get_context_data(form=form),
            request=self.request)

        #------------------------------
        concept = Concept.objects.get(id=self.kwargs['concept_id'])
        data['latest_history_ID'] = concept.history.latest(
        ).pk if self.request.POST.get(
            'latest_history_id_shown') is None else self.request.POST.get(
                'latest_history_id_shown')
        #------------------------------

        return JsonResponse(data)

    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        formset = context['coderegex_formset']
        if formset.is_valid():
            with transaction.atomic():
                form.instance.modified_by = self.request.user
                # !!! self.object appears unnecessary, as above.
                # self.object = form.save()
                # formset.instance = self.object
                formset.instance = form.save()

                code_list_id = self.request.POST.get('coderegex-0-code_list')

                formset.save()

                # process any uploaded files
                if self.request.FILES.get('upload_file'):
                    csv_file = self.request.FILES['upload_file']
                    #file_reader = csv.reader(csv_file, delimiter=',')
                    file_reader = csv.reader(
                        [line.decode() for line in csv_file], delimiter=',')

                    row_count = 0
                    for row in file_reader:
                        row_count += 1

                        # check if first row contains column headings or not
                        if (self.request.POST.get(
                                'first_row_contains_column_headings_checkbox')
                                == '1' and row_count == 1):
                            continue

                        # !!! Do we need to assign theses: obj, created =
                        Code.objects.get_or_create(
                            code_list_id=code_list_id,
                            code=row[0],
                            defaults={'description': row[1]})

                # find the matched and non matched items
                added_codes = json.loads(self.request.POST.get('added_codes'))
                deleted_codes = json.loads(
                    self.request.POST.get('deleted_codes'))

                # delete old codes
                for code in deleted_codes:
                    codes_to_del = Code.objects.filter(
                        code_list_id=code_list_id, code=code['code'])

                    for code_to_del in codes_to_del:
                        try:
                            code_to_del.delete()
                        except ObjectDoesNotExist:
                            code_to_del = None

                # add new codes
                for code in added_codes:
                    codes_to_add = Code.objects.filter(
                        code_list_id=code_list_id, code=code['code'])

                    if not codes_to_add:
                        Code.objects.create(
                            code_list=CodeList.objects.get(pk=code_list_id),
                            code=code['code'],
                            description=code['description'])

                # save the concept with a change reason to reflect the update
                # within the concept audit history
                db_utils.save_Entity_With_ChangeReason(
                    Concept,
                    self.kwargs['concept_id'],
                    "Updated component: %s" % (form.instance.name),
                    modified_by_user=self.request.user)
                # Update dependent concepts & working sets
                db_utils.saveDependentConceptsChangeReason(
                    self.kwargs['concept_id'], "Component concept #" +
                    str(self.kwargs['concept_id']) + " was updated")

            #components = Component.objects.filter(concept_id=self.kwargs['concept_id'])

            data['form_is_valid'] = True
            # refresh component list
            data['html_component_list'] = render_to_string(
                'clinicalcode/component/partial_component_list.html',
                build_permitted_components_list(self.request,
                                                self.kwargs['concept_id']))

            concept = Concept.objects.get(id=self.kwargs['concept_id'])

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
                            concept_id=self.kwargs['concept_id']).values_list(
                                'concept_history_id', flat=True))
                },
                request=self.request)

            data['latest_history_ID'] = concept.history.latest().pk

            # update add_menu_items to reflect latest history id
            data['add_menu_items'] = render_to_string(
                'clinicalcode/concept/add_menu_items.html', {
                    'pk': self.kwargs['concept_id'],
                    'latest_history_id': concept.history.latest().pk
                })

        else:
            data['form_is_valid'] = False
            data['html_form'] = render_to_string(
                'clinicalcode/component/expressionselect/update.html',
                context=self.get_context_data(form=form),
                request=self.request)

        return JsonResponse(data)


def component_history_expression_detail_combined(request, pk, concept_id,
                                                 concept_history_id,
                                                 component_history_id):
    '''
        Display the detail of a code regex component at a point in time.
        (both for public and app pages)

        The parameters are returned from the URL.
        pk - The id of the component to be detailed.
        concept_id - The concept.
        concept_history_id - The historical version of the concept.
        component_history_id - The historical version of the component.
    '''

    # validate access for login and public site
    validate_access_to_view(request,
                            Concept,
                            concept_id,
                            set_history_id=concept_history_id)

    if not Component.history.filter(
            Q(id=pk), Q(history_id=component_history_id),
            Q(concept_id=concept_id), ~Q(history_type='-')).exists():
        raise PermissionDenied

    #----------------------------------------------------------------------

    concept = db_utils.getHistoryConcept(concept_history_id)
    concept_history_date = concept['history_date']

    component = db_utils.getHistoryComponentByHistoryId(component_history_id)
    coderegex = db_utils.getHistoryCodeRegex(component['id'],
                                             concept_history_date)
    codelist = db_utils.getHistoryCodeListById(coderegex['code_list_id'],
                                               concept_history_date)
    if codelist is not None:
        codes = db_utils.getHistoryCodes(codelist['id'], concept_history_date)
    else:
        codes = []

    return render(
        request, 'clinicalcode/component/expression/detail_combined.html', {
            'component': component,
            'coderegex': coderegex,
            'codelist': codelist,
            'codes': json.dumps(codes)
        })


@login_required
def component_expression_searchcodes(request, concept_id):
    '''
        Search for codes using a pattern string either %patt% or a regex.
        !!! (1) Case-sensitivity --- seems to ignore lower-case.
        !!! (2) Should we do %patt% by default?
        !!! (3) How do we do whole-word only, e.g. search for PSA not xxxPSAxxx? Not quite % PSA %?
    '''
    validate_access_to_view(request, Concept, concept_id)
    concept = Concept.objects.get(id=concept_id)
    coding_system = concept.coding_system
    codes = db_utils.search_codes(
        Component.COMPONENT_TYPE_EXPRESSION,
        coding_system.database_connection_name, coding_system.table_name,
        coding_system.code_column_name, coding_system.desc_column_name,
        request.POST.get('search_text'), request.POST.get('search_params'),
        utils.get_int_value(request.POST.get('column_search'), -1),
        utils.get_int_value(request.POST.get('logical_type'), -1),
        utils.get_int_value(request.POST.get('regex_type'), -1),
        request.POST.get('regex_code'), coding_system.filter,
        utils.get_bool_value(request.POST.get('case_sensitive_search'), False))
    return JsonResponse(codes, safe=False)


@login_required
def component_expressionselect_codes(request, concept_id, code_list_id):
    '''
        Return a list of codes based on code list id.
    '''

    codes = list(Code.objects.filter(code_list_id=code_list_id).values())

    return JsonResponse(serializers.serialize('json', codes), safe=False)


@login_required
def component_expressionselect_search_codes(request, concept_id):
    '''
        Search code select regex codes by regex_code.
    '''

    validate_access_to_view(request, Concept, concept_id)

    # logical_type, regex_type
    # get coding system for the current concept
    concept = Concept.objects.get(id=concept_id)

    coding_system = concept.coding_system

    codes = db_utils.search_codes(
        Component.COMPONENT_TYPE_EXPRESSION_SELECT,
        coding_system.database_connection_name, coding_system.table_name,
        coding_system.code_column_name, coding_system.desc_column_name,
        request.POST.get('search_text'), request.POST.get('search_params'),
        utils.get_int_value(request.POST.get('column_search'), -1),
        utils.get_int_value(request.POST.get('logical_type'), -1),
        utils.get_int_value(request.POST.get('regex_type'), -1),
        request.POST.get('regex_code'), coding_system.filter,
        utils.get_bool_value(request.POST.get('case_sensitive_search'), False))

    return JsonResponse(codes, safe=False)


def component_history_expressionselect_detail_combined(request, pk, concept_id,
                                                       concept_history_id,
                                                       component_history_id):
    '''
        Display the detail of a expression select at a point in time.
    '''

    # validate access for login and public site
    validate_access_to_view(request,
                            Concept,
                            concept_id,
                            set_history_id=concept_history_id)

    if not Component.history.filter(
            Q(id=pk), Q(history_id=component_history_id),
            Q(concept_id=concept_id), ~Q(history_type='-')).exists():
        raise PermissionDenied

    #----------------------------------------------------------------------
    concept = db_utils.getHistoryConcept(concept_history_id)
    concept_history_date = concept['history_date']

    component = db_utils.getHistoryComponentByHistoryId(component_history_id)
    coderegex = db_utils.getHistoryCodeRegex(component['id'],
                                             concept_history_date)
    codelist = db_utils.getHistoryCodeListByComponentId(
        component['id'], concept_history_date)

    if codelist is not None:
        codes = db_utils.getHistoryCodes(codelist['id'], concept_history_date)
    else:
        codes = []

    return render(
        request,
        'clinicalcode/component/expressionselect/detail_combined.html', {
            'component': component,
            'coderegex': coderegex,
            'codelist': codelist,
            'codes': json.dumps(codes)
        })
