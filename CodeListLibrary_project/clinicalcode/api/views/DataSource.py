import json
# from clinicalcode.context_processors import clinicalcode
from collections import OrderedDict
from collections import OrderedDict as ordr
from datetime import datetime

from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import PermissionDenied
from django.core.validators import URLValidator
from django.db.models import Q
from django.db.models.aggregates import Max
from django.http.response import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import (api_view, authentication_classes, permission_classes)
from rest_framework.response import Response

from ...db_utils import *
from ...models import *
from ...permissions import *
from ...utils import *
from ..serializers import *
from .View import *

from drf_yasg.utils import swagger_auto_schema

# Don't show in Swagger
@swagger_auto_schema(method='post', auto_schema=None)
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

        # remove brand from ds
        #brand_id = request.data.get('brand_id')
        #new_datasource.brand = Brand.objects.get(id=brand_id)

        new_datasource.created_by = request.user

        is_valid, errors_dict = isValidDataSource(request, new_datasource)
        if not is_valid:
            return Response(data=errors_dict,
                            content_type="json",
                            status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            #    check if already exists
            #if not DataSource.objects.filter(name=new_datasource.name, uid=new_datasource.uid, url=new_datasource.url, description=new_datasource.description).exists():
            if not DataSource.objects.filter(name__iexact=new_datasource.name.strip()).exists():
                new_datasource.save()
                created_ds = DataSource.objects.get(pk=new_datasource.pk)
                created_ds.history.latest().delete()

                # created_ds.changeReason = "Created from API"
                # created_ds.save()
                save_Entity_With_ChangeReason(DataSource, created_ds.pk, "Created from API")

                data = {
                    'message': 'DataSource created successfully',
                    'id': created_ds.pk
                }
                return Response(data=data,
                                content_type="text/json-comment-filtered",
                                status=status.HTTP_201_CREATED)

            else:
                #existed_id = DataSource.objects.get(name=new_datasource.name, uid=new_datasource.uid, url=new_datasource.url, description=new_datasource.description).id
                existed_id = DataSource.objects.get(name__iexact=new_datasource.name.strip()).id
                data = {
                    'message':
                    'DataSource created successfully',  # left the msg as it in create case not to confuse the scraper
                    'id': existed_id
                }
                return Response(data=data,
                                content_type="text/json-comment-filtered",
                                status=status.HTTP_201_CREATED)


#--------------------------------------------------------------------------
#disable authentication for this function
@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def published_data_sources(request,
                           pk=None,
                           get_live_phenotypes=False,
                           show_published_data_only=False):
    '''
        Get the API output for the list of data sources included in published phenotypes.
    '''
    return get_data_sources(request,
                            pk=pk,
                            get_live_phenotypes=get_live_phenotypes,
                            show_published_data_only=show_published_data_only,
                            is_authenticated_user=False)


#--------------------------------------------------------------------------
@api_view(['GET'])
def data_sources(request,
                pk=None,
                get_live_phenotypes=False,
                show_published_data_only=False):
    '''
        Get the API output for the list of user data sources.
    '''
    return get_data_sources(request,
                            pk=pk,
                            get_live_phenotypes=get_live_phenotypes,
                            show_published_data_only=show_published_data_only,
                            is_authenticated_user=True)


#--------------------------------------------------------------------------
@robots()
def get_data_sources(request,
                    pk=None,
                    get_live_phenotypes=False,
                    show_published_data_only=False,
                    is_authenticated_user=True):

    if pk is not None:
        data_source_id = pk
    else:
        data_source_id = request.query_params.get('id', None)

    # set phenotype search status
    # 1= live only, 2= published only, 3= live+published
    # based on show_published_data_only / get_live_phenotypes
    live_and_or_published_ver = 3
    if show_published_data_only:
        live_and_or_published_ver = 2

    # --- when in a brand, show only this brand's data
    # get only brands used inside the phenotypes of the current brand (or all, if no brand)
    phenotypes = get_visible_live_or_published_phenotype_versions(request,
                                                                get_live_and_or_published_ver=live_and_or_published_ver,  # 1= live only, 2= published only, 3= live+published 
                                                                exclude_deleted=True,
                                                                show_top_version_only=[False, True][get_live_phenotypes],
                                                                force_get_live_and_or_published_ver=live_and_or_published_ver
                                                                )

    phenotypes_ids = get_list_of_visible_entity_ids(phenotypes, return_id_or_history_id="id")

    datasource_ids = list(set(list(PhenotypeDataSourceMap.history.filter(phenotype_id__in=phenotypes_ids).values_list('datasource_id', flat=True))))

    queryset = DataSource.objects.filter(id__in=datasource_ids)

    keyword_search = request.query_params.get('search', None)
    if keyword_search is not None:
        queryset = queryset.filter(name__icontains=keyword_search)

    if data_source_id is not None:
        queryset = queryset.filter(id=data_source_id)

    queryset = queryset.order_by('name')

    rows_to_return = []
    titles = ['id', 'name', 'url', 'uid', 'description','datasource_id' , 'phenotypes']

    for ds in queryset:
        ret = [
            ds.id,
            ds.name.encode('ascii', 'ignore').decode('ascii'), ds.url, ds.uid,
            ds.description,
            ds.datasource_id
        ]
        if get_live_phenotypes:
            ret.append(
                get_LIVE_phenotypes_associated_with_data_source(ds.id,
                                                                phenotypes_ids,
                                                                show_published_data_only=show_published_data_only)
                                                                )
        else:
            ret.append(
                get_HISTORICAl_phenotypes_associated_with_data_source(ds.id,
                                                                      phenotypes_ids,
                                                                      show_published_data_only=show_published_data_only)
                                                                    )

        rows_to_return.append(ordr(list(zip(titles, ret))))

    if rows_to_return:
        return Response(rows_to_return, status=status.HTTP_200_OK)
    else:
        raise Http404
        #return Response(rows_to_return, status=status.HTTP_404_NOT_FOUND)


def get_LIVE_phenotypes_associated_with_data_source(
        data_source_id, brand_phenotypes_ids, show_published_data_only=False):

    # return LIVE phenotypes associated with data_source
    phenotype_ids = list(set(list(PhenotypeDataSourceMap.objects.filter(datasource_id=data_source_id, phenotype_id__in=brand_phenotypes_ids).values_list('phenotype_id', flat=True))))
    phenotypes = Phenotype.objects.filter(id__in=phenotype_ids).order_by('name')

    rows_to_return = []
    titles = [
        'phenotype_id', 'phenotype_version_id', 'phenotype_name',
        'phenotype_uuid', 'phenotype_author'
    ]
    for p in phenotypes:
        phenotype_latest_history_id = Phenotype.objects.get(pk=p.id).history.latest().history_id

        if show_published_data_only:
            is_published = checkIfPublished(Phenotype, p.id, phenotype_latest_history_id)
            if not is_published:
                continue

        ret = [
            p.friendly_id, phenotype_latest_history_id,
            p.name.encode('ascii', 'ignore').decode('ascii'), p.phenotype_uuid,
            p.author
        ]
        rows_to_return.append(ordr(list(zip(titles, ret))))

    return rows_to_return


def get_HISTORICAl_phenotypes_associated_with_data_source(
        data_source_id, brand_phenotypes_ids, show_published_data_only=False):

    # return HISTORICAl phenotypes associated with data_source
    associated_phenotype_ids = list(set(list(PhenotypeDataSourceMap.history.filter(datasource_id=data_source_id, phenotype_id__in=brand_phenotypes_ids).values_list('phenotype_id', flat=True))))

    ver_to_return = []
    rows_to_return = []
    ph_titles = ['phenotype_id', 'versions']
    ver_titles = [
        'phenotype_id', 'phenotype_version_id', 'phenotype_name',
        'phenotype_uuid', 'phenotype_author', 'is_latest'
    ]

    for p_id in associated_phenotype_ids:
        ver_to_return = []
        # get versions obj
        associated_phenotype_versions = Phenotype.objects.get(pk=p_id).history.all().order_by('-history_id')
        max_version_id = associated_phenotype_versions.aggregate(Max('history_id'))['history_id__max']
        include_this_phenotype = False
        for ver in associated_phenotype_versions:
            if show_published_data_only:
                is_published = checkIfPublished(Phenotype, p_id, ver.history_id)
                if not is_published:
                    continue

            data_sources_history = getHistoryDataSource_Phenotype(p_id, ver.history_date)
            if data_sources_history:
                phenotype_ds_list = [i['datasource_id'] for i in data_sources_history if 'datasource_id' in i ]

                if data_source_id in set(phenotype_ds_list):
                    ret = [
                        ver.friendly_id, ver.history_id,
                        ver.name.encode('ascii', 'ignore').decode('ascii'),
                        ver.phenotype_uuid, ver.author,
                        [False, True][ver.history_id == max_version_id]
                    ]
                    ver_to_return.append(ordr(list(zip(ver_titles, ret))))
                    include_this_phenotype = True
                else:
                    pass
        if include_this_phenotype:
            rows_to_return.append(ordr(list(zip(ph_titles, ['PH' + str(p_id), ver_to_return]))))

    return rows_to_return


