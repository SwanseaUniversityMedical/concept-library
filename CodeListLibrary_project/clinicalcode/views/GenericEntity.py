'''
    ---------------------------------------------------------------------------
    GENERIC-ENTITY VIEW
    ---------------------------------------------------------------------------
'''
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotFound
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.generic import DetailView, TemplateView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import UpdateView
from django.utils.decorators import method_decorator
from collections import OrderedDict

import csv
import json
import logging
import re
import time

from .. import utils
from clinicalcode.entity_utils import entity_db_utils
from ..models import *
from ..permissions import *
from .View import *
from clinicalcode.api.views.View import get_canonical_path_by_brand
from clinicalcode.constants import *

from ..entity_utils import template_utils, gen_utils, model_utils, create_utils, stats_utils, search_utils, constants

logger = logging.getLogger(__name__)

class EntitySearchView(TemplateView):
    '''
        Entity single search view
            - Responsible for:
                -> Managing context of template and which entities to render
                -> SSR of entities at initial GET request based on request params
                -> AJAX-driven update of template based on request params (through JsonResponse)
    '''
    template_name = 'clinicalcode/generic_entity/search.html'
    result_template = 'components/search/results.html'
    pagination_template = 'components/search/pagination_container.html'

    def get_context_data(self, *args, **kwargs):
        '''
            Provides contextful data to template based on request parameters
        '''
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
        '''
            Manages get requests to this view
            
            [!] Note: if search_filtered is passed as a parameter (through a fetch req),
                    the GET request will return the pagination and results
                    for hotreloading relevant search results instead of forcing
                    a page reload
        '''
        context = self.get_context_data(*args, **kwargs)
        filtered = gen_utils.try_get_param(request, 'search_filtered', None)

        if filtered is not None and request.headers.get('X-Requested-With'):
            context['request'] = request

            results = render_to_string(self.result_template, context)
            pagination = render_to_string(self.pagination_template, context)            
            return HttpResponse(results + pagination, content_type='text/plain')
            
        return render(request, self.template_name, context)

