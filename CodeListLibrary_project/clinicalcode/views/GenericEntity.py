"""
    ---------------------------------------------------------------------------
    GENERIC-ENTITY VIEW
    ---------------------------------------------------------------------------
"""
from django.urls import reverse
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from collections import OrderedDict
from django.contrib import messages
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.http.response import HttpResponse, JsonResponse, Http404
from django.core.exceptions import BadRequest, PermissionDenied
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from rest_framework.decorators import schema
from django.contrib.auth.decorators import login_required

import csv
import json
import time
import logging

from ..entity_utils import (concept_utils, entity_db_utils, permission_utils,
                            template_utils, gen_utils, model_utils, 
                            create_utils, search_utils, constants)

from clinicalcode.views import View
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.models.Concept import Concept
from clinicalcode.models.Template import Template
from clinicalcode.models.OntologyTag import OntologyTag
from clinicalcode.models.CodingSystem import CodingSystem
from clinicalcode.models.GenericEntity import GenericEntity
from clinicalcode.models.PublishedGenericEntity import PublishedGenericEntity


logger = logging.getLogger(__name__)


class EntitySearchView(TemplateView):
    """
        Entity single search view

        Note:
            Responsibilities:
            - Managing context of template and which entities to render
            - SSR of entities at initial GET request based on request params
            - AJAX-driven update of template based on request params (through JsonResponse)
    """
    template_name = 'clinicalcode/generic_entity/search/search.html'
    result_template = 'components/search/results.html'
    pagination_template = 'components/search/pagination_container.html'

    def get_context_data(self, *args, **kwargs):
        """Provides contextful data to template based on request parameters"""
        context = super(EntitySearchView, self).get_context_data(*args, **kwargs)
        request = self.request

        # Get the renderable, published entities that match our request params & the selected entity_type (optional)
        entity_type_param = kwargs.get('entity_type')
        entity_type = search_utils.try_derive_entity_type(entity_type_param)
        
        # Raise 404 when trying to access an entity class that does not exist
        if entity_type_param is not None and entity_type is None:
            raise Http404

        entities, layouts = search_utils.get_renderable_entities(
            request,
            entity_types=entity_type
        )

        # Paginate reponse
        page_obj = search_utils.try_get_paginated_results(request, entities)

        # For detail referral highlighting
        request.session['searchterm'] = gen_utils.try_get_param(request, 'search', None)

        return context | {
            'entity_type': entity_type,
            'page_obj': page_obj,
            'layouts': layouts
        }
    
    def get(self, request, *args, **kwargs):
        """
            Manages get requests to this view
            
            Note:
                If `search_filtered` is passed as a parameter (through a fetch req),
                the `GET` request will return the pagination and results
                for hotreloading relevant search results instead of forcing
                a page reload.

                In reality, we should change this to a `JSON` Response at some point
                and make the client render it rather than wasting server resources.
        """
        context = self.get_context_data(*args, **kwargs)
        filtered = gen_utils.try_get_param(request, 'search_filtered', None)

        if filtered is not None and request.headers.get('X-Requested-With'):
            context['request'] = request

            results = render_to_string(self.result_template, context)
            pagination = render_to_string(self.pagination_template, context)
            return HttpResponse(results + pagination, content_type='text/plain')
            
        return render(request, self.template_name, context)


