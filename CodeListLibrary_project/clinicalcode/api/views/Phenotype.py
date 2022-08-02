import json
from collections import OrderedDict
from collections import OrderedDict as ordr
from datetime import datetime

from clinicalcode.context_processors import clinicalcode
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.core.validators import URLValidator
from django.db.models import Q
from django.db.models.aggregates import Max
from django.http.response import Http404
from numpy.distutils.fcompiler import none
from rest_framework import status, viewsets
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response
from django.db.models.functions import Lower

from ...db_utils import *
from ...models import *
from ...permissions import *
from ...utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ..serializers import *
from .View import *
#from .View import chk_group, chk_group_access, chk_tags, chk_world_access

from drf_yasg.utils import swagger_auto_schema


# Don't show in Swagger
@swagger_auto_schema(method='post', auto_schema=None)
@api_view(['POST'])
def api_phenotype_create(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if is_member(request.user, group_name='ReadOnlyUsers'):
        raise PermissionDenied

    validate_access_to_create()
    user_groups = getGroups(request.user)
    if request.method == 'POST':
        errors_dict = {}
        is_valid = True

        # don't check unique UUid
        #         known_phenotypes = set(get_visible_phenotypes(request.user).exclude(is_deleted=True).values_list('phenotype_uuid', flat=True))
        #         new_phenotype_uuid = request.data.get('phenotype_uuid')
        #         if new_phenotype_uuid in known_phenotypes:
        #           return Response(
        #             data = {'phenotype_uuid': 'phenotype_uuid must be unique: submitted id is already found'},
        #             content_type="json",
        #             status=status.HTTP_406_NOT_ACCEPTABLE
        #           )

        new_phenotype = Phenotype()
        new_phenotype.phenotype_uuid = request.data.get('phenotype_uuid')
        new_phenotype.title = request.data.get('title')
        new_phenotype.name = request.data.get('name')
        new_phenotype.author = request.data.get('author')
        new_phenotype.layout = request.data.get('layout')
        new_phenotype.type = request.data.get('type')
        new_phenotype.validation_performed = request.data.get('validation_performed')
        new_phenotype.validation = request.data.get('validation')

        new_phenotype.valid_event_data_range = request.data.get('valid_event_data_range')
        #         new_phenotype.valid_event_data_range_start = request.data.get('valid_event_data_range_start')
        #         new_phenotype.valid_event_data_range_end = request.data.get('valid_event_data_range_end')
        new_phenotype.sex = request.data.get('sex')
        new_phenotype.status = request.data.get('status')
        new_phenotype.hdr_created_date = request.data.get('hdr_created_date')
        new_phenotype.hdr_modified_date = request.data.get('hdr_modified_date')
        new_phenotype.publications = request.data.get('publications')
        new_phenotype.publication_doi = request.data.get('publication_doi')
        new_phenotype.publication_link = request.data.get('publication_link')
        new_phenotype.secondary_publication_links = request.data.get('secondary_publication_links')
        new_phenotype.source_reference = request.data.get('source_reference')
        new_phenotype.citation_requirements = request.data.get(
            'citation_requirements')
        #new_phenotype.concept_informations = request.data.get('concept_informations')

        new_phenotype.description = request.data.get('description')
        new_phenotype.implementation = request.data.get('implementation')
        new_phenotype.phenoflowid = request.data.get('phenoflowid')

        new_phenotype.created_by = request.user
        new_phenotype.owner_access = Permissions.EDIT
        new_phenotype.owner_id = request.user.id


        # concept_informations
        concept_ids_list = request.data.get('concept_informations')
        is_valid_data, err, ret_value = chk_concept_ids_list(request, concept_ids_list, item_name='concept_informations')
        if is_valid_data:
            concept_ids_list = ret_value
            concept_informations = getPhenotypeConceptJson(concept_ids_list)
            new_phenotype.concept_informations = concept_informations
            new_phenotype.clinical_terminologies = get_CodingSystems_from_Phenotype_concept_informations(concept_informations)
        else:
            errors_dict['concept_informations'] = err
 
            
            
        # group id
        is_valid_data, err, ret_value = chk_group(request.data.get('group'), user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                new_phenotype.group_id = None
                new_phenotype.group_access = 1
            else:
                new_phenotype.group_id = group_id

                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    new_phenotype.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err

        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(
            request.data.get('world_access'))
        if is_valid_data:
            new_phenotype.world_access = ret_value
        else:
            errors_dict['world_access'] = err

        # handling tags
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
            if tags:
                new_phenotype.tags = [int(i) for i in tags]
        else:
            errors_dict['tags'] = err

        # handling data-sources
        datasource_ids_list = request.data.get('data_sources')
        is_valid_data, err, ret_value = chk_data_sources(
            request.data.get('data_sources'))
        if is_valid_data:
            datasource_ids_list = ret_value
        else:
            errors_dict['data_sources'] = err

        # Validation
        errors_pt = {}
        if bool(errors_dict):
            is_valid = False

        is_valid_pt = True
        is_valid_pt, errors_pt = isValidPhenotype(request, new_phenotype)

        if not is_valid or not is_valid_pt:
            errors_dict.update(errors_pt)
            return Response(data=errors_dict,
                            content_type="json",
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            new_phenotype.save()
            created_pt = Phenotype.objects.get(pk=new_phenotype.pk)
            created_pt.history.latest().delete()

            # - datasource -----
            if datasource_ids_list:
                new_datasource_list = [int(i) for i in datasource_ids_list]
                for datasource_id in new_datasource_list:
                    PhenotypeDataSourceMap.objects.get_or_create(phenotype=new_phenotype,
                                                                datasource=DataSource.objects.get(id=datasource_id), 
                                                                created_by=request.user
                                                                )

            save_Entity_With_ChangeReason(Phenotype, created_pt.pk, "Created from API")
            # created_pt.changeReason = "Created from API"
            # created_pt.save()

            # publish immediately - for HDR-UK testing
            if request.data.get('publish_immediately') == True:
                publish_entity(request, Phenotype, created_pt.pk)

            data = {
                'message': 'Phenotype created successfully',
                'id': created_pt.pk
            }

            return Response(data=data,
                            content_type="text/json-comment-filtered",
                            status=status.HTTP_201_CREATED)


# Don't show in Swagger
@swagger_auto_schema(method='put', auto_schema=None)
@api_view(['PUT'])
def api_phenotype_update(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if is_member(request.user, group_name='ReadOnlyUsers'):
        raise PermissionDenied

    validate_access_to_create()
    user_groups = getGroups(request.user)
    if request.method == 'PUT':
        errors_dict = {}
        is_valid = True

        phenotype_id = request.data.get('id')
        is_valid_id, err, ret_int_id = chk_valid_id(request, Phenotype, phenotype_id, chk_permission=True)
        if is_valid_id:
            phenotype_id = ret_int_id
        else:
            errors_dict['id'] = err
            return Response(data=errors_dict,
                            content_type="json",
                            status=status.HTTP_406_NOT_ACCEPTABLE)
               
        # if not isInt(phenotype_id):
        #     errors_dict['id'] = 'phenotype_id must be a valid id.'
        #     return Response(data=errors_dict,
        #                     content_type="json",
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)
        #
        # if Phenotype.objects.filter(pk=phenotype_id).count() == 0:
        #     errors_dict['id'] = 'phenotype_id not found.'
        #     return Response(data=errors_dict,
        #                     content_type="json",
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)
        # if not allowed_to_edit(request, Phenotype, phenotype_id):
        #     errors_dict[
        #         'id'] = 'phenotype_id must be a valid accessible phenotype id.'
        #     return Response(data=errors_dict,
        #                     content_type="json",
        #                     status=status.HTTP_406_NOT_ACCEPTABLE)

        update_phenotype = Phenotype.objects.get(pk=phenotype_id)
        update_phenotype.phenotype_uuid = request.data.get('phenotype_uuid')
        update_phenotype.title = request.data.get('title')
        update_phenotype.name = request.data.get('name')
        update_phenotype.author = request.data.get('author')
        update_phenotype.layout = request.data.get('layout')
        update_phenotype.type = request.data.get('type')
        update_phenotype.validation = request.data.get('validation')

        update_phenotype.valid_event_data_range = request.data.get('valid_event_data_range')
        #         update_phenotype.valid_event_data_range_start = request.data.get('valid_event_data_range_start')
        #         update_phenotype.valid_event_data_range_end = request.data.get('valid_event_data_range_end')
        update_phenotype.sex = request.data.get('sex')
        update_phenotype.status = request.data.get('status')
        update_phenotype.hdr_created_date = request.data.get('hdr_created_date')
        update_phenotype.hdr_modified_date = request.data.get('hdr_modified_date')
        update_phenotype.publications = request.data.get('publications')
        update_phenotype.publication_doi = request.data.get('publication_doi')
        update_phenotype.publication_link = request.data.get('publication_link')
        update_phenotype.secondary_publication_links = request.data.get('secondary_publication_links')
        update_phenotype.source_reference = request.data.get('source_reference')  # With data_sources I don't think this is needed
        update_phenotype.citation_requirements = request.data.get('citation_requirements')
        update_phenotype.concept_informations = None  # request.data.get('concept_informations')
        update_phenotype.clinical_terminologies = None

        update_phenotype.description = request.data.get('description')
        update_phenotype.implementation = request.data.get('implementation')
        update_phenotype.phenoflowid = request.data.get('phenoflowid')

        update_phenotype.updated_by = request.user
        update_phenotype.modified = datetime.datetime.now()
        
        # concept_informations
        concept_ids_list = request.data.get('concept_informations')
        is_valid_data, err, ret_value = chk_concept_ids_list(request, concept_ids_list, item_name='concept_informations')
        if is_valid_data:
            concept_ids_list = ret_value
            concept_informations = getPhenotypeConceptJson(concept_ids_list)
            update_phenotype.concept_informations = concept_informations
            update_phenotype.clinical_terminologies = get_CodingSystems_from_Phenotype_concept_informations(concept_informations)
        else:
            errors_dict['concept_informations'] = err

            
            
        #  group id
        is_valid_data, err, ret_value = chk_group(request.data.get('group'),user_groups)
        if is_valid_data:
            group_id = ret_value
            if group_id is None or group_id == "0":
                update_phenotype.group_id = None
                update_phenotype.group_access = 1
            else:
                update_phenotype.group_id = group_id
                is_valid_data, err, ret_value = chk_group_access(request.data.get('group_access'))
                if is_valid_data:
                    update_phenotype.group_access = ret_value
                else:
                    errors_dict['group_access'] = err
        else:
            errors_dict['group'] = err

        # handle world-access
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            update_phenotype.world_access = ret_value
        else:
            errors_dict['world_access'] = err

        # handling tags
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
            if tags:
                update_phenotype.tags = [int(i) for i in tags]
            else:
                update_phenotype.tags = None
        else:
            errors_dict['tags'] = err

        # handling data-sources
        datasource_ids_list = request.data.get('data_sources')
        is_valid_data, err, ret_value = chk_data_sources(request.data.get('data_sources'))
        if is_valid_data:
            datasource_ids_list = ret_value
        else:
            errors_dict['data_sources'] = err

        # Validation
        errors_pt = {}
        if bool(errors_dict):
            is_valid = False

        is_valid_pt = True
        is_valid_pt, errors_pt = isValidPhenotype(request, update_phenotype)
        if not is_valid or not is_valid_pt:
            errors_dict.update(errors_pt)
            return Response(data=errors_dict,
                            content_type="json",
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            # update data-sources
            new_datasource_list = []

            if datasource_ids_list:
                new_datasource_list = [int(i) for i in datasource_ids_list]

            old_datasource_list = list(PhenotypeDataSourceMap.objects.filter(phenotype=update_phenotype).values_list('datasource',  flat=True))
            datasource_ids_to_add = list(set(new_datasource_list) - set(old_datasource_list))
            datasource_ids_to_remove = list(set(old_datasource_list) - set(new_datasource_list))

            for datasource_id_to_add in datasource_ids_to_add:
                PhenotypeDataSourceMap.objects.get_or_create(phenotype=update_phenotype,
                                                            datasource=DataSource.objects.get(id=datasource_id_to_add),
                                                            created_by=request.user)

            for datasource_id_to_remove in datasource_ids_to_remove:
                datasource_to_remove = PhenotypeDataSourceMap.objects.filter(phenotype=update_phenotype,
                                                                            datasource=DataSource.objects.get(id=datasource_id_to_remove))
                datasource_to_remove.delete()

            #save_Entity_With_ChangeReason(Phenotype, update_phenotype.pk, "Updated from API")
            # update_phenotype.changeReason = "Updated from API"
            update_phenotype.save()
            modify_Entity_ChangeReason(Phenotype, update_phenotype.pk, "Updated from API")

            # publish immediately - for HDR-UK testing
            if request.data.get('publish_immediately') == True:
                publish_entity(request, Phenotype, update_phenotype.pk)

            data = {
                'message': 'Phenotype updated successfully',
                'id': update_phenotype.pk
            }

            return Response(data=data,
                            content_type="text/json-comment-filtered",
                            status=status.HTTP_201_CREATED)


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
@robots()
def export_published_phenotype_codes(request, pk, phenotype_history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        phenotype (pk),
        for a specific historical phenotype version (phenotype_history_id).
    '''

    if not Phenotype.objects.filter(id=pk).exists():
        raise PermissionDenied
    
    if phenotype_history_id is None:
        # get the latest published version
        latest_published_version = PublishedPhenotype.objects.filter(phenotype_id=pk, approval_status=2).order_by('-phenotype_history_id').first()
        if latest_published_version:
            phenotype_history_id = latest_published_version.phenotype_history_id

    if not Phenotype.history.filter(id=pk, history_id=phenotype_history_id).exists():
        raise PermissionDenied

    is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)

    # check if the phenotype version is published
    if not is_published:
        raise PermissionDenied

    #----------------------------------------------------------------------
    if request.method == 'GET':
        rows_to_return = get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)


#--------------------------------------------------------------------------
@api_view(['GET'])
def export_phenotype_codes_byVersionID(request, pk, phenotype_history_id=None):
    '''
        Return the unique set of codes and descriptions for the specified
        phenotype (pk),
        for a specific historical phenotype version (phenotype_history_id).
    '''
        
    if phenotype_history_id is None:
        # get the latest version
        phenotype_history_id = Phenotype.objects.get(pk=pk).history.latest().history_id
        
    # Require that the user has access to the base phenotype.
    # validate access for login site
    validate_access_to_view(request,
                            Phenotype,
                            pk,
                            set_history_id=phenotype_history_id)

    #----------------------------------------------------------------------

    current_phenotype = Phenotype.objects.get(pk=pk)

    user_can_export = (allowed_to_view_children(
        request, Phenotype, pk, set_history_id=phenotype_history_id)
                       and chk_deleted_children(
                           request,
                           Phenotype,
                           pk,
                           returnErrors=False,
                           set_history_id=phenotype_history_id)
                       and not current_phenotype.is_deleted)

    if not user_can_export:
        raise PermissionDenied
    #----------------------------------------------------------------------

    if request.method == 'GET':
        rows_to_return = get_phenotype_conceptcodesByVersion(request, pk, phenotype_history_id)
        return Response(rows_to_return, status=status.HTTP_200_OK)


##################################################################################
# search my phenotypes / published ones


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def published_phenotypes(request, pk=None):
    """
    Lists <em>the published</em> phenotypes and the data sources associated with each.
    User can search with criteria using a combinations of querystring parameters:   
    -  <code>?search=Alcohol</code>  
    search by part of phenotype name (do not put wild characters here)  
    -  <code>?tag_concept_ids=11,4</code>  
    You can specify tag or collection ids   
    -  <code>?selected_phenotype_types=drug,lifestyle risk factor</code>
    Specify types of the phenotypes  
    -  <code>?show_only_validated_phenotypes=1</code>  
    will show only validated phenotypes  
    -  <code>?brand=HDRUK</code>  
    will show only phenotypes with brand=HDRUK (this overwrites the site default brand)  
    -  <code>?author=Kuan</code>  
    search by part of the author name        
    -  <code>?do_not_show_versions=1</code>  
    do not show phenotypes versions (by default, all phenotype's version ids are shown)  
    """
    return getPhenotypes(request, is_authenticated_user=False, pk=pk, set_class=Phenotype)


#--------------------------------------------------------------------------
@api_view(['GET'])
def phenotypes(request, pk=None):
    """
    Lists all available phenotypes <em>for the user</em> and the data sources associated with each.
    User can search with criteria using a combinations of querystring parameters:   
    -  <code>?search=Alcohol</code>  
    search by part of phenotype name (do not put wild characters here)  
    -  <code>?tag_concept_ids=11,4</code>  
    You can specify tag or collection ids   
    -  <code>?selected_phenotype_types=drug,lifestyle risk factor</code>
    Specify types of the phenotypes         
    -  <code>?show_only_my_phenotypes=1</code>  
    Only show phenotypes owned by me  
    -  <code>?show_deleted_phenotypes=1</code>  
    will show also deleted phenotypes (by default, deleted objects are not shown)  
    -  <code>?show_only_validated_phenotypes=1</code>  
    will show only validated phenotypes  
    -  <code>?brand=HDRUK</code>  
    will show only phenotypes with brand=HDRUK (this overwrites the site default brand)  
    -  <code>?author=Kuan</code>  
    search by part of the author name  
    -  <code>?owner_username=a.john</code>  
    search by full username of the owner  
    -  <code>?do_not_show_versions=1</code>  
    do not show phenotypes versions (by default, all phenotype's version ids are shown)  
    -  <code>?must_have_published_versions=1</code>  
    show only phenotypes which have a published version(by default, all phenotypes are shown)  
    """
    return getPhenotypes(request, is_authenticated_user=True, pk=pk, set_class=Phenotype)


#--------------------------------------------------------------------------
@robots2()
def getPhenotypes(request, is_authenticated_user=True, pk=None, set_class=Phenotype):
    search = request.query_params.get('search', '')

    if pk is not None:
        phenotype_id = pk
    else:
        phenotype_id = request.query_params.get('id', None)

    tag_ids = request.query_params.get('tag_concept_ids', '')
    owner = request.query_params.get('owner_username', '')
    show_only_my_phenotypes = request.query_params.get('show_only_my_phenotypes', "0")
    show_deleted_phenotypes = request.query_params.get('show_deleted_phenotypes', "0")
    show_only_validated_phenotypes = request.query_params.get('show_only_validated_phenotypes', "0")
    phenotype_brand = request.query_params.get('brand', "")
    author = request.query_params.get('author', '')
    do_not_show_versions = request.query_params.get('do_not_show_versions', "0")
    expand_published_versions = 0  # disable this option
    #expand_published_versions = request.query_params.get('expand_published_versions', "1")
    show_live_and_or_published_ver = "3"  # request.query_params.get('show_live_and_or_published_ver', "3")      # 1= live only, 2= published only, 3= live+published
    must_have_published_versions = request.query_params.get('must_have_published_versions', "0")
    selected_phenotype_types = request.query_params.get('selected_phenotype_types', '')
    
    selected_phenotype_types = selected_phenotype_types.strip().lower()

    search_tag_list = []
    selected_phenotype_types_list = []

    # remove leading, trailing and multiple spaces from text search params
    search = re.sub(' +', ' ', search.strip())
    owner = re.sub(' +', ' ', owner.strip())
    author = re.sub(' +', ' ', author.strip())
    
    
    filter_cond = " 1=1 "
    exclude_deleted = True
    get_live_and_or_published_ver = 3  # 1= live only, 2= published only, 3= live+published
    show_top_version_only = True

    # available phenotype_types in the DB
    phenotype_types = Phenotype.history.annotate(type_lower=Lower('type')).values('type_lower').distinct().order_by('type_lower')
    phenotype_types_list = list(phenotype_types.values_list('type_lower',  flat=True))
    
    # search by ID (only with prefix)
    # chk if the search word is valid ID (with  prefix 'PH' case insensitive)
    search_by_id = False
    id_match = re.search(r"(?i)^PH\d+$", search)
    if id_match:
        if id_match.group() == id_match.string: # full match
            is_valid_id, err, ret_int_id = chk_valid_id(request, set_class=Phenotype, pk=search, chk_permission=False)
            if is_valid_id:
                search_by_id = True
                filter_cond += " AND (id =" + str(ret_int_id) + " ) "    
    
    if tag_ids:
        # split tag ids into list
        search_tag_list = [str(i).strip() for i in tag_ids.split(",")]
        # chk if these tags are valid, to prevent injection
        # use only those found in the DB
        tags = Tag.objects.filter(id__in=search_tag_list)
        search_tag_list = list(tags.values_list('id',  flat=True))
        search_tag_list = [str(i) for i in search_tag_list]
        filter_cond += " AND tags && '{" + ','.join(search_tag_list) + "}' "

    if selected_phenotype_types:
        selected_phenotype_types_list = [str(t).strip() for t in selected_phenotype_types.split(',')]
        # chk if these types are valid, to prevent injection
        # use only those found in the DB
        selected_phenotype_types_list = list(set(phenotype_types_list).intersection(set(selected_phenotype_types_list)))
        filter_cond += " AND lower(type) IN('" + "', '".join(selected_phenotype_types_list) + "') "
   
    
    
    # check if it is the public site or not
    if is_authenticated_user:
        # ensure that user is only allowed to view/edit the relevant phenotypes

        get_live_and_or_published_ver = 3
        if must_have_published_versions == "1":
            get_live_and_or_published_ver = 2

#         if show_live_and_or_published_ver in ["1", "2", "3"]:
#             get_live_and_or_published_ver = int(show_live_and_or_published_ver)   #    2= published only
#         else:
#             return Response([], status=status.HTTP_200_OK)

# show only phenotypes created by the current user
        if show_only_my_phenotypes == "1":
            filter_cond += " AND owner_id=" + str(request.user.id)

        # if show deleted phenotypes is 1 then show deleted phenotypes
        if show_deleted_phenotypes != "1":
            exclude_deleted = True
        else:
            exclude_deleted = False

    else:
        # show published phenotypes
        get_live_and_or_published_ver = 2  #    2= published only

        if PublishedPhenotype.objects.all().count() == 0:
            return Response([], status=status.HTTP_200_OK)

    if expand_published_versions == "1":
        show_top_version_only = False

    if phenotype_id is not None:
        if phenotype_id != '':
            filter_cond += " AND id=" + phenotype_id

    if owner is not None:
        if owner != '':
            if User.objects.filter(username__iexact=owner.strip()).exists():
                owner_id = User.objects.get(username__iexact=owner.strip()).id
                filter_cond += " AND owner_id=" + str(owner_id)
            else:
                # username not found
                filter_cond += " AND owner_id= -1 "

    # if show_only_validated_phenotypes is 1 then show only phenotypes with validation_performed=True
    if show_only_validated_phenotypes == "1":
        filter_cond += " AND COALESCE(validation_performed, FALSE) IS TRUE "

    # show phenotypes for a specific brand
    force_brand = None
    if phenotype_brand != "":
        force_brand = "-xzy"  # an invalid brand name
        if Brand.objects.all().filter(name__iexact=phenotype_brand.strip()).exists():
            current_brand = Brand.objects.get(name__iexact=phenotype_brand.strip())
            force_brand = current_brand.name

    phenotypes_srch = get_visible_live_or_published_phenotype_versions(
                                                            request,
                                                            get_live_and_or_published_ver=get_live_and_or_published_ver,
                                                            search=[search, ''][search_by_id],
                                                            author=author,
                                                            exclude_deleted=exclude_deleted,
                                                            filter_cond=filter_cond,
                                                            show_top_version_only=show_top_version_only,
                                                            force_brand=force_brand,
                                                            search_name_only = False
                                                            )

    rows_to_return = []
    titles = ['phenotype_id', 'version_id']
    if is_authenticated_user:
        titles += ['UUID']
        
    titles +=['phenotype_name', 'type', 'author', 'owner', 'tags', 'collections', 
              'clinical_terminologies', 'data_sources']
    
    if is_authenticated_user:
        titles +=['created_by', 'created_date',
              'modified_by', 'modified_date', 'is_deleted', 'deleted_by', 'deleted_date',
              'is_published']
    
    
    if do_not_show_versions != "1":
        titles += ['versions']

    for c in phenotypes_srch:
        c_tags = []
        c_collections = []
        phenotype_tags = c['tags']
        if phenotype_tags:
            c_tags = list(Tag.objects.filter(pk__in=phenotype_tags, tag_type=1).values('description', 'id'))
            c_collections = list(Tag.objects.filter(pk__in=phenotype_tags, tag_type=2).values('description', 'id',  'collection_brand'))
            if c_collections:
                for col in c_collections:
                    col['collection_brand'] = Brand.objects.get(pk=col['collection_brand']).name
                    
        c_clinical_terminologies = []
        phenotype_clinical_terminologies = c['clinical_terminologies']
        if phenotype_clinical_terminologies:
            c_clinical_terminologies = list(CodingSystem.objects.filter(pk__in=phenotype_clinical_terminologies).values('name', 'id'))

        #--------------

        data_sources = []  # DataSource.objects.filter(pk=-1)
        data_sources_comp = getHistoryDataSource_Phenotype(c['id'], c['history_date'])
        if data_sources_comp:
            ds_list = [i['datasource_id'] for i in data_sources_comp if 'datasource_id' in i ]
            data_sources = list(DataSource.objects.filter(pk__in=ds_list).values('id', 'name', 'url'))  # , 'uid', 'description'

        ret = [
            c['friendly_id'],
            c['history_id']
        ]
        if is_authenticated_user:
            ret += [c['phenotype_uuid']]  #UUID
            
        ret += [
            c['name'].encode('ascii', 'ignore').decode('ascii'),
            c['type'],
            c['author'],
            c['owner_name'],
            c_tags,
            c_collections,
            c_clinical_terminologies,
            data_sources
        ]
        
        if is_authenticated_user:
            ret += [
                    c['created_by_username'],
                    c['created'],
                ]

            if (c['updated_by_id']):
                ret += [c['modified_by_username'],
                        c['modified']
                    ]
            else:
                ret += [None, None]
    
            ret += [c['is_deleted']]
    
            if (c['is_deleted'] == True):
                ret += [c['deleted_by_username']]
            else:
                ret += [None]
    
            ret += [c['deleted'], c['published']]
                    

        if do_not_show_versions != "1":
            ret += [get_visible_versions_list(request, Phenotype, c['id'], is_authenticated_user)]

        rows_to_return.append(ordr(list(zip(titles, ret))))

    if phenotypes_srch:
        return Response(rows_to_return, status=status.HTTP_200_OK)
    else:
        raise Http404
        #return Response(rows_to_return, status=status.HTTP_404_NOT_FOUND)


# show phenotype detail
#=============================================================
@api_view(['GET'])
def phenotype_detail(request,
                     pk,
                     phenotype_history_id=None,
                     get_versions_only=None):
    ''' 
        Display the detail of a phenotype at a point in time.
    '''

    if Phenotype.objects.filter(id=pk).count() == 0:
        raise Http404

    if phenotype_history_id is not None:
        phenotype_ver = Phenotype.history.filter(id=pk, history_id=phenotype_history_id)
        if phenotype_ver.count() == 0: raise Http404

    # validate access phenotype
    if not allowed_to_view(request, Phenotype, pk, set_history_id=phenotype_history_id):
        raise PermissionDenied

    # we can remove this check as in phenotype-detail
    #---------------------------------------------------------
    # validate access to child phenotypes
    if not (allowed_to_view_children(
            request, Phenotype, pk, set_history_id=phenotype_history_id)
            and chk_deleted_children(request,
                                     Phenotype,
                                     pk,
                                     returnErrors=False,
                                     set_history_id=phenotype_history_id)):
        raise PermissionDenied
    #---------------------------------------------------------

    if phenotype_history_id is None:
        # get the latest version
        phenotype_history_id = Phenotype.objects.get(pk=pk).history.latest().history_id

    return getPhenotypeDetail(request,
                              pk = pk,
                              history_id = phenotype_history_id,
                              is_authenticated_user = True,
                              get_versions_only = get_versions_only,
                              set_class = Phenotype)


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def phenotype_detail_PUBLIC(request,
                            pk,
                            phenotype_history_id=None,
                            get_versions_only=None):
    ''' 
        Display the detail of a published phenotype at a point in time.
    '''

    if Phenotype.objects.filter(id=pk).count() == 0:
        raise Http404

    if phenotype_history_id is not None:
        phenotype_ver = Phenotype.history.filter(id=pk, history_id=phenotype_history_id)
        if phenotype_ver.count() == 0: raise Http404

    if phenotype_history_id is None:
        # get the latest version
        phenotype_history_id = Phenotype.objects.get(pk=pk).history.latest().history_id

    is_published = checkIfPublished(Phenotype, pk, phenotype_history_id)
    # check if the phenotype version is published
    if not is_published and get_versions_only != '1':
        raise PermissionDenied

    return getPhenotypeDetail(request,
                              pk = pk,
                              history_id = phenotype_history_id,
                              is_authenticated_user = False,
                              get_versions_only = get_versions_only,
                              set_class = Phenotype)


#--------------------------------------------------------------------------
@robots2()
def getPhenotypeDetail(request,
                       pk,
                       history_id=None,
                       is_authenticated_user=True,
                       get_versions_only=None,
                       set_class=Phenotype):

    if get_versions_only is not None:
        if get_versions_only == '1':
            titles = ['versions']
            ret = [get_visible_versions_list(request, Phenotype, pk, is_authenticated_user)]
            rows_to_return = []
            rows_to_return.append(ordr(list(zip(titles, ret))))
            return Response(rows_to_return, status=status.HTTP_200_OK)
    #--------------------------

    phenotype = getHistoryPhenotype(history_id)
    # The history phenotype contains the owner_id, to provide the owner name, we
    # need to access the user object with that ID and add that to the phenotype.
    phenotype['owner'] = None
    if phenotype['owner_id'] is not None:
        phenotype['owner'] = User.objects.get(pk=phenotype['owner_id']).username

    phenotype['group'] = None
    if phenotype['group_id'] is not None:
        phenotype['group'] = Group.objects.get(pk=phenotype['group_id']).name

    phenotype_history_date = phenotype['history_date']
    #--------------

    #----------------------------------------------------------------------
    concept_id_list = []
    concept_hisoryid_list = []
    concepts = Concept.history.filter(pk=-1)

    if phenotype['concept_informations']:
        concept_id_list = [x['concept_id'] for x in json.loads(phenotype['concept_informations'])]
        concept_hisoryid_list = [x['concept_version_id'] for x in json.loads(phenotype['concept_informations'])]
        concepts = Concept.history.filter(id__in=concept_id_list, history_id__in=concept_hisoryid_list)

    clinicalTerminologies = []  #CodingSystem.objects.filter(pk=-1)
    CodingSystem_ids = phenotype['clinical_terminologies']
    if CodingSystem_ids:
        clinicalTerminologies = list(CodingSystem.objects.filter(pk__in=list(CodingSystem_ids)).values('name', 'id'))

    #--------------

    data_sources = []  #DataSource.objects.filter(pk=-1)
    data_sources_comp = getHistoryDataSource_Phenotype(pk, phenotype_history_date)
    if data_sources_comp:
        ds_list = [i['datasource_id'] for i in data_sources_comp if 'datasource_id' in i ]
        data_sources = list(
            DataSource.objects.filter(pk__in=ds_list).values('id', 'name', 'url'))  # , 'uid', 'description'

    tags = []
    collections = []
    phenotype_tags = phenotype['tags']
    if phenotype_tags:
        tags = list(Tag.objects.filter(pk__in=phenotype_tags, tag_type=1).values('description', 'id'))
        collections = list(Tag.objects.filter(pk__in=phenotype_tags, tag_type=2).values('description', 'id',  'collection_brand'))
        if collections:
            for col in collections:
                col['collection_brand'] = Brand.objects.get(pk=col['collection_brand']).name
                
                    
    rows_to_return = []
    titles = [
        'phenotype_id',
        'version_id'
    ]
    
    if is_authenticated_user:
        titles += ['UUID']
        
    titles +=[
        'phenotype_name',
        'type',
        'tags',
        'collections',
        'author',
        # 'entry_date',
        'clinical_terminologies',
        'data_sources',
        'definition',
    ]
    
    if is_authenticated_user:
        titles += [
            'created_by',
            'created_date',
            'modified_by',
            'modified_date'
            ]
    
    titles += [
        'validation_performed',
        #, 'validation_description',
        'publication_doi',
        'publication_link',
        # 'secondary_publication_links,
        'source_reference',
        'citation_requirements',
        'implementation',
        'publications'
    ]
    
    if is_authenticated_user:
        titles +=[
            'owner',
            'owner_access',
            'group',
            'group_access',
            'world_access',
            'is_deleted',  # may come from phenotype live version / or history
            # 'deleted_by', 'deleted_date' # no need here
        ]
    
    titles +=[
        'concepts',
        'versions'
    ]
    
    

    ret = [
        phenotype['friendly_id'],
        phenotype['history_id']
        ]
    if is_authenticated_user:
        ret += [phenotype['phenotype_uuid']]  #UUID
        
    ret += [
        phenotype['name'].encode('ascii', 'ignore').decode('ascii'),
        phenotype['type'],
        tags,
        collections,
        phenotype['author'],
        #phenotype['entry_date'],
        clinicalTerminologies,
        data_sources,
        phenotype['description'],
    ]
    
    if is_authenticated_user:
        ret += [
            phenotype['created_by_username'],
            phenotype['created']
            ]
        if phenotype['modified_by_username']:
            ret += [
                phenotype['modified_by_username'],
                phenotype['modified']
                ]
        else:
            ret += [None, None]
    
    ret += [
        phenotype['validation_performed'],
        #phenotype['validation_description'],
        phenotype['publication_doi'],
        phenotype['publication_link'],
        #phenotype['secondary_publication_links'],
        phenotype['source_reference'],
        phenotype['citation_requirements']
        ]
    
    implementation = phenotype['implementation'] 
    if len(str(phenotype['phenoflowid'])) >0 :
        implementation += "   " + "PhenoFlow Implementation: https://kclhi.org/phenoflow/phenotype/download/" + str(phenotype['phenoflowid'])
        
    ret += [
        implementation,
        phenotype['publications']
        ]
    
    if is_authenticated_user:    
        ret +=[
            phenotype['owner'],
            dict(Permissions.PERMISSION_CHOICES)[phenotype['owner_access']],
            phenotype['group'],
            dict(Permissions.PERMISSION_CHOICES)[phenotype['group_access']],
            dict(Permissions.PERMISSION_CHOICES)[phenotype['world_access']],
        ]
    
        # may come from phenotype live version / or history
        if (phenotype['is_deleted'] == True or Phenotype.objects.get(pk=pk).is_deleted == True):
            ret += [True]
        else:
            ret += [None]

    # concepts
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

    # concepts
    ret += [ret_concepts]

    # versions
    ret += [get_visible_versions_list(request, Phenotype, pk, is_authenticated_user) ]

    rows_to_return.append(ordr(list(zip(titles, ret))))

    return Response(rows_to_return, status=status.HTTP_200_OK)