class CreateEntityView(TemplateView):
    '''
        Entity Create View
            @desc Used to create entities - CreateView isn't used due to the requirements
                  of having a form dynamically created to reflect the dynamic model.
    '''
    fetch_methods = ['search_codes', 'get_options']
    templates = {
        'form': 'clinicalcode/generic_entity/creation/create.html',
        'select': 'clinicalcode/generic_entity/creation/select.html'
    }
    
    ''' View methods '''
    @method_decorator([login_required])
    def dispatch(self, request, *args, **kwargs):
        '''
            @desc Dispatch view
        '''
        return super(CreateEntityView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        '''
            @desc Provides contextual data
        '''
        context = super(CreateEntityView, self).get_context_data(*args, **kwargs)
        return context
    
    @method_decorator([login_required])
    def get(self, request, *args, **kwargs):
        '''
            @desc Handles get requests by determining whether it was made
                  through the fetch method, or accessed via a browser.
                  
                  If requested via browser, will render a view. Otherwise
                  will respond with appropriate method, if applicable.
        '''
        if gen_utils.is_fetch_request(request):
            return self.fetch_response(request, *args, **kwargs)
        
        return self.render_view(request, *args, **kwargs)

    @method_decorator([login_required])
    def post(self, request, *args, **kwargs):
        '''
            @desc Handles:
                - form submission on creating or updating an entity
        '''
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
            'redirect': reverse('generic_entity_history_detail', kwargs={ 'pk': entity.id, 'history_id': entity.history_id })
        })        

    ''' Main view render '''
    def render_view(self, request, *args, **kwargs):
        '''
            @desc Template and entity is tokenised in the URL - providing the latter requires
                  users to be permitted to modify that particular entity.

                  If no entity_id is passed, a creation form is returned, otherwise the user is
                  redirected to an update form.
        '''
        context = self.get_context_data(*args, **kwargs)

        # Send to selection page if no template_id and entity_id
        template_id = kwargs.get('template_id')
        entity_id = kwargs.get('entity_id')
        if template_id is None and entity_id is None:
            return self.select_form(request, context)

        # Send to create form if template_id is selected
        template_id = gen_utils.parse_int(template_id, default=None)
        if template_id is not None:
            template = model_utils.try_get_instance(Template, pk=template_id)
            if template is None:
                raise Http404
            return self.create_form(request, context, template)

        # Send to update form if entity_id is selected
        entity_history_id = gen_utils.parse_int(kwargs.get('entity_history_id'), default=None)
        if entity_id is not None and entity_history_id is not None:
            entity = create_utils.try_validate_entity(request, entity_id, entity_history_id)
            if not entity:
                raise PermissionDenied
            
            template = entity.template
            if template is None:
                raise BadRequest('Invalid request.')
            
            return self.update_form(request, context, template, entity)
        
        # Raise 404 if no param matches views
        raise Http404
    
    ''' Forms '''
    def select_form(self, request, context):
        '''
            @desc Renders the template selection form
        '''
        context['entity_data'] = create_utils.get_createable_entities(request)
        return render(request, self.templates.get('select'), context)

    def create_form(self, request, context, template):
        '''
            @desc Renders the entity create form
        '''
        context['metadata'] = constants.metadata
        context['template'] = template
        context['form_method'] = constants.FORM_METHODS.CREATE
        return render(request, self.templates.get('form'), context)

    def update_form(self, request, context, template, entity):
        '''
            @desc Renders the entity update form
        '''
        context['metadata'] = constants.metadata
        context['template'] = template
        context['entity'] = entity
        context['object_reference'] = { 'id': entity.id, 'history_id': entity.history_id }
        context['form_method'] = constants.FORM_METHODS.UPDATE
        return render(request, self.templates.get('form'), context)

    ''' Fetch methods '''
    def fetch_response(self, request, *args, **kwargs):
        '''
            @desc Parses the X-Target header to determine which GET method
                  to respond with
        '''
        target = request.headers.get('X-Target', None)
        if target is None or target not in self.fetch_methods:
            raise BadRequest('No such target')
        
        return getattr(self, target)(request, *args, **kwargs)
    
    def get_options(self, request, *args, **kwargs):
        '''
            @desc GET request made by client to retrieve all available
                  options for a given field within its template

        '''
        template_id = gen_utils.parse_int(gen_utils.try_get_param(request, 'template'), default=None)
        if not template_id:
            return gen_utils.jsonify_response(message='Invalid template parameter', code=400, status='false')
        
        template = model_utils.try_get_instance(Template, pk=template_id)
        if template is None:
            return gen_utils.jsonify_response(message='Invalid template parameter, template does not exist', code=400, status='false')
        
        field = gen_utils.try_get_param(request, 'parameter')
        if field is None or gen_utils.is_empty_string(field):
            return gen_utils.jsonify_response(message='Invalid field parameter', code=400, status='false')

        if template_utils.is_metadata(GenericEntity, field):
            options = template_utils.get_template_sourced_values(constants.metadata, field)
        else:
            options = template_utils.get_template_sourced_values(template, field)
        
        if options is None:
            return gen_utils.jsonify_response(message='Invalid field parameter, does not exist or is not an optional parameter', code=400, status='false')

        options = model_utils.append_coding_system_data(options)
        return JsonResponse({
            'result': options
        })

    def search_codes(self, request, *args, **kwargs):
        '''
            @desc GET request made by client to search a codelist given its coding id,
                  a search term, and the relevant template
            
                  e.g. entity/{update|create}/?search=C1&coding_system=4&template=1
        '''
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

        codelist = search_utils.search_codelist(coding_system, search_term)
        if codelist is not None:
            codelist = list(codelist.values('id', 'code', 'description'))
        else:
            codelist = [ ]
        
        return JsonResponse({
            'result': codelist
        })

