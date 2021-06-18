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
from View import *
from django.db.models.aggregates import Max
from clinicalcode.models.PhenotypeDataSourceMap import PhenotypeDataSourceMap
from clinicalcode.models.Phenotype import Phenotype

@api_view(['POST'])
def api_datasource_create(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if is_member(request.user, group_name='ReadOnlyUsers'):
        raise PermissionDenied

    validate_access_to_create()
    user_groups = getGroups(request.user)
    if request.method == 'POST':
        new_datasource = DataSource()
        new_datasource.name = request.data.get('name')
        new_datasource.uid = request.data.get('uid')
        new_datasource.url = request.data.get('url')
        new_datasource.description = request.data.get('description')

        new_datasource.created_by = request.user

        is_valid, errors_dict = isValidDataSource(request, new_datasource)
        if not is_valid:
            return Response(
              data = errors_dict, 
              content_type="json", 
              status=status.HTTP_406_NOT_ACCEPTABLE
            )
        else:
            #    check if already exists 
            if not DataSource.objects.filter(name=new_datasource.name, uid=new_datasource.uid, url=new_datasource.url, description=new_datasource.description).exists():            
                new_datasource.save()
                created_ds = DataSource.objects.get(pk=new_datasource.pk)
                created_ds.history.latest().delete() 
    
                created_ds.changeReason = "Created from API"
                created_ds.save()   
                data = {
                  'message': 'DataSource created successfully',
                  'id': created_ds.pk
                }
                return Response(
                  data = data, 
                  content_type="text/json-comment-filtered", 
                  status=status.HTTP_201_CREATED
                )
                
            else:
                existed_id = DataSource.objects.get(name=new_datasource.name, uid=new_datasource.uid, url=new_datasource.url, description=new_datasource.description).id
                data = {
                  'message': 'DataSource created successfully', # left the msg as it in create case not to confuse the scraper
                  'id': existed_id
                }
                return Response(
                  data = data, 
                  content_type="text/json-comment-filtered", 
                  status=status.HTTP_201_CREATED
                )
                
                
                

#--------------------------------------------------------------------------
@api_view(['GET'])
def get_data_source(request, pk=None, get_live_phenotypes=False):   
    
    if pk is not None:
        data_source_id = pk
    else:   
        data_source_id = request.query_params.get('id', None)
        

    queryset = DataSource.objects.all()
    
    keyword_search = request.query_params.get('search', None)
    if keyword_search is not None:
        queryset = queryset.filter(name__icontains=keyword_search)
    
    if data_source_id is not None:
        queryset = queryset.filter(id=data_source_id)

    queryset = queryset.order_by('name')
   
        
    rows_to_return = []
    titles = ['id', 'name', 'url', 'uid', 'description', 'phenotypes']
        
    for ds in queryset:
        ret = [
                ds.id,  
                ds.name.encode('ascii', 'ignore').decode('ascii'),
                ds.url,
                ds.uid,
                ds.description
            ]
        if get_live_phenotypes:
            ret.append(get_LIVE_phenotypes_associated_with_data_source(ds.id))
        else:
            ret.append(get_HISTORICAl_phenotypes_associated_with_data_source(ds.id))
            
        rows_to_return.append(ordr(zip(titles,  ret )))
        
        
    
    return Response(rows_to_return, status=status.HTTP_200_OK)   
        
         
def get_LIVE_phenotypes_associated_with_data_source(data_source_id):   
    
    # return LIVE phenotypes associated with data_source
    phenotype_ids = list(PhenotypeDataSourceMap.objects.filter(datasource_id=data_source_id).values_list('phenotype_id', flat=True))
    phenotypes = Phenotype.objects.filter(id__in = phenotype_ids).order_by('name') 
    
    rows_to_return = []
    titles = ['phenotype_id', 'phenotype_version_id', 'phenotype_name', 'phenotype_uuid', 'phenotype_author']
    for p in phenotypes:
        ret = [
                p.id,  
                Phenotype.objects.get(id=p.id).history.latest().history_id,
                p.name.encode('ascii', 'ignore').decode('ascii'),
                p.phenotype_uuid,
                p.author
            ]
        rows_to_return.append(ordr(zip(titles,  ret )))
        
    return rows_to_return

    
def get_HISTORICAl_phenotypes_associated_with_data_source(data_source_id):   
    
    # return HISTORICAl phenotypes associated with data_source
    associated_phenotype_ids = list(PhenotypeDataSourceMap.objects.filter(datasource_id=data_source_id).values_list('phenotype_id', flat=True))
    
    ver_to_return = []
    rows_to_return = []
    ph_titles = ['phenotype_id', 'versions']
    ver_titles = ['phenotype_id', 'phenotype_version_id', 'phenotype_name', 'phenotype_uuid', 'phenotype_author']
    
    for p_id in associated_phenotype_ids:
        ver_to_return = []
        # get version obj
        associated_phenotype_versions = Phenotype.history.filter(id=p_id)
        for ver in associated_phenotype_versions:  
            data_sources_history = getHistoryDataSource_Phenotype(p_id, ver.history_date)
            if data_sources_history:
                phenotype_ds_list = [i['datasource_id'] for i in data_sources_history if 'datasource_id' in i]
                
                if data_source_id in set(phenotype_ds_list):
                    ret = [
                            p_id,  
                            ver.history_id,
                            ver.name.encode('ascii', 'ignore').decode('ascii'),
                            ver.phenotype_uuid,
                            ver.author
                        ]
                    ver_to_return.append(ordr(zip(ver_titles,  ret )))
                else:
                    pass      
        
        rows_to_return.append(ordr(zip(ph_titles,  [p_id, ver_to_return] )))
         
    return rows_to_return





    
    
    
        