from rest_framework import viewsets, status
from rest_framework.decorators import detail_route, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.http.response import Http404
from django.db.models import Q

from ..serializers import *

from ...models.Concept import Concept
from ...models.Tag import Tag
from ...models.Phenotype import Phenotype
from ...models.PhenotypeTagMap import PhenotypeTagMap
from ...models.DataSource import DataSource
from ...models.Brand import Brand

from django.contrib.auth.models import User

from ...db_utils import *
from ...viewmodels.js_tree_model import TreeModelManager
from ...permissions import *

from collections import OrderedDict
from django.core.exceptions import PermissionDenied
import json
from clinicalcode.context_processors import clinicalcode
from collections import OrderedDict as ordr
from ...utils import *
from numpy.distutils.fcompiler import none

from django.core import serializers
from datetime import datetime
from django.core.validators import URLValidator
from View import chk_group, chk_group_access, chk_tags, chk_world_access
from django.db.models.aggregates import Max

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

        known_phenotypes = set(get_visible_phenotypes(request.user).exclude(is_deleted=True).values_list('phenotype_id', flat=True))
        new_phenotype_id = request.data.get('phenotype_id')
        if new_phenotype_id in known_phenotypes:
          return Response(
            data = {'phenotype_id': 'Phenotype_id must be unique: submitted id is already found'}, 
            content_type="json", 
            status=status.HTTP_406_NOT_ACCEPTABLE
          )

        new_phenotype = Phenotype()
        new_phenotype.phenotype_id = new_phenotype_id
        new_phenotype.title = request.data.get('title')
        new_phenotype.name = request.data.get('name')
        new_phenotype.author = request.data.get('author')
        new_phenotype.layout = request.data.get('layout')
        new_phenotype.type = request.data.get('type')
        new_phenotype.validation = request.data.get('validation')
        new_phenotype.valid_event_data_range_start = request.data.get('valid_event_data_range_start')
        new_phenotype.valid_event_data_range_end = request.data.get('valid_event_data_range_end')
        new_phenotype.sex = request.data.get('sex')
        new_phenotype.status = request.data.get('status')
        new_phenotype.hdr_created_date = request.data.get('hdr_created_date')
        new_phenotype.hdr_modified_date = request.data.get('hdr_modified_date')
        new_phenotype.publications = request.data.get('publications')
        new_phenotype.publication_doi = request.data.get('publication_doi')
        new_phenotype.publication_link = request.data.get('publication_link')
        new_phenotype.secondary_publication_links = request.data.get('secondary_publication_links')
        new_phenotype.source_reference = request.data.get('source_reference') 
        new_phenotype.citation_requirements = request.data.get('citation_requirements')
        new_phenotype.concept_informations = request.data.get('concept_informations')
        
        new_phenotype.created_by = request.user        
        new_phenotype.owner_access = Permissions.EDIT
        new_phenotype.owner_id = request.user.id

        concept_ids_list = request.data.get('concept_informations')
        if concept_ids_list is None or not isinstance(concept_ids_list, list):
            errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
        else:
            if len(concept_ids_list) == 0:
                errors_dict['concept_informations'] = 'concept_informations must have a valid non-empty concept ids list'
            else:
                if not chkListIsAllIntegers(concept_ids_list):
                    errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
                else: 
                    if len(set(concept_ids_list)) != len(concept_ids_list):
                        errors_dict['concept_informations'] = 'concept_informations must have a unique concept ids list'
                    else:
                        permittedConcepts = get_list_of_visible_concept_ids(get_visible_live_or_published_concept_versions(request , exclude_deleted = True)
                                                                            , return_id_or_history_id="id")
                        if not (set(concept_ids_list).issubset(set(permittedConcepts))):
                            errors_dict['concept_informations'] = 'invalid concept_informations ids list, all concept ids must be valid and accessible by user'
                        else:
                            #print('')
                            concept_informations = getPhenotypeConceptJson(concept_ids_list) #concept.history.latest.pkid
                            new_phenotype.concept_informations = concept_informations

        # group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
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
        is_valid_data, err, ret_value = chk_world_access(request.data.get('world_access'))
        if is_valid_data:
            new_phenotype.world_access = ret_value
        else:
            errors_dict['world_access'] = err        

        # handling tags  
        tags = request.data.get('tags')
        is_valid_data, err, ret_value = chk_tags(request.data.get('tags'))
        if is_valid_data:
            tags = ret_value
        else:
            errors_dict['tags'] = err  
           
        # Validation
        errors_pt = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_pt = True
        is_valid_pt, errors_pt = isValidPhenotype(request, new_phenotype)
        
        if not is_valid or not is_valid_pt:          
            errors_dict.update(errors_pt)
            return Response(
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        else:
            new_phenotype.save()
            created_pt = Phenotype.objects.get(pk=new_phenotype.pk)
            created_pt.history.latest().delete() 
             
            tag_ids = tags
            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids]
            if tag_ids:
                for tag_id_to_add in new_tag_list:
                    PhenotypeTagMap.objects.get_or_create(phenotype=new_phenotype, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)
            
            datasource_ids_list = request.data.get('data_sources')
            for cur_id in datasource_ids_list:
              new_phenotype.data_sources.add(
                int(cur_id)
              )

            created_pt.changeReason = "Created from API"
            created_pt.save()   
            data = {
              'message': 'Phenotype created successfully',
              'id': created_pt.pk
            }
            return Response(
              data = data, 
              content_type="text/json-comment-filtered", 
              status=status.HTTP_201_CREATED
            )

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
        if not isInt(phenotype_id):
            errors_dict['id'] = 'phenotype_id must be a valid id.' 
            return Response(
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        
        if Phenotype.objects.filter(pk=phenotype_id).count() == 0: 
            errors_dict['id'] = 'phenotype_id not found.' 
            return Response( 
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        if not allowed_to_edit(request.user, Phenotype, phenotype_id):
            errors_dict['id'] = 'phenotype_id must be a valid accessible phenotype id.' 
            return Response( 
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        
        update_phenotype = Phenotype.objects.get(pk=phenotype_id)
        update_phenotype.phenotype_id = request.data.get('phenotype_id')
        update_phenotype.title = request.data.get('title')
        update_phenotype.name = request.data.get('name')
        update_phenotype.author = request.data.get('author')
        update_phenotype.layout = request.data.get('layout')
        update_phenotype.type = request.data.get('type')
        update_phenotype.validation = request.data.get('validation')
        update_phenotype.valid_event_data_range_start = request.data.get('valid_event_data_range_start')
        update_phenotype.valid_event_data_range_end = request.data.get('valid_event_data_range_end')
        update_phenotype.sex = request.data.get('sex')
        update_phenotype.status = request.data.get('status')
        update_phenotype.hdr_created_date = request.data.get('hdr_created_date')
        update_phenotype.hdr_modified_date = request.data.get('hdr_modified_date')
        update_phenotype.publications = request.data.get('publications')
        update_phenotype.publication_doi = request.data.get('publication_doi')
        update_phenotype.publication_link = request.data.get('publication_link')
        update_phenotype.secondary_publication_links = request.data.get('secondary_publication_links')
        #update_phenotype.source_reference = request.data.get('source_reference') # With data_sources I don't think this is needed
        update_phenotype.citation_requirements = request.data.get('citation_requirements')
        update_phenotype.concept_informations = request.data.get('concept_informations')
        
        update_phenotype.updated_by = request.user        
        update_phenotype.modified = datetime.now() 
        
        # concepts
        concept_ids_list = request.data.get('concept_informations')
        if concept_ids_list is None or not isinstance(concept_ids_list, list):
            errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
        else:
            if len(concept_ids_list) == 0:
                errors_dict['concept_informations'] = 'concept_informations must have a valid non-empty concept ids list'
            else:
                if not chkListIsAllIntegers(concept_ids_list):
                    errors_dict['concept_informations'] = 'concept_informations must have a valid concept ids list'
                else: 
                    if len(set(concept_ids_list)) != len(concept_ids_list):
                        errors_dict['concept_informations'] = 'concept_informations must have a unique concept ids list'
                    else:
                        permittedConcepts = get_list_of_visible_concept_ids(
                                                                            get_visible_live_or_published_concept_versions(request , exclude_deleted = True)
                                                                            , return_id_or_history_id="id")
                        if not (set(concept_ids_list).issubset(set(permittedConcepts))):
                            errors_dict['concept_informations'] = 'invalid concept_informations ids list, all concept ids must be valid and accessible by user'
                        else:
                            concept_informations = convert_concept_ids_to_WSjson(concept_ids_list , no_attributes=True)
                            update_phenotype.concept_informations = concept_informations
                            update_phenotype.concept_version = getWSConceptsHistoryIDs(concept_informations, concept_ids_list = concept_ids_list)

        """data_sources = request.data.get('data_sources')
        if data_sources is None:
          update_phenotype.data_sources = None
        elif not isinstance(data_sources, list):
          errors_dict['data_sources'] = 'data_sources must be a valid list of data_source ids'
        else:
          if len(data_sources) == 0:
            errors_dict['data_sources'] = 'data_sources must be a valid non-empty list of data_source ids'
          else:
            if len(set(data_sources)) != len(data_sources):
              errors_dict['data_sources'] = 'data_sources must be a unique list of data_source ids'
            else:
              known_sources = set(get_visible_data_sources(request.user).exclude(is_deleted=True).values_list('id', flat=True))
              if not set(data_sources).issubset(known_sources):
                errors_dict['data_sources'] = 'Invalid data_sources ids listed, all data_source ids must be valid and accessible by the user'
              else:
                update_phenotype.data_sources = data_sources"""

        """clinical_terminologies = request.data.get('clinical_terminologies')
        if clinical_terminologies is None:
          update_phenotype.clinical_terminologies = None
        elif not isinstance(clinical_terminologies, list):
          errors_dict['clinical_terminologies'] = 'clinical_terminologies must be a valid list of clinical_terminology ids'
        else:
          if len(clinical_terminologies) == 0:
            errors_dict['clinical_terminologies'] = 'clinical_terminologies must be a valid non-empty list of clinical_terminology ids'
          else:
            if len(set(clinical_terminologies)) != len(clinical_terminologies):
              errors_dict['clinical_terminologies'] = 'clinical_terminologies must be a unique list of clinical_terminology ids'
            else:
              known_sources = set(get_visible_clinical_terminologies(request.user).exclude(is_deleted=True).values_list('id', flat=True))
              if not set(clinical_terminologies).issubset(known_sources):
                errors_dict['clinical_terminologies'] = 'Invalid clinical_terminologies ids listed, all clinical_terminology ids must be valid and accessible by the user'
              else:
                update_phenotype.clinical_terminologies = clinical_terminologies"""

        #  group id 
        is_valid_data, err, ret_value = chk_group(request.data.get('group') , user_groups)
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
        else:
            errors_dict['tags'] = err  

        # Validation
        errors_pt = {}
        if bool(errors_dict):
            is_valid = False
            
        is_valid_pt = True
        is_valid_pt, errors_pt = isValidPhenotype(request, update_phenotype)
        if not is_valid or not is_valid_pt:        
            errors_dict.update(errors_pt)
            return Response(
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        else:
            tag_ids = tags
            new_tag_list = []

            if tag_ids:
                new_tag_list = [int(i) for i in tag_ids]

            old_tag_list = list(PhenotypeTagMap.objects.filter(phenotype=update_phenotype).values_list('tag', flat=True))
            tag_ids_to_add = list(set(new_tag_list) - set(old_tag_list))
            tag_ids_to_remove = list(set(old_tag_list) - set(new_tag_list))

            for tag_id_to_add in tag_ids_to_add:
                PhenotypeTagMap.objects.get_or_create(phenotype=update_phenotype, tag=Tag.objects.get(id=tag_id_to_add), created_by=request.user)

            for tag_id_to_remove in tag_ids_to_remove:
                tag_to_remove = PhenotypeTagMap.objects.filter(phenotype=update_phenotype, tag=Tag.objects.get(id=tag_id_to_remove))
                tag_to_remove.delete()
                         
            update_phenotype.changeReason = "Updated from API"
            update_phenotype.save()   
            data = {
              'message': 'Phenotype updated successfully',
              'id': update_phenotype.pk
            }
            return Response(
              data = data, 
              content_type="text/json-comment-filtered", 
              status=status.HTTP_201_CREATED
            )
