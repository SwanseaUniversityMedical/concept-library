from rest_framework.decorators import (api_view, permission_classes)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.conf import settings

from ...models import *
from ...entity_utils import permission_utils
from ...entity_utils import template_utils
from ...entity_utils import search_utils
from ...entity_utils import api_utils
from ...entity_utils import gen_utils
from ...entity_utils import constants

''' Create/Update GenericEntity '''

@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_generic_entity(request):
    '''
    
    '''
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.CREATE.value
    )
    if isinstance(form, Response):
        return form
        
    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully created entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_generic_entity(request):
    '''
    
    '''
    if permission_utils.is_member(request.user, 'ReadOnlyUsers') or settings.CLL_READ_ONLY:
        return Response(
            data={
                'message': 'Permission denied'
            },
            content_type='json',
            status=status.HTTP_403_FORBIDDEN
        )
    
    form = api_utils.validate_api_create_update_form(
        request, method=constants.FORM_METHODS.UPDATE.value
    )
    if isinstance(form, Response):
        return form

    entity = api_utils.create_update_from_api_form(request, form)
    if isinstance(entity, Response):
        return entity
    
    entity_data = {
        'id': entity.id,
        'version_id': entity.history_id,
        'created': entity.created,
        'updated': entity.updated,
    }
    if template_utils.get_entity_field(entity, 'concept_information'):
        concept_data = api_utils.get_concept_versions_from_entity(entity)
        entity_data = entity_data | {
            'concepts': concept_data
        }

    return Response(
        data={
            'message': 'Successfully updated entity',
            'entity': entity_data
        },
        status=status.HTTP_201_CREATED
    )

''' Get GenericEntity version history '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entity_version_history(request, primary_key=None):
    '''
    
    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True
    
    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(primary_key)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(primary_key)
    if isinstance(entity_response, Response):
        return entity_response
    
    return Response(
        data=api_utils.get_entity_version_history(request, primary_key), 
        status=status.HTTP_200_OK
    )

''' Get GenericEntities '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_generic_entities(request, should_paginate=False):
    '''
    
    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True

    # Get all accessible entities for this user
    entities = permission_utils.get_accessible_entities(
        request, 
        consider_user_perms=False, 
        status=[constants.APPROVAL_STATUS.ANY]
    )
    if not entities.exists():
        return Response([], status=status.HTTP_200_OK)
    
    # Filter by template id and version
    template_id = request.query_params.get('template_id', None)
    template_version_id = request.query_params.get('template_version_id', None)
    if template_id:
        template = Template.objects.filter(id=template_id)
        if not template.exists():
            return Response(
                data={
                    'message': 'Template with specified id does not exist'
                },
                content_type='json',
                status=status.HTTP_404_NOT_FOUND
            )
        
        template = template.first()
        if template_version_id:
            template = template.history.filter(template_version=template_version_id)
            if not template.exists():
                return Response(
                    data={
                        'message': 'Template with specified version id does not exist'
                    },
                    content_type='json',
                    status=status.HTTP_404_NOT_FOUND
                )
            
            template = template.latest()
            entities = entities.filter(
                template__id=template.id, template_version=template.template_version
            )
        else:
            entities = entities.filter(
                template__id=template.id
            )

    # Build query from searchable GenericEntity template fields
    templates = Template.objects.all()
    for template in templates:
        template_query, where_clause = api_utils.build_query_from_template(
            request, user_authed, template=template.definition['fields']
        )

        entities = entities.filter(Q(**template_query))
        entities = entities.extra(where=where_clause)

    # Search terms
    search = request.query_params.get('search', None)
    if search:
        entities = search_utils.search_entities(
            entities, search, fuzzy=False, order_by_relevance=False
        )

    # Exit early if queries do not match
    if not entities.exists():
        return Response([], status=status.HTTP_200_OK)
    
    ''' Please note, this looks redundant but is *required* due to varchar entity ID '''
    entities = GenericEntity.history.filter(
        id__in=entities.values_list('id', flat=True),
        history_id__in=entities.values_list('history_id', flat=True)
    )
    entities = entities.extra(
        select={'true_id': """CAST(REGEXP_REPLACE(id, '[a-zA-Z]+', '') AS INTEGER)"""}
    ).order_by('true_id', 'id')

    # Paginate results
    if should_paginate:
        page = gen_utils.parse_int(request.query_params.get('page', 1), default=1)
        entities = search_utils.try_get_paginated_results(
            request, entities, page, page_size=50
        )
    
    # Get details of each entity
    formatted_entities = []
    for entity in entities:
        entity_detail = api_utils.get_entity_detail(
            request, 
            entity.id, 
            entity, 
            user_authed, 
            fields_to_ignore=constants.ENTITY_LIST_API_HIDDEN_FIELDS, 
            return_data=True
        )

        if not isinstance(entity_detail, Response):
            formatted_entities.append(entity_detail)

    if should_paginate:
        result = {
            'page': page,
            'num_pages': entities.paginator.num_pages,
            'data': formatted_entities
        }
    else:
        result = formatted_entities

    return Response(
        data=result,
        status=status.HTTP_200_OK
    )