class EntityStatisticsView(TemplateView):
    '''
        Admin job panel to save statistics for templates across entities
    '''
    def get(self, request, *args, **kwargs):
        if settings.CLL_READ_ONLY:
            raise PermissionDenied
        
        if not request.user.is_superuser:
            raise PermissionDenied
        
        stats_utils.collect_statistics(request)
        return render(request, 'clinicalcode/admin/run_statistics.html', {
            'successMsg': ['Filter statistics for Concepts/Phenotypes saved'],
        })

class ExampleSASSView(TemplateView):
    template_name = 'clinicalcode/generic_entity/examples.html'

    def get(self, request):
        ctx = {

        }

        return render(request, self.template_name, context=ctx)

def generic_entity_list_temp(request):
    '''
        Display the list of phenotypes. 
    '''
    from django.core.paginator import EmptyPage, Paginator
    
    page = utils.get_int_value(request.GET.get('page', request.session.get('entity_page', 1)), request.session.get('phenotype_page', 1))
    page_size = 20    
 
    request.session['entity_page'] = page
    
    srch = entity_db_utils.get_visible_live_or_published_generic_entity_versions(request,
                                                                            get_live_and_or_published_ver=3,
                                                                            search='',
                                                                            author='',
                                                                            exclude_deleted=True,
                                                                            filter_cond=" 1=1 ",
                                                                            search_name_only = False,
                                                                            highlight_result = True
                                                                            )
    # create pagination
    paginator = Paginator(srch,
                          page_size,
                          allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    p_btns = utils.get_paginator_pages(paginator, p)


    context = {
        'page': page,
        'page_size': str(20),
        'page_obj': p,
        'search_form': 'basic-form',
        'p_btns': p_btns,
        }
    
    return render(request, 'clinicalcode/generic_entity/search_temp.html', context)



def generic_entity_detail(request, pk, history_id=None):
    ''' 
        Display the detail of a generic entity at a point in time.
    '''
    # validate access for login and public site
    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)

    is_published = checkIfPublished(GenericEntity, pk, history_id)
    approval_status = get_publish_approval_status(GenericEntity, pk, history_id)
    is_lastapproved = len(PublishedGenericEntity.objects.filter(entity=GenericEntity.objects.get(pk=pk).id, approval_status=2)) > 0

    # ----------------------------------------------------------------------

    generic_entity = entity_db_utils.get_historical_entity(history_id
                                            , highlight_result = [False, True][entity_db_utils.is_referred_from_search_page(request)]
                                            , q_highlight = entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))  
                                            )
    # The historical entity contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the generic_entity.
    if generic_entity['owner_id'] is not None:
        generic_entity['owner'] = User.objects.get(id=int(generic_entity['owner_id']))
        
    generic_entity['group'] = None
    if generic_entity['group_id'] is not None:
        generic_entity['group'] = Group.objects.get(id=int(generic_entity['group_id']))

    history_date = generic_entity['history_date']



################################################
    entity_class = generic_entity['entity_class']
        
    side_menu = get_side_menu(request, generic_entity['fields_data'])




