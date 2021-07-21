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
    if not request.user.is_superuser:
        raise PermissionDenied
        
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
    stat = get_HDRUK_statistics()
    
    if Statistics.objects.all().filter(org__iexact = 'HDRUK', type__iexact = 'landing-page').exists():
        HDRUK_stat = Statistics.objects.get(org__iexact = 'HDRUK', type__iexact = 'landing-page')
        HDRUK_stat.stat = stat
        HDRUK_stat.updated_by = request.user
        HDRUK_stat.modified = datetime.now()
        HDRUK_stat.save()
        
        return [stat, HDRUK_stat.id]
    else:
        obj, created = Statistics.objects.get_or_create(
                                    org = 'HDRUK',
                                    type = 'landing-page',
                                    stat = stat,
                                    created_by = request.user,                                    
                                )
    
        return [stat , obj.id]
    
    
def get_HDRUK_statistics():
    '''
        get HDRUK statistics for display in the HDR UK homepage.
    '''   

    return  {
                # ONLY PUBLISHED COUNTS HERE
                'published_concept_count': PublishedConcept.objects.values('concept_id').distinct().count(),
                'published_phenotype_count': PublishedPhenotype.objects.values('phenotype_id').distinct().count(),
                'published_clinical_codes': get_published_clinical_codes(),
                'datasources_component_count': DataSource.objects.all().count(),
                'clinical_terminologies': 9, # number of coding systems
                # terminologies to be added soon

            }


def get_published_clinical_codes():
    '''
        count (none distinct) the clinical codes 
        in published concepts and phenotypes
    '''

    from ..db_utils import getGroupOfCodesByConceptId_HISTORICAL
    count = 0
    
    #return 650645
    # count codes in published concepts
    # (to publish a phenotype you need to publish its concepts first)
    # so this count will also include any code in published phenotypes as well.
    
    published_concepts_id_version = PublishedConcept.objects.values_list('concept_id' , 'concept_history_id')
    for c in published_concepts_id_version:
        cc = len(getGroupOfCodesByConceptId_HISTORICAL(concept_id = c[0], concept_history_id = c[1]))
        count = count + cc
        

    return count       


