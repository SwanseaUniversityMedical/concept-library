from django.contrib.auth.mixins import LoginRequiredMixin #, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse_lazy, reverse
from django.db import transaction #, models, IntegrityError
from django.http import HttpResponseRedirect #, StreamingHttpResponse, HttpResponseForbidden
from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.generic import DetailView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import CreateView, UpdateView #, DeleteView
from django.contrib.auth.models import User
from django.conf import settings
from simple_history.models import HistoricalRecords
import time

#from ..forms.ConceptForms import ConceptForm, ConceptUploadForm
from ..models import *
from View import *
from .. import db_utils
from .. import utils
from ..permissions import *
from django.utils.timezone import now
from datetime import datetime

logger = logging.getLogger(__name__)

from django.core.exceptions import  PermissionDenied
from django.db import connection, connections #, transaction
import json
import os



    
def run_statistics(request):
#     if not request.user.is_superuser:
#         raise PermissionDenied


    if settings.CLL_READ_ONLY:
        raise PermissionDenied
         
    
    if request.method == 'GET':
        stat = save_statistics(request)
        return render(request, 
                        'clinicalcode/admin/run_statistics.html', 
                        {
                            'successMsg': ['HDR-UK statistics saved'],
                            'stat': stat
                        }
                    )
        

 
def save_statistics(request):
    stat = get_HDRUK_statistics(request)
    
    if Statistics.objects.all().filter(org__iexact = 'HDRUK', type__iexact = 'landing-page').exists():
        HDRUK_stat = Statistics.objects.get(org__iexact = 'HDRUK', type__iexact = 'landing-page')
        HDRUK_stat.stat = stat
        HDRUK_stat.updated_by = [None, request.user][request.user.is_authenticated()]
        HDRUK_stat.modified = datetime.now()
        HDRUK_stat.save()
        
        return [stat, HDRUK_stat.id]
    else:
        obj, created = Statistics.objects.get_or_create(
                                    org = 'HDRUK',
                                    type = 'landing-page',
                                    stat = stat,
                                    created_by = [None, request.user][request.user.is_authenticated()]                                    
                                )
    
        return [stat , obj.id]
    
    
def get_HDRUK_statistics(request):
    '''
        get HDRUK statistics for display in the HDR UK homepage.
    '''   

    HDRUK_brand_collection_ids = db_utils.get_brand_collection_ids('HDRUK')
    HDRUK_brand_collection_ids = [str(i) for i in HDRUK_brand_collection_ids]
        
    filter_cond = " 1=1 "
    if HDRUK_brand_collection_ids:
        filter_cond += " AND tags && '{" + ','.join(HDRUK_brand_collection_ids) + "}' "
        
    HDRUK_published_concepts = db_utils.get_visible_live_or_published_concept_versions(request
                                            , get_live_and_or_published_ver = 2 # 1= live only, 2= published only, 3= live+published 
                                            , exclude_deleted = False
                                            , filter_cond = filter_cond
                                            , show_top_version_only = False
                                            )
    
    HDRUK_published_concepts_ids = db_utils.get_list_of_visible_entity_ids(HDRUK_published_concepts
                                                                            , return_id_or_history_id = "id")
    
    HDRUK_published_concepts_id_version = db_utils.get_list_of_visible_entity_ids(HDRUK_published_concepts
                                                                            , return_id_or_history_id = "both")
        
    #--------------------------
    filter_cond = " 1=1 "
    if HDRUK_brand_collection_ids:
        filter_cond += " AND tags && '{" + ','.join(HDRUK_brand_collection_ids) + "}' "
        
    HDRUK_published_phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(request
                                            , get_live_and_or_published_ver = 2 # 1= live only, 2= published only, 3= live+published 
                                            , exclude_deleted = False
                                            , filter_cond = filter_cond
                                            , show_top_version_only = False
                                            )
    
    HDRUK_published_phenotypes_ids = db_utils.get_list_of_visible_entity_ids(HDRUK_published_phenotypes
                                                                            , return_id_or_history_id = "id")
        
    #return {}
    return  {
                # ONLY PUBLISHED COUNTS HERE
                'published_concept_count': len(HDRUK_published_concepts_ids),   #PublishedConcept.objects.filter(concept_id__in = HDRUK_published_concepts_ids).values('concept_id').distinct().count(),
                'published_phenotype_count': len(HDRUK_published_phenotypes_ids),   # PublishedPhenotype.objects.filter(phenotype_id__in = HDRUK_published_phenotypes_ids).values('phenotype_id').distinct().count(),
                'published_clinical_codes': get_published_clinical_codes(HDRUK_published_concepts_id_version),
                'datasources_component_count': DataSource.objects.all().count(),
                'clinical_terminologies': 9, # number of coding systems
                # terminologies to be added soon

            }


