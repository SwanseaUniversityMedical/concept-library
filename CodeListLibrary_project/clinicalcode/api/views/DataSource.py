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