################################################


    is_latest_version = (int(history_id) == GenericEntity.objects.get(pk=pk).history.latest().history_id)
    is_latest_pending_version = False

    if len(PublishedGenericEntity.objects.filter(entity_id=pk, entity_history_id=history_id, approval_status=1)) > 0:
        is_latest_pending_version = True
   # print(is_latest_pending_version)


    children_permitted_and_not_deleted = True
    error_dict = {}
    #are_concepts_latest_version = True
    version_alerts = {}

    if request.user.is_authenticated:
        can_edit = (not GenericEntity.objects.get(pk=pk).is_deleted) and allowed_to_edit(request, GenericEntity, pk)

        user_can_export = True 
         # (allowed_to_view_children(request, GenericEntity, pk, set_history_id=history_id)
         #                   and entity_db_utils.chk_deleted_children(request,
         #                                                   GenericEntity,
         #                                                   pk,
         #                                                   returnErrors=False,
         #                                                   set_history_id=history_id)
         #                   and not GenericEntity.objects.get(pk=pk).is_deleted)
        user_allowed_to_create = allowed_to_create()

        #children_permitted_and_not_deleted, error_dict = entity_db_utils.chk_children_permission_and_deletion(request, GenericEntity, pk)


    else:
        can_edit = False
        user_can_export = is_published
        user_allowed_to_create = False

    publish_date = None
    if is_published:
        publish_date = PublishedGenericEntity.objects.get(entity_id=pk, entity_history_id=history_id).created

    if GenericEntity.objects.get(pk=pk).is_deleted == True:
        messages.info(request, "This entity has been deleted.")

    # published versions
    published_historical_ids = list(PublishedGenericEntity.objects.filter(entity_id=pk, approval_status=2).values_list('entity_history_id', flat=True))

    # # history
    history = get_history_table_data(request, pk)
   

    # rmd 
    if generic_entity['fields_data']['implementation'] is None:
        generic_entity['fields_data']['implementation'] = ''




    context = {
        'side_menu': side_menu,  
        'entity_class': entity_class,
        'entity': generic_entity,
        'entity_fields': generic_entity['fields_data'],
        'history': history,
        
        'page_canonical_path': get_canonical_path_by_brand(request, GenericEntity, pk, history_id),
        
        
        'user_can_edit': False,  # for now  #can_edit,
        'allowed_to_create': False,  # for now  #user_allowed_to_create,    # not settings.CLL_READ_ONLY,
        'user_can_export': user_can_export,
        
        'live_ver_is_deleted': GenericEntity.objects.get(pk=pk).is_deleted,
        'published_historical_ids': published_historical_ids,
        'is_published': is_published,
        'approval_status': approval_status,
        'is_lastapproved': is_lastapproved,
        'publish_date': publish_date,
        'is_latest_version': is_latest_version,
        'is_latest_pending_version':is_latest_pending_version,
        'current_phenotype_history_id': int(history_id),

        'q': entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', '')),
        'force_highlight_result':  ['0', '1'][entity_db_utils.is_referred_from_search_page(request)]                              
    }

    concept_dict = get_concept_data(request, pk, history_id, generic_entity, is_latest_version, children_permitted_and_not_deleted)
    return render(request, 
                  'clinicalcode/generic_entity/detail.html',
                  context | concept_dict
                )


def get_side_menu(request, template_data):
    """
    return side menu tabs
    """
   
    side_menu = {}
    
    field_definitions = template_data
    for (field_name, field_definition) in field_definitions.items():
        ##field_name = field_name.replace(' ', '') 
        is_side_menu = False
        side_menu_title = ''
        
        if field_name.strip().lower() == 'name':
            continue
        
        if 'do_not_show_in_production' in field_definition and field_definition['do_not_show_in_production'] == True:
            if (not settings.IS_DEMO) and (not settings.IS_DEVELOPMENT_PC):
                continue  
                     
        if 'requires_auth' in field_definition and field_definition['requires_auth'] == True:
            if not request.user.is_authenticated:
                continue  
            
        if 'hide_if_empty' in field_definition and field_definition['hide_if_empty'] == True:
            if str(field_definition['value']).strip() == '':
                continue   
                
        # if 'is_base_field' in field_definition and field_definition['is_base_field'] == True:
        #     is_side_menu = True
        #     side_menu_title = field_name 

        if 'side_menu' in field_definition:
            is_side_menu = True
            side_menu_title = field_definition['side_menu'] 


        if is_side_menu:
            #field_name = side_menu_title.replace(' ', '')
            side_menu[field_definition['html_id']] = side_menu_title

    return side_menu
            