''' Get GenericEntity detail '''

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_entity_detail(request, primary_key, historical_id=None, field=None):
    '''

    '''
    user_authed = False
    if request.user and not request.user.is_anonymous:
        user_authed = True

    # Check if primary_key is valid, i.e. matches regex '^[a-zA-Z]\d+'
    entity_id_response = api_utils.is_malformed_entity_id(primary_key)
    if isinstance(entity_id_response, Response):
        return entity_id_response

    # Check if entity with prefix and id exists
    entity_response = api_utils.exists_entity(primary_key)
    if isinstance(entity_response, Response):
        return entity_response
    
    # Find latest historical id if not provided, and get first matching historical entity
    historical_entity_response = api_utils.exists_historical_entity(
        primary_key, request.user, historical_id=historical_id
    )
    if isinstance(historical_entity_response, Response):
        return historical_entity_response
    historical_entity = historical_entity_response

    # Check if the user has the permissions to view this entity version
    user_can_access = permission_utils.can_user_view_entity(
        request, historical_entity.id, historical_entity.history_id
    )
    if not user_can_access:
        return Response(
            data={
                'message': 'Entity version must be published or you must have permission to access it'
            }, 
            content_type='json',
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if field is not None:
        if template_utils.is_valid_field(historical_entity, field):
            return api_utils.get_entity_detail(
                request, 
                primary_key, 
                historical_entity, 
                user_authed, 
                target_field=field, 
                return_data=True
            )
        
        if field == 'codes':
            return api_utils.get_codelist_from_entity(historical_entity)
        
        return Response(
            data={
                'message': 'Field does not exist'
            }, 
            content_type='json',
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return api_utils.get_entity_detail(
        request, primary_key, historical_entity, user_authed
    )

### M. Elmessary  ############

from ...db_utils import *
from clinicalcode.entity_utils import entity_db_utils
from ...permissions import *
from ...utils import *
from ..serializers import *
from .View import *

# show generic_entity detail
#=============================================================
@api_view(['GET'])
def generic_entity_detail(request,
                     pk,
                     history_id=None,
                     get_versions_only=None):
    ''' 
        Display the detail of a generic entity at a point in time.
    '''

    if GenericEntity.objects.filter(id=pk).count() == 0:
        raise Http404

    if history_id is not None:
        generic_entity_ver = GenericEntity.history.filter(id=pk, history_id=history_id)
        if generic_entity_ver.count() == 0: raise Http404
   
    if history_id  is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)   
        
        
    # validate access generic_entity
    if not allowed_to_view(request, GenericEntity, pk, set_history_id=history_id):
        raise PermissionDenied

    # # we can remove this check as in generic_entity-detail
    # #---------------------------------------------------------
    # # validate access to child generic_entitys
    # if not (allowed_to_view_children(request, GenericEntity, pk, set_history_id=history_id)
    #         and chk_deleted_children(request,
    #                                  GenericEntity,
    #                                  pk,
    #                                  returnErrors=False,
    #                                  set_history_id=history_id)):
    #     raise PermissionDenied
    # #---------------------------------------------------------

     

    return get_generic_entity_detail(request,
                              pk = pk,
                              history_id = history_id,
                              is_authenticated_user = True,
                              get_versions_only = get_versions_only,
                              set_class = GenericEntity)


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def generic_entity_detail_PUBLIC(request,
                            pk,
                            history_id=None,
                            get_versions_only=None):
    ''' 
        Display the detail of a published generic_entity at a point in time.
    '''

    if GenericEntity.objects.filter(id=pk).count() == 0:
        raise Http404

    if history_id is not None:
        generic_entity_ver = GenericEntity.history.filter(id=pk, history_id=history_id)
        if generic_entity_ver.count() == 0: raise Http404

    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)

    is_published = checkIfPublished(GenericEntity, pk, history_id)
    # check if the generic_entity version is published
    if not is_published and get_versions_only != '1':
        raise PermissionDenied

    return get_generic_entity_detail(request,
                              pk = pk,
                              history_id = history_id,
                              is_authenticated_user = False,
                              get_versions_only = get_versions_only,
                              set_class = GenericEntity)