def get_published_clinical_codes(published_concepts_id_version):
    '''
        count (none distinct) the clinical codes 
        in published concepts and phenotypes
    '''

    count = 0
    
    # count codes in published concepts
    # (to publish a phenotype you need to publish its concepts first)
    # so this count will also include any code in published phenotypes as well.
    
    #published_concepts_id_version = PublishedConcept.objects.values_list('concept_id' , 'concept_history_id')
    for c in published_concepts_id_version:
        cc = len(db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id = c[0], concept_history_id = c[1]))
        count = count + cc
        

    return count       

def run_statistics_collections(request):
    brands = Brand.objects.all()
    brand_list = list(brands.values_list('name', flat=True))

    if settings.CLL_READ_ONLY:
        raise PermissionDenied
    if request.method == 'GET':
        for brand in brand_list:
            save_statistics_collections(request, 'concept', brand)
            save_statistics_collections(request, 'phenotype', brand)
        save_statistics_collections(request, 'concept', brand='')
        save_statistics_collections(request, 'phenotype', brand='')

    return render(request,
                  'clinicalcode/admin/run_statistics.html',
                  {
                      'successMsg': ['Collection/Phenotype statistics saved'],
                  }
                  )


# Function to insert statistics to the table clinicalcode_statistics.
# This will include the number of collections associated with each brand for phenotype/concepts.
# The code will not update if an existing unchanged record exists.

def save_statistics_collections(request, concept_or_phenotype, brand):
    if concept_or_phenotype == 'concept':
        concept_stat = get_brand_collections(request, 'concept', force_brand=brand)
        if Statistics.objects.all().filter(org__iexact=brand, type__iexact='CONCEPT_COLLECTIONS').exists():
            concept_stat = Statistics.objects.get(org__iexact=brand, type__iexact='CONCEPT_COLLECTIONS')
            concept_stat.stat = concept_stat
            concept_stat.updated_by = [None, request.user][request.user.is_authenticated()]
            concept_stat.modified = datetime.now()
            return [concept_stat, concept_stat.id]
        else:

            obj, created = Statistics.objects.get_or_create(
                modified=datetime.now(),
                created=datetime.now(),
                org=brand,
                type='CONCEPT_COLLECTIONS',
                stat=concept_stat,
                created_by=[None, request.user][request.user.is_authenticated()],
                updated_by=[None, request.user][request.user.is_authenticated()]
            )
    else:
        if concept_or_phenotype == 'phenotype':
            concept_stat = get_brand_collections(request, 'phenotype', force_brand=brand)
            if Statistics.objects.all().filter(org__iexact=brand, type__iexact='PHENOTYPE_COLLECTIONS').exists():
                concept_stat = Statistics.objects.get(org__iexact=brand, type__iexact='PHENOTYPE_COLLECTIONS')
                concept_stat.stat = concept_stat
                concept_stat.updated_by = [None, request.user][request.user.is_authenticated()]
                concept_stat.modified = datetime.now()
                return [concept_stat, concept_stat.id]
            else:
                obj, created = Statistics.objects.get_or_create(
                    modified=datetime.now(),
                    created=datetime.now(),
                    org=brand,
                    type='PHENOTYPE_COLLECTIONS',
                    stat=concept_stat,
                    created_by=[None, request.user][request.user.is_authenticated()],
                    updated_by=[None, request.user][request.user.is_authenticated()]
                )
        return [concept_stat, obj.id]


# Gathers all of the unique collection IDs for a particular brand
# ForceBrand = Brand Name to search via, concept_or_phenotype will
def get_brand_collections(request, concept_or_phenotype, force_brand=None):
    if concept_or_phenotype == 'concept':
        data = db_utils.get_visible_live_or_published_concept_versions(request, exclude_deleted=False,
                                                                       force_brand=force_brand)
    elif concept_or_phenotype == 'phenotype':
        data = db_utils.get_visible_live_or_published_phenotype_versions(request, exclude_deleted=False,
                                                                         force_brand=force_brand)

    Tag_List = []
    for i in data:
        if i['tags'] is not None:
            Tag_List = Tag_List + i['tags']
    unique_tags_ids = []
    unique_tags_ids = list(set(Tag_List))
    return list(Tag.objects.filter(id__in=unique_tags_ids, tag_type=2).values_list('id', flat=True))