def get_history_table_data(request, pk):
    """"
        get history table data for the template
    """
    
    versions = GenericEntity.objects.get(pk=pk).history.all()
    historical_versions = []

    for v in versions:
        ver = entity_db_utils.get_historical_entity(v.history_id
                                        , highlight_result = [False, True][entity_db_utils.is_referred_from_search_page(request)]
                                        , q_highlight = entity_db_utils.get_q_highlight(request, request.session.get('generic_entity_search', ''))
                                        , include_template_data = False  
                                        )
        
        if ver['owner_id'] is not None:
            ver['owner'] = User.objects.get(id=int(ver['owner_id']))

        if ver['created_by_id'] is not None:
            ver['created_by'] = User.objects.get(id=int(ver['created_by_id']))

        ver['updated_by'] = None
        if ver['updated_by_id'] is not None:
            ver['updated_by'] = User.objects.get(pk=ver['updated_by_id'])

        is_this_version_published = False
        is_this_version_published = checkIfPublished(GenericEntity, ver['id'], ver['history_id'])

        if is_this_version_published:
            ver['publish_date'] = PublishedGenericEntity.objects.get(entity_id=ver['id'], entity_history_id=ver['history_id'], approval_status=2).created
        else:
            ver['publish_date'] = None

        ver['approval_status'] = -1
        ver['approval_status_label'] = ''
        if PublishedGenericEntity.objects.filter(entity_id=ver['id'], entity_history_id=ver['history_id']).exists():
            ver['approval_status'] = PublishedGenericEntity.objects.get(entity_id=ver['id'], entity_history_id=ver['history_id']).approval_status
            ver['approval_status_label'] = APPROVED_STATUS[ver['approval_status']][1]        
        
        
        if request.user.is_authenticated:
            if allowed_to_edit(request, GenericEntity, pk) or allowed_to_view(request, GenericEntity, pk):
                historical_versions.append(ver)
            else:
                if is_this_version_published:
                    historical_versions.append(ver)
        else:
            if is_this_version_published:
                historical_versions.append(ver)
                
    return historical_versions
   
   
def get_concept_data(request, pk, history_id, generic_entity, is_latest_version, children_permitted_and_not_deleted):
    """
    get concept data from concept_informations
    """
    error_dict = {}
    are_concepts_latest_version = True
    
    concept_id_list = []
    concept_hisoryid_list = []
    concepts = Concept.history.filter(pk=-1).values('id', 'history_id', 'name', 'group')

    if generic_entity['fields_data']['concept_information']:
        concept_information = generic_entity['fields_data']['concept_information']['value']
        concept_id_list = [x['concept_id'] for x in concept_information]
        concept_hisoryid_list = [x['concept_version_id'] for x in concept_information]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list).values('id', 'history_id', 'name', 'group')

    concepts_id_name = json.dumps(list(concepts))
    
    if request.user.is_authenticated:
        if is_latest_version:
            are_concepts_latest_version, version_alerts = check_concept_version_is_the_latest(pk)
    
    # how to show codelist tab
    if request.user.is_authenticated:
        component_tab_active = "active"
        codelist_tab_active = ""
        codelist = []
        codelist_loaded = 0
    else:
        # published
        component_tab_active = "active"  # ""
        codelist_tab_active = ""  # "active"
        codelist = entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id) ## change
        codelist_loaded = 1
        
    # codelist = entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id)
    # codelist_loaded = 1    
    
    conceptBrands = entity_db_utils.getConceptBrands(request, concept_id_list)
    concept_data = []
    if concept_information:
        for c in concept_information:
            c['codingsystem'] = CodingSystem.objects.get(pk=Concept.history.get(id=c['concept_id'], history_id=c['concept_version_id']).coding_system_id).name
            c['code_attribute_header'] = Concept.history.get(id=c['concept_id'], history_id=c['concept_version_id']).code_attribute_header

            c['alerts'] = ''
            if not are_concepts_latest_version:
                if c['concept_version_id'] in version_alerts:
                    c['alerts'] = version_alerts[c['concept_version_id']]

            if not children_permitted_and_not_deleted:
                if c['concept_id'] in error_dict:
                    c['alerts'] += "<BR>- " + "<BR>- ".join(error_dict[c['concept_id']])

            c['alerts'] = re.sub("Child ", "", c['alerts'], flags=re.IGNORECASE)

            c['brands'] = ''
            if c['concept_id'] in conceptBrands:
                for brand in conceptBrands[c['concept_id']]:
                    c['brands'] += "<img src='" + static('img/brands/' + brand + '/logo.png') + "' height='10px' title='" + brand + "' alt='" + brand + "' /> "

            c['is_published'] = checkIfPublished(Concept, c['concept_id'], c['concept_version_id'])
            c['name'] = concepts.get(id=c['concept_id'], history_id=c['concept_version_id'])['name']

            c['codesCount'] = 0
            if codelist:
                c['codesCount'] = len([x['code'] for x in codelist if x['concept_id'] == 'C' + str(c['concept_id']) and x['concept_version_id'] == c['concept_version_id'] ])

            c['concept_friendly_id'] = 'C' + str(c['concept_id'])
            concept_data.append(c)

    ret_dict = {        
        #'concept_information': json.dumps(concept_information),
        'component_tab_active': component_tab_active,
        'codelist_tab_active': codelist_tab_active,
        'codelist': codelist,  # json.dumps(codelist)
        'codelist_loaded': codelist_loaded,
        'concepts_id_name': concepts_id_name,
        'concept_data': concept_data,
        }
    
    return ret_dict
   