#--------------------------------------------------------------------------
@robots2()
def get_generic_entity_detail(request,
                       pk,
                       history_id=None,
                       is_authenticated_user=True,
                       get_versions_only=None,
                       set_class=GenericEntity):

    if get_versions_only is not None:
        if get_versions_only == '1':
            titles = ['versions']
            ret = [get_visible_versions_list(request, GenericEntity, pk, is_authenticated_user)]
            rows_to_return = []
            rows_to_return.append(ordr(list(zip(titles, ret))))
            return Response(rows_to_return, status=status.HTTP_200_OK)
    #--------------------------

    generic_entity = entity_db_utils.get_historical_entity(history_id, return_queryset_as_list=True)
    # The history generic_entity contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the generic_entity.
    generic_entity['owner'] = None
    if generic_entity['owner_id'] is not None:
        generic_entity['owner'] = User.objects.get(pk=generic_entity['owner_id']).username

    generic_entity['group'] = None
    if generic_entity['group_id'] is not None:
        generic_entity['group'] = Group.objects.get(pk=generic_entity['group_id']).name

    #---------------------------------------------------------------------- 
    template_data = generic_entity['fields_data']    
    
    has_phenotype_concept_informations = False
    if 'concept_information' in template_data:
        has_phenotype_concept_informations = True
    

    rows_to_return = []
    
    titles = [
        'id',
        'version_id'
    ]
    
    ret = [
        generic_entity['id'],
        generic_entity['history_id']
    ]
    
    # loop through data
    for (field_name, field_data) in template_data.items():
        if entity_db_utils.can_field_be_shown(field_data
                                                      , is_authenticated_user
                                                      , block_list={"field_type": ["concept_information"]}):
            titles += [field_name]
            ret += [field_data['value']]
    

    
    if is_authenticated_user:
        titles += [
            'created_by',
            'created_date',
            'updated_by',
            'updated_date'
            ]
    

    if is_authenticated_user:
        titles +=[
            'owner',
            'owner_access',
            'group',
            'group_access',
            'world_access',
            'is_deleted',  # may come from generic_entity live version / or history
            # 'deleted_by', 'deleted_date' # no need here
        ]
    
    if has_phenotype_concept_informations:
        titles +=['concepts']
    
    titles +=['versions']
    
    if is_authenticated_user:
        ret += [
            generic_entity['created_by_username'],
            generic_entity['created']
            ]
        if generic_entity['updated_by_username']:
            ret += [
                generic_entity['updated_by_username'],
                generic_entity['updated']
                ]
        else:
            ret += [None, None]
    

    
    if is_authenticated_user:    
        ret +=[
            generic_entity['owner'],
            dict(Permissions.PERMISSION_CHOICES)[generic_entity['owner_access']],
            generic_entity['group'],
            dict(Permissions.PERMISSION_CHOICES)[generic_entity['group_access']],
            dict(Permissions.PERMISSION_CHOICES)[generic_entity['world_access']],
        ]
    
        # may come from generic_entity live version / or history
        if (generic_entity['is_deleted'] == True or GenericEntity.objects.get(pk=pk).is_deleted == True):
            ret += [True]
        else:
            ret += [None]


    if has_phenotype_concept_informations:
        phenotype_concept_informations_data = get_phenotype_concept_informations_data(request, 
                                                concept_information = generic_entity['fields_data']['concept_information']['value'])
        ret += [phenotype_concept_informations_data]


    # versions
    ret += [get_visible_versions_list(request, GenericEntity, pk, is_authenticated_user) ]

    rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)