@schema(None)
class EntityDescendantSelection(APIView):
    """
        API-like view for internal services to discern template-related information and to retrieve entity descendant data via search.

        TODO:
            Could be moved to API in future?
    """
    fetch_methods = ['get_filters', 'get_results']

    ''' Private methods '''
    def __get_template(self, template_id):
        """Attempts to get the assoc. template if available or raises a bad request"""
        template = model_utils.try_get_instance(Template, pk=template_id)
        if template is None:
            raise BadRequest('Template ID is invalid')
        return template

    ''' View methods '''
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def dispatch(self, request, *args, **kwargs):
        """Dispatch view if not in read-only and user is authenticated"""
        return super(EntityDescendantSelection, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        """Provides contextual data"""
        context = { }
        request = self.request

        template_id = gen_utils.parse_int(kwargs.get('template_id'), default=None)
        if template_id is None:
            raise BadRequest('Invalid request')
        return context | { 'template_id': template_id }
    
    def get(self, request, *args, **kwargs):
        """Handles GET requests made by the client and directs the params to the appropriate method given the fetch target"""
        if gen_utils.is_fetch_request(request):
            method = gen_utils.handle_fetch_request(request, self, *args, **kwargs)
            return method(request, *args, **kwargs)
        raise BadRequest('Invalid request')

    ''' Fetch methods '''
    def get_filters(self, request, *args, **kwargs):
        """Gets the filter specification for this template"""
        context = self.get_context_data(*args, **kwargs)

        template = self.__get_template(context.get('template_id'))
        template_filters = search_utils.get_template_filters(request, template, default=[])
        metadata_filters = search_utils.get_metadata_filters(request)

        return JsonResponse({
            'template': template_filters,
            'metadata': metadata_filters,
        })
    
    def get_results(self, request, *args, **kwargs):
        """Gets the search results for the desired template after applying query params"""
        context = self.get_context_data(*args, **kwargs)
        template_id = context.get('template_id')
        result = search_utils.get_template_entities(request, template_id)
        return JsonResponse(result)


class CreateEntityView(TemplateView):
    """
        Used to create entities
            
        Note:
            - `CreateView` isn't used due to the requirements of having a form dynamically created to reflect the dynamic model.
    """
    fetch_methods = [
        'search_codes', 'get_options', 'import_rule', 'import_concept',
        'query_ontology_typeahead', 'query_ontology_record',
    ]
    templates = {
        'form': 'clinicalcode/generic_entity/creation/create.html',
        'select': 'clinicalcode/generic_entity/creation/select.html'
    }

    ''' View methods '''
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def dispatch(self, request, *args, **kwargs):
        """Dispatch view"""
        return super(CreateEntityView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        """
            @desc Provides contextual data
        """
        context = super(CreateEntityView, self).get_context_data(*args, **kwargs)
        return context
    
    @method_decorator([login_required, permission_utils.redirect_readonly])
    def get(self, request, *args, **kwargs):
        """
            Handles get requests by determining whether it was made through the fetch method, or accessed via a browser.

            Note:
                - If requested via browser, will render a view. Otherwise will respond with appropriate method, if applicable.
        """
        if gen_utils.is_fetch_request(request):
            method = gen_utils.handle_fetch_request(request, self, *args, **kwargs)
            return method(request, *args, **kwargs)
        
        return self.render_view(request, *args, **kwargs)

    @method_decorator([login_required, permission_utils.redirect_readonly])
    def post(self, request, *args, **kwargs):
        """
            Handles form submissions for both:
                - creating
                - updating
        """
        form_errors = []
        form = gen_utils.get_request_body(request)
        form = create_utils.validate_entity_form(request, form, form_errors)

        if form is None:
            # Errors occurred - use the validation errors to generate a comprehensive response
            return gen_utils.jsonify_response(
                code=400,
                status='false',
                message={
                    'type': 'INVALID_FORM',
                    'errors': form_errors
                }
            )
        
        form_errors = []

        entity = create_utils.create_or_update_entity_from_form(request, form, form_errors)
        if entity is None:
            # Errors occurred when building - report the error list
            return gen_utils.jsonify_response(
                code=400,
                status='false',
                message={
                    'type': 'SUBMISSION_ERROR',
                    'errors': form_errors
                }
            )

        return JsonResponse({
            'success': True,
            'entity': { 'id': entity.id, 'history_id': entity.history_id },
            'redirect': reverse('entity_history_detail', kwargs={ 'pk': entity.id, 'history_id': entity.history_id })
        })

    ''' Main view render '''
    def render_view(self, request, *args, **kwargs):
        """
            Template and entity is tokenised in the URL - providing the latter requires users to be permitted to modify that particular entity.

            Note:
                - If no `entity_id` is passed, a creation form is returned, otherwise the user is redirected to an update form.
        """
        context = self.get_context_data(*args, **kwargs)

        # Send to selection page if no template_id and entity_id
        template_id = kwargs.get('template_id')
        entity_id = kwargs.get('entity_id')
        if template_id is None and entity_id is None:
            if not permission_utils.can_user_create_entities(request):
                raise PermissionDenied

            return self.select_form(request, context)

        # Send to create form if template_id is selected
        template_id = gen_utils.parse_int(template_id, default=None)
        if template_id is not None:
            template = model_utils.try_get_instance(Template, pk=template_id)
            if template is None or template.hide_on_create:
                raise Http404

            if not permission_utils.can_user_create_entities(request):
                raise PermissionDenied

            return self.create_form(request, context, template)

        # Send to update form if entity_id is selected
        entity_history_id = gen_utils.parse_int(kwargs.get('entity_history_id'), default=None)
        if entity_id is not None and entity_history_id is not None:
            entity = create_utils.try_validate_entity(request, entity_id, entity_history_id)
            if not entity:
                raise Http404

            template = entity.template
            if template is None:
                raise Http404

            return self.update_form(request, context, template, entity)
        
        # Raise 400 if no param matches views
        raise HttpResponseBadRequest('Invalid request.')
    
    ''' Forms '''
    def select_form(self, request, context):
        """Renders the template selection form"""
        context['entity_data'] = create_utils.get_createable_entities(request)
        return render(request, self.templates.get('select'), context)

    def create_form(self, request, context, template):
        """Renders the entity create form"""
        context['metadata'] = constants.metadata
        context['template'] = template
        context['form_method'] = constants.FORM_METHODS.CREATE
        return render(request, self.templates.get('form'), context)

    def update_form(self, request, context, template, entity):
        """Renders the entity update form"""
        context['metadata'] = constants.metadata
        context['template'] = template
        context['entity'] = entity
        context['object_reference'] = { 'id': entity.id, 'history_id': entity.history_id }
        context['form_method'] = constants.FORM_METHODS.UPDATE
        context['is_historical'] = model_utils.is_legacy_entity(entity.id, entity.history_id)
        context['derived_ownership'] = permission_utils.has_derived_edit_access(request, entity.id, entity.history_id)
        return render(request, self.templates.get('form'), context)

    ''' Fetch methods '''
    def import_rule(self, request, *args, **kwargs):
        """GET request made by client to retrieve the codelist _assoc._ with the concept they are attempting to import as a rule"""
        concept_id = gen_utils.try_get_param(request, 'concept_id')
        concept_version_id = gen_utils.try_get_param(request, 'concept_version_id')
        if concept_id is None or concept_version_id is None:
            raise BadRequest('Parameters are missing')

        concept_id = gen_utils.parse_int(concept_id, None)
        concept_version_id = gen_utils.parse_int(concept_version_id, None)
        if concept_id is None or concept_version_id is None:
            raise BadRequest('Parameter type mismatch')
        
        concept = concept_utils.get_clinical_concept_data(
            concept_id,
            concept_version_id,
            include_component_codes=False,
            aggregate_component_codes=False,
            include_reviewed_codes=True
        )

        return JsonResponse({
            'concept_id': concept_id,
            'concept_version_id': concept_version_id,
            'codelist': concept.get('codelist')
        })
    
    def import_concept(self, request, *args, **kwargs):
        """GET request made by client to retrieve codelists _assoc._ with the concepts they are attempting to import as top-level objects"""
        concept_ids = gen_utils.try_get_param(request, 'concept_ids')
        concept_version_ids = gen_utils.try_get_param(request, 'concept_version_ids')
        if concept_ids is None or concept_version_ids is None:
            raise BadRequest('Parameters are missing')
        
        concept_ids = [gen_utils.parse_int(x) for x in concept_ids.split(',') if gen_utils.parse_int(x) is not None]
        concept_version_ids = [gen_utils.parse_int(x) for x in concept_version_ids.split(',') if gen_utils.parse_int(x) is not None]
        if len(concept_ids) != len(concept_version_ids):
            raise BadRequest('Parameter mismatch')
        
        concepts = [
            concept_utils.get_clinical_concept_data(
                concept[0],
                concept[1],
                aggregate_component_codes=False,
            ) | {
                'has_edit_access': False,
            }
            for concept in zip(concept_ids, concept_version_ids)
        ]
        
        return JsonResponse({
            'concepts': concepts
        })

    def query_ontology_record(self, request, *args, **kwargs):
        """
			Queries ontology node & its ancestry

            See: :func:`~clinicalcode.models.OntologyTag.OntologyTag.get_creation_data~`

			QueryParams:
				node_id     (int): the node id
				type_id (str|int): the node's type id

			Returns:
				An object describing the node and its ancestry if found; otherwise returns an appropriate err

        """
        node_id = gen_utils.try_value_as_type(
            gen_utils.try_get_param(request, 'node_id'),
            'int',
            default=None
        )

        type_id = gen_utils.try_value_as_type(
            gen_utils.try_get_param(request, 'type_id'),
            'int',
            default=None
        )

        if node_id is None or type_id is None:
            return gen_utils.jsonify_response(message='Invalid NodeId and/or TypeId parameter', code=400, status='false')

        result = OntologyTag.build_tree([node_id], None) # OntologyTag.get_creation_data([node_id], [type_id], None)
        if result is None:
            return gen_utils.jsonify_response(message=f'Node<id: {node_id}, type: {type_id}> not found', code=404, status='false')

        return JsonResponse({ 'result': result })

    def query_ontology_typeahead(self, request, *args, **kwargs):
        """
			Autocomplete, typeahead-like web search for Ontology search components

            See: :func:`~clinicalcode.models.OntologyTag.OntologyTag.query_typeahead~`

			Query Params:
				search             (str): some web query search term; defaults to an empty `str`
				type_ids (str|int|int[]): narrow the resultset by specifying the ontology type ids; defaults to `None`

			Returns:
				An array, ordered by search rank, listing each of the matching ontological terms

        """
        searchterm = gen_utils.try_value_as_type(
            gen_utils.try_get_param(request, 'search'),
            'string',
            default=None
        )
        if not isinstance(searchterm, str) or gen_utils.is_empty_string(searchterm):
            return JsonResponse({ 'result': [] })

        type_ids = gen_utils.try_value_as_type(
            gen_utils.try_get_param(request, 'type_ids', default='').split(','),
            'int_array',
            default=None
        )

        if not isinstance(type_ids, list):
            return JsonResponse({ 'result': [] })

        return JsonResponse({ 'result': OntologyTag.query_typeahead(searchterm, type_ids) })

    def get_options(self, request, *args, **kwargs):
        """GET request made by client to retrieve all available options for a given field within its template. Atm, it is exclusively used to retrieve Coding Systems"""
        template_id = gen_utils.parse_int(gen_utils.try_get_param(request, 'template'), default=None)
        if not template_id:
            return gen_utils.jsonify_response(message='Invalid template parameter', code=400, status='false')
        
        template = model_utils.try_get_instance(Template, pk=template_id)
        if template is None:
            return gen_utils.jsonify_response(message='Invalid template parameter, template does not exist', code=400, status='false')
        
        field = gen_utils.try_get_param(request, 'parameter')
        if field is None or gen_utils.is_empty_string(field):
            return gen_utils.jsonify_response(message='Invalid field parameter', code=400, status='false')

        info = template_utils.get_template_field_info(template, field)
        struct = info.get('field')
        if info.get('is_metadata'):
            default_value = None

            if struct is not None:
                validation = template_utils.try_get_content(struct, 'validation')
                if validation is not None:
                    default_value = [] if validation.get('type') == 'int_array' else default_value

            options = template_utils.get_template_sourced_values(constants.metadata, field, request=request, default=default_value, struct=struct)
        else:
            options = template_utils.get_template_sourced_values(template, field, request=request, struct=struct)

        if options is None:
            return gen_utils.jsonify_response(message='Invalid field parameter, does not exist or is not an optional parameter', code=400, status='false')

        options = model_utils.append_coding_system_data(options)
        return JsonResponse({
            'result': options
        })

    def search_codes(self, request, *args, **kwargs):
        """GET request made by client to search a codelist given its coding id, a search term, and the relevant template, _e.g._ `entity/{update|create}/?search=C1&coding_system=4&template=1`"""
        template_id = gen_utils.parse_int(gen_utils.try_get_param(request, 'template'), default=None)
        if not template_id:
            return gen_utils.jsonify_response(message='Invalid template parameter', code=400, status='false')
        
        template = model_utils.try_get_instance(Template, pk=template_id)
        if template is None:
            return gen_utils.jsonify_response(message='Invalid template parameter, template does not exist', code=400, status='false')
        
        search_term = gen_utils.try_get_param(request, 'search', '')
        search_term = gen_utils.decode_uri_parameter(search_term)
        if not search_term or gen_utils.is_empty_string(search_term):
            return gen_utils.jsonify_response(message='Invalid search term parameter', code=400, status='false')
        
        coding_system = gen_utils.parse_int(gen_utils.try_get_param(request, 'coding_system'), None)
        coding_system = model_utils.try_get_instance(CodingSystem, codingsystem_id=coding_system)
        if not coding_system:
            return gen_utils.jsonify_response(message='Invalid coding system parameter', code=400, status='false')

        use_desc = gen_utils.parse_int(gen_utils.try_get_param(request, 'use_desc'), None)
        use_desc = use_desc == 1

        use_wildcard = gen_utils.parse_int(gen_utils.try_get_param(request, 'use_wildcard'), None)
        use_wildcard = use_wildcard == 1

        case_sensitive = gen_utils.parse_int(gen_utils.try_get_param(request, 'case_sensitive'), None)
        case_sensitive = case_sensitive == 1

        codelist = search_utils.search_codelist(coding_system, search_term, use_desc=use_desc, use_wildcard=use_wildcard, case_sensitive=case_sensitive)
        if codelist is not None:
            codelist = list(codelist.values('id', 'code', 'description'))
        else:
            codelist = [ ]
        
        return JsonResponse({
            'result': codelist
        })


class RedirectConceptView(TemplateView):
    """
        Redirects requests to the phenotype page, assuming a phenotype owner can be resolved from the child Concept

        Note:
            - Used to maintain legacy URLs where users could visit `concepts/C<pk>/detail`
    """

    # URL Name of the detail page
    ENTITY_DETAIL_VIEW = 'entity_detail'

    def get(self, request, *args, **kwargs):
        """
            Given the pk kwarg:
                1. Will validate the existence of that Concept
                2. Will then try to find its Phenotype owner
                3. Finally, redirect the user to the Phenotype page
        """
        brand = model_utils.try_get_brand(request)
        if brand is not None:
            brand_mapping = brand.get_map_rules()
        else:
            brand_mapping = constants.DEFAULT_CONTENT_MAPPING

        tx_concept = brand_mapping.get('concept', 'Concept')
        tx_phenotype = brand_mapping.get('phenotype', 'Phenotype')

        concept_id = gen_utils.parse_int(kwargs.get('pk'), default=None)
        if concept_id is None:
            return View.notify_err(
                request,
                title='Bad Request - Invalid ID',
                status_code=400,
                details=[f'The {tx_concept} ID you supplied is invalid. If we sent you here, please contact us and let us know.']
            )

        concept = model_utils.try_get_instance(Concept, id=concept_id)
        if concept is None:
            return View.notify_err(
                request,
                title=f'Page Not Found - Missing {tx_concept}',
                status_code=404,
                details=[f'Sorry but it looks like this {tx_concept} doesn\'t exist. If we sent you here, please contact us and let us know.']
            )

        entity_owner = concept.phenotype_owner
        if entity_owner is None:
            return View.notify_err(
                request,
                title='Page Not Found - Failed To Resolve',
                status_code=404,
                details=[f'Sorry but it looks like this {tx_concept} isn\'t currently associated with a {tx_phenotype}. Please use the API to access the contents of this {tx_concept}.']
            )

        return redirect(reverse(self.ENTITY_DETAIL_VIEW, kwargs={ 'pk': entity_owner.id }))


def generic_entity_detail(request, pk, history_id=None):
    """Display the detail of a generic entity at a point in time."""
    # validate pk param
    brand = model_utils.try_get_brand(request)
    if brand is not None:
        brand_mapping = brand.get_map_rules()
    else:
        brand_mapping = constants.DEFAULT_CONTENT_MAPPING

    tx_phenotype = brand_mapping.get('phenotype', 'Phenotype')
    if not model_utils.get_entity_id(pk):
        return View.notify_err(
            request,
            title='Bad Request - Invalid ID',
            status_code=400,
            details=[f'The {tx_phenotype} ID you supplied is invalid. If we sent you here, please contact us and let us know.']
        )

    # find latest accessible entity for given pk if historical id not specified
    history_id = gen_utils.parse_int(history_id, default=None)
    if not isinstance(history_id, int):
        entities = permission_utils.get_accessible_entities(request, pk=pk)

        if not entities.exists():
            return View.notify_err(
                request,
                title=f'Page Not Found - Missing {tx_phenotype}',
                status_code=404,
                details=[f'Sorry but it looks like this {tx_phenotype} doesn\'t exist. If we sent you here, please contact us and let us know.']
            )
        else:
            history_id = entities.first().history_id

    accessibility, err = permission_utils.get_accessible_detail_entity(request, pk, history_id)
    if err is not None:
        return View.notify_err(
            request,
            title=err.get('title'),
            status_code=err.get('status_code'),
            details=[err.get('message')]
        )
    elif not accessibility or not accessibility.get('view_access'):
        return View.notify_err(
            request,
            title='Forbidden - Permission Denied',
            status_code=403,
            details=[f'Sorry but it looks like this {tx_phenotype} hasn\'t been made accessible to you yet. Please contact the author of this {tx_phenotype} to grant you access.']
        )

    entity = accessibility.get('historical_entity')
    live_entity = accessibility.get('entity')

    is_deleted = not not live_entity.is_deleted
    is_published = accessibility.get('is_published', False)
    approval_status = entity.publish_status
    user_can_export = request.user is not None and request.user.is_authenticated

    entity_dataset = permission_utils.get_accessible_entity_history(request, pk, history_id)
    entity_dataset = entity_dataset if isinstance(entity_dataset, dict) else { }

    is_lastapproved = entity_dataset.get('is_last_approved', False)
    is_latest_pending_version = entity_dataset.get('is_latest_pending_version', False)

    history = entity_dataset.get('entities', [])
    published_historical_ids = entity_dataset.get('published_ids', [])

    template = entity.template.history.filter(template_version=entity.template_version).latest()
    entity_class = template.entity_class

    if request.user.is_authenticated:
        can_edit = accessibility.get('edit_access', False)
        user_allowed_to_create = permission_utils.allowed_to_create()
    else:
        can_edit = False
        user_allowed_to_create = False

    is_latest_version = history_id == entity_dataset.get('latest_history_id', -1)
    if is_deleted:
        messages.info(request, "This entity has been deleted.")

    context = {
        'entity_class': entity_class,
        'entity': entity,
        'history': history,
        'template': template,
        'page_canonical_path': get_canonical_path_by_brand(request, GenericEntity, pk, history_id),        
        'user_can_edit': not not can_edit,  
        'allowed_to_create': user_allowed_to_create,
        'user_can_export': user_can_export,
        'live_ver_is_deleted': is_deleted,
        'published_historical_ids': published_historical_ids,
        'approval_status': approval_status,
        'is_latest_version': is_latest_version,
        'is_latest_pending_version':is_latest_pending_version,
        'is_lastapproved': is_lastapproved,
        'is_published': is_published,
        'current_phenotype_history_id': int(history_id),                           
    }

    return render(request, 
        'clinicalcode/generic_entity/detail/detail.html',
        context 
    )


def get_history_table_data(request, pk):
    """"Gets history table data for the template"""
    versions = GenericEntity.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = entity_db_utils.get_historical_entity(pk, v.history_id
                                        , highlight_result = [False, True][entity_db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))
                                        , include_template_data = False  
                                        )

        is_this_version_published = False
        is_this_version_published = permission_utils.check_if_published(GenericEntity, ver.id, ver.history_id)

        if is_this_version_published:
            ver.publish_date = PublishedGenericEntity.objects.get(entity_id=ver.id, entity_history_id=ver.history_id, approval_status=2).modified
        else:
            ver.publish_date = None

        ver.approval_status = constants.APPROVAL_STATUS.ANY
        ver.approval_status_label = ''
        if PublishedGenericEntity.objects.filter(entity_id=ver.id, entity_history_id=ver.history_id).exists():
            ver.approval_status = PublishedGenericEntity.objects.get(entity_id=ver.id, entity_history_id=ver.history_id).approval_status
            if ver.approval_status != constants.APPROVAL_STATUS.ANY:
                ver.approval_status_label = [s.name for s in constants.APPROVAL_STATUS if s == ver.approval_status][0]   
        
        if request.user.is_authenticated:
            if permission_utils.can_user_edit_entity(request, pk) or permission_utils.can_user_view_entity(request, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)
                
    return historical_versions


def export_entity_codes_to_csv(request, pk, history_id=None):
    """Returns a csv file of codes for a clinical-coded phenotype for a specific historical version."""

    # get the latest version/ or latest published version
    if not isinstance(history_id, int):
        entities = permission_utils.get_accessible_entities(request, pk=pk)

        if not entities.exists():
            return View.notify_err(
                request,
                title='Page Not Found - Missing Codelist',
                status_code=404,
                details=['Sorry but it looks like this codelist doesn\'t exist.']
            )
        else:
            history_id = entities.first().history_id
        
    # validate access for login and public site
    permission_utils.validate_access_to_view(request, pk, history_id)

    is_published = permission_utils.check_if_published(GenericEntity, pk, history_id)

    # ----------------------------------------------------------------------

    # exclude(is_deleted=True)
    if GenericEntity.objects.filter(id=pk).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # exclude(is_deleted=True)
    if GenericEntity.history.filter(id=pk, history_id=history_id).count() == 0:
        return HttpResponseNotFound("Not found.")
        # raise permission_denied # although 404 is more relevant

    # here, check live version
    current_ph = GenericEntity.objects.get(pk=pk)

    # if not is_published:
    #     children_permitted_and_not_deleted, error_dict = db_utils.chk_children_permission_and_deletion(request, GenericEntity, pk, set_history_id=history_id)
    #     if not children_permitted_and_not_deleted:
    #         raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    current_ph_version = GenericEntity.history.get(id=pk, history_id=history_id)

    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = entity_db_utils.get_concept_ids_versions_of_historical_phenotype(pk, history_id)

    my_params = {
        'phenotype_id': pk,
        'history_id': history_id,
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="%(phenotype_id)s_ver_%(history_id)s_codelists_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    final_titles = ([
        'code', 'description', 'coding_system', 
        'concept_id', 'concept_version_id', 'concept_name',
        'phenotype_id', 'phenotype_version_id', 'phenotype_name'
        ])
    
    # if the phenotype contains only one concept, write titles in the loop below
    final_titles = final_titles + ["code_attributes"]
    writer.writerow(final_titles)
        
    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        current_concept_version = Concept.history.get(id=concept_id, history_id=concept_version_id)
        concept_coding_system = current_concept_version.coding_system.name
        concept_name = current_concept_version.name
        code_attribute_header = current_concept_version.code_attribute_header
        
        rows_no = 0        
        concept_data = concept_utils.get_clinical_concept_data(concept_id,
                                                      concept_version_id,
                                                      include_component_codes=False,
                                                      include_attributes=True,
                                                      include_reviewed_codes=True)
            
        #---------------------------------------------
        
        for cc in concept_data['codelist']:
            rows_no += 1
                         
            #---------------------------------------------   
            code_attributes = []
            code_attributes_dict = OrderedDict([])
            if code_attribute_header:
                code_attributes_dict = OrderedDict(zip(code_attribute_header, cc['attributes']))
                code_attributes.append(dict(code_attributes_dict))
                
            if code_attributes:
                code_attributes = [json.dumps(code_attributes)]
            #---------------------------------------------
            
            
            writer.writerow([
                cc['code'], 
                cc['description'].encode('ascii', 'ignore').decode('ascii'), 
                concept_coding_system, 
                'C' + str(concept_id), 
                concept_version_id,
                concept_name,
                current_ph_version.id, 
                current_ph_version.history_id,
                current_ph_version.name
            ] + code_attributes)

        if rows_no == 0:
            writer.writerow([
                '', 
                '', 
                concept_coding_system, 
                'C' + str(concept_id), 
                concept_version_id,
                concept_name,
                current_ph_version.id, 
                current_ph_version.history_id,
                current_ph_version.name
            ])

    return response