@login_required
# phenotype_conceptcodesByVersion
def phenotype_concept_codes_by_version(request,
                                    pk,
                                    history_id,
                                    target_concept_id = None,
                                    target_concept_history_id = None):
    '''
        Get the codes of the phenotype concepts
        for a specific version
        for a specific concept
        Parameters:     request    The request.
                        pk         The phenotype id.
                        history_id  The version id
                        target_concept_id
                        target_concept_history_id
        Returns:        data       Dict with the codes. 
    '''

    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    # here, check live version
    current_ph = GenericEntity.objects.get(pk=pk)

    #     children_permitted_and_not_deleted, error_dict = db_utils.chk_children_permission_and_deletion(request,
    #                                                                                                 GenericEntity, pk,
    #                                                                                                 set_history_id=history_id)
    #     if not children_permitted_and_not_deleted:
    #         raise PermissionDenied

    if current_ph.is_deleted == True:
        raise PermissionDenied

    # --------------------------------------------------

    codes = entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id, target_concept_id, target_concept_history_id)

    data = dict()
    data['form_is_valid'] = True


    # Get the list of concepts in the phenotype data
    concept_ids_historyIDs = entity_db_utils.get_concept_ids_versions_of_historical_phenotype(pk, history_id)

    concept_codes_html = []
    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]

        # check if the sent concept id/ver are valid
        if (target_concept_id is not None and target_concept_history_id is not None):
            if target_concept_id != str(concept_id) and target_concept_history_id != str(concept_version_id):
                continue

        c_codes = []

        c_codes = codes

        c_codes_count = "0"
        try:
            c_codes_count = str(len(c_codes))
        except:
            c_codes_count = "0"

        # c_codes_count_2 = len([c['code'] for c in codes if c['concept_id'] == concept_id and c['concept_version_id'] == concept_version_id ])

        c_code_attribute_header = Concept.history.get(id=concept_id, history_id=concept_version_id).code_attribute_header
        concept_codes_html.append({
            'concept_id': concept_id,
            'concept_version_id': concept_version_id,
            'c_codes_count': c_codes_count,
            'c_html': render_to_string(
                                        'clinicalcode/phenotype/get_concept_codes.html', {
                                            'codes': c_codes,
                                            'code_attribute_header': c_code_attribute_header,
                                            'showConcept': False,
                                            'q': ['', request.session.get('phenotype_search', '')][request.GET.get('highlight','0')=='1']
                                        })
        })

    data['concept_codes_html'] = concept_codes_html

    # data['codes'] = codes

    return JsonResponse(data)