def get_phenotype_concept_informations_data(request, concept_information):
    
    # concepts for clinical-coded phenotype
    concept_id_list = []
    concept_hisoryid_list = []
    concepts = Concept.history.filter(pk=-1)
    
    #concept_information = generic_entity['fields_data']['concept_information']['value']
    if concept_information:
        concept_id_list = [x['concept_id'] for x in concept_information]
        concept_hisoryid_list = [x['concept_version_id'] for x in concept_information]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list)
            
    com_titles = ['name', 'concept_id', 'concept_version_id', 'coding_system', 'codes']

    ret_concepts = []
    for c in concepts:
        ret_codes = []
        ret_codes = getGroupOfCodesByConceptId_HISTORICAL(c.id, c.history_id)
        final_ret_codes = []
        #################
        #---------
        code_attribute_header = c.code_attribute_header
        concept_history_date = c.history_date
        codes_with_attributes = []
        if code_attribute_header:
            codes_with_attributes = getConceptCodes_withAttributes_HISTORICAL(
                                                                            concept_id=c.id,
                                                                            concept_history_date=concept_history_date,
                                                                            allCodes=ret_codes,
                                                                            code_attribute_header=code_attribute_header)

            ret_codes = codes_with_attributes
        #---------

        code_titles = ['code', 'description']
        if code_attribute_header:
            if request.query_params.get('format', 'xml').lower() == 'xml':
                # clean attr names/ remove space, etc
                code_titles = code_titles + [clean_str_as_db_col_name(a) for a in code_attribute_header ]
            else:
                code_titles = code_titles + [a for a in code_attribute_header]

        for cd in ret_codes:
            code_attributes = []
            if code_attribute_header:
                for a in code_attribute_header:
                    code_attributes.append(cd[a])

            final_ret_codes.append(ordr(list(zip(code_titles, 
                                                [cd['code'], cd['description'].encode('ascii', 'ignore').decode('ascii')] + code_attributes
                                                )
                                            )
                                        )
                                    )
        #################
        ret_comp_data = [c.name, c.friendly_id, c.history_id, c.coding_system.name, final_ret_codes ]
        ret_concepts.append(ordr(list(zip(com_titles, ret_comp_data))))

    
    return ret_concepts


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
@robots()
def export_published_phenotype_codes(request, pk, history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        phenotype (pk),
        for a specific historical phenotype version (history_id).
    '''

    if not GenericEntity.objects.filter(id=pk).exists():
        raise PermissionDenied
    
    if history_id is None:
        # get the latest published version
        latest_published_version = GenericEntity.objects.filter(entity_id=pk, approval_status=2).order_by('-entity_history_id').first()
        if latest_published_version:
            history_id = latest_published_version.history_id

    if not GenericEntity.history.filter(id=pk, history_id=history_id).exists():
        raise PermissionDenied

    is_published = checkIfPublished(GenericEntity, pk, history_id)

    # check if the phenotype version is published
    if not is_published:
        raise PermissionDenied

    #----------------------------------------------------------------------
    if request.method == 'GET':
        rows_to_return = entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)


#--------------------------------------------------------------------------
@api_view(['GET'])
def export_phenotype_codes_byVersionID(request, pk, history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        phenotype (pk),
        for a specific historical version (history_id).
    '''
        
    if history_id is None:
        # get the latest version/ or latest published version
        history_id = try_get_valid_history_id(request, GenericEntity, pk)        
        
    # Require that the user has access to the base phenotype.
    # validate access for login site
    validate_access_to_view(request,
                            GenericEntity,
                            pk,
                            set_history_id=history_id)

    #----------------------------------------------------------------------

    current_phenotype = GenericEntity.objects.get(pk=pk)

    # user_can_export = (allowed_to_view_children(request, GenericEntity, pk, set_history_id=history_id)
    #                    and chk_deleted_children(request,
    #                                            GenericEntity,
    #                                            pk,
    #                                            returnErrors=False,
    #                                            set_history_id=history_id)
    #                     and not current_phenotype.is_deleted
    #                     )
    #
    # if not user_can_export:
    #     raise PermissionDenied
    #----------------------------------------------------------------------

    if request.method == 'GET':
        rows_to_return = entity_db_utils.get_phenotype_concept_codes_by_version(request, pk, history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)


##################################################################################