def check_concept_version_is_the_latest(phenotypeID):
    """
    check live version of concepts in a phenotype concept_information
    """

    phenotype = GenericEntity.objects.get(pk=phenotypeID)

    is_ok = True
    version_alerts = {}

    if not phenotype.template_data['concept_information']:
        return is_ok, version_alerts

    concepts_id_versionID = phenotype.template_data['concept_information']

    # loop for concept versions
    for c in concepts_id_versionID:
        c_id = c['concept_id']
        c_ver_id = c['concept_version_id']
        latest_history_id = Concept.objects.get(pk=c_id).history.latest('history_id').history_id
        if latest_history_id != c_ver_id:
            version_alerts[c_ver_id] = "newer version available"
            is_ok = False
    #         else:
    #             version_alerts[c_id] = ""
    return is_ok, version_alerts




@login_required
def Entity_Create(request):
    """
        create an antity
    """
    # TODO: implement this
    pass


class Entity_Update(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, UpdateView):
    """
        Update the current entity.
    """
    # ToDo
    pass


class PhenotypeDelete(LoginRequiredMixin, HasAccessToEditPhenotypeCheckMixin, TemplateResponseMixin, View):
    """
        Delete an entity.
    """
    # ToDo
    pass



def history_phenotype_codes_to_csv(request, pk, history_id=None):
    """
        Return a csv file of codes for a phenotype for a specific historical version.
    """
    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)        
        
    # validate access for login and public site
    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    is_published = checkIfPublished(GenericEntity, pk, history_id)

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
    response['Content-Disposition'] = ('attachment; filename="phenotype_%(phenotype_id)s_ver_%(history_id)s_concepts_%(creation_date)s.csv"' % my_params)

    writer = csv.writer(response)

    final_titles = ([
        'code', 'description', 'coding_system', 
        'concept_id', 'concept_version_id', 'concept_name',
        'phenotype_id', 'phenotype_version_id', 'phenotype_name'
        ])
    # if the phenotype contains only one concept, write titles in the loop below
    if len(concept_ids_historyIDs) != 1:
        final_titles = final_titles + ["code_attributes"]
        writer.writerow(final_titles)
        

    for concept in concept_ids_historyIDs:
        concept_id = concept[0]
        concept_version_id = concept[1]
        current_concept_version = Concept.history.get(id=concept_id, history_id=concept_version_id)
        concept_coding_system = current_concept_version.coding_system.name
        concept_name = current_concept_version.name
        code_attribute_header = current_concept_version.code_attribute_header
        concept_history_date = current_concept_version.history_date
        
        rows_no = 0
        codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id, concept_version_id)

        #---------------------------------------------
        #  code attributes  ---
        codes_with_attributes = []
        if code_attribute_header:
            codes_with_attributes = db_utils.getConceptCodes_withAttributes_HISTORICAL(concept_id=concept_id,
                                                                                    concept_history_date=concept_history_date,
                                                                                    allCodes=codes,
                                                                                    code_attribute_header=code_attribute_header)
        
            codes = codes_with_attributes
            
        # if the phenotype contains only one concept
        if len(concept_ids_historyIDs) == 1:
            if code_attribute_header:
                final_titles = final_titles + code_attribute_header
                
            writer.writerow(final_titles)
    
        #---------------------------------------------

        
        for cc in codes:
            rows_no += 1
                         
            #---------------------------------------------   
            code_attributes = []
            # if the phenotype contains only one concept
            if len(concept_ids_historyIDs) == 1:
                if code_attribute_header:
                    for a in code_attribute_header:
                        code_attributes.append(cc[a])
            else:
                code_attributes_dict = OrderedDict([])
                if code_attribute_header:
                    for a in code_attribute_header:
                        code_attributes_dict[a] = cc[a]
                    code_attributes.append(dict(code_attributes_dict))
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





