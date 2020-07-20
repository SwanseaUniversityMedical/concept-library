import csv
import sys
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
from django.db.models.aggregates import Max
# from django.contrib.auth.models import User
from django.conf import settings
from django.shortcuts import render
from simple_history.models import HistoricalRecords
import time

from ..models.PublishedConcept import PublishedConcept
from ..models.Brand import Brand
#from ..models.Code import Code
from ..models.Concept import Concept
from ..models.Component import Component
#from ..models.CodeList import CodeList
#from ..models.CodeRegex import CodeRegex
from ..models.ConceptTagMap import ConceptTagMap
from ..models.Tag import Tag
from clinicalcode.models.CodingSystem import CodingSystem

#from View import *
from .. import db_utils
from .. import utils
from ..permissions import (
    validate_access_to_view, get_visible_concepts,
    HasAccessToViewConceptCheckMixin,
    HasAccessToPublishCheckMixin, allowed_to_view_children, 
    getGroups
)
from django.utils.timezone import now
from datetime import datetime
from django.core.exceptions import  PermissionDenied
import json
    
    
    
def published_concept_list(request):
    '''
        Display the list of published concepts. This view can be searched and contains paging.
    '''    
    # get page index variables from query 
    page_size = utils.get_int_value(request.GET.get('page_size', 20), 20)
    page = utils.get_int_value(request.GET.get('page', 1), 1)
    concept_brand = request.GET.get('concept_brand', request.CURRENT_BRAND)
    search = request.GET.get('search', '')

    if request.method == 'POST':
        # get posted parameters
        search = request.POST.get('search', '')
        page_size = request.POST.get('page_size')
        page = request.POST.get('page', page)
        concept_brand = request.POST.get('concept_brand', request.CURRENT_BRAND)

    #########################################
    # work on concept.history and make sure it is in published concept
    all_published_history_id = list(PublishedConcept.objects.all().values_list('concept_history_id', flat=True))
    pconcepts = Concept.history.filter(history_id__in = all_published_history_id)
    
    # check if there is any search criteria supplied
    if search is not None:
        if search != '':
            pconcepts = pconcepts.filter(name__icontains=search)
            
    
    # show concepts for a specific brand
    if concept_brand != "":
        current_brand = Brand.objects.all().filter(name = concept_brand)
        pconcepts = pconcepts.filter(group__id__in = list(current_brand.values_list('groups', flat=True)))

    # for each concept_id get max historical_id
    pconcepts_ids = list(pconcepts.all().values_list('id', flat=True).distinct().order_by())
    pconcepts_history_ids = list(pconcepts.all().values_list('history_id', flat=True).distinct().order_by())
    max_historical_ids = list(PublishedConcept.objects.all().filter(concept_id__in = pconcepts_ids , concept_history_id__in = pconcepts_history_ids).values('concept_id').annotate(max_id=Max('concept_history_id')).values_list('max_id', flat=True))


    # get the latest version for each published concept (with search criteria)
    pconcepts = pconcepts.filter(history_id__in=max_historical_ids).order_by('id')

    # publish_date
    for c in pconcepts:
        c.publish_date = PublishedConcept.objects.get(concept_id=c.id, concept_history_id=c.history_id).created
       
    #########################################

    # create pagination
    paginator = Paginator(pconcepts, page_size, allow_empty_first_page=True)
    try:
        p = paginator.page(page)
    except EmptyPage:
        p = paginator.page(paginator.num_pages)

    return render(request, 
                'clinicalcode/publishedconcept/index.html', 
                {
                    'page': page,
                    'page_size': str(page_size),
                    'page_obj': p,
                    'search': search,
                    'concept_brand': concept_brand
                }
                )


def published_concept_details(request, pk, concept_history_id):
    
    # check if the concept version is published
    if not PublishedConcept.objects.filter(concept_id=pk, concept_history_id=concept_history_id).exists(): 
        raise PermissionDenied 
    

    historical_concept = db_utils.getHistoryConcept(concept_history_id)
    
    historical_concept['owner'] = User.objects.filter(pk=historical_concept['owner_id']).first()
    historical_concept['created_by'] = User.objects.filter(pk=historical_concept['created_by_id']).first()
    historical_concept['modified_by'] = User.objects.filter(pk=historical_concept['modified_by_id']).first()
    
    # publish_date
    historical_concept['publish_date'] = PublishedConcept.objects.get(concept_id=pk, concept_history_id=concept_history_id).created
    
    # get group.name to show brand for concept, if exist
    group_id = historical_concept['group_id']
    group = Group.objects.filter(pk=group_id).values('name')
    if group:
        historical_concept['group_name'] = group.all()[0]['name']
   
    brands_url = list(Brand.objects.all().values('name', 'website'))
    
    # Tree
    com_codes = get_components_tree(concept_history_id, parent=None, tree=[])
    Tree_com_codes = json.dumps(com_codes)

    # just codes, to make code list table for review
    codes = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=pk, concept_history_id=concept_history_id)


    # history
    other_versions = list(PublishedConcept.objects.filter(concept_id=pk).exclude(concept_history_id=concept_history_id)
                                                .values('concept_history_id').order_by('-concept_history_id'))
    other_historical_versions = []

    for ov in other_versions:
        ver = db_utils.getHistoryConcept(ov['concept_history_id'])
        ver['owner'] = User.objects.get(pk=ver['owner_id'])
        ver['publish_date'] = PublishedConcept.objects.get(concept_id=ver['id'], concept_history_id=ver['history_id']).created
        other_historical_versions.append(ver)


    return render(request, 
                'clinicalcode/publishedconcept/details.html', 
                {
                    'concept': historical_concept, 
                    'tree': Tree_com_codes,
                    'history': other_historical_versions, 
                    'codes': codes,
                    'brands_url': brands_url
                }
                )



def get_logical_name(logical_type):
    if logical_type == 1:
        return "Add Codes"
    else:
        return "Remove Codes"

def get_type_name(component_type):
    if component_type == 1:
        return "Concept"
    elif component_type == 2:
        return "Query Builder"
    elif component_type == 3:
        return "Expression"
    else:
        return "Select/Import"



def get_components_tree(concept_history_id, parent, tree):
    # stop this function, for now
    return []

    # check if the concept version is published    
    concept = PublishedConcept.objects.filter(concept_history_id=concept_history_id)
    if concept.count() == 0: 
        #raise PermissionDenied
        return []
    
    #return tree

    historical_concept = db_utils.getHistoryConcept(concept_history_id)
    history_date = historical_concept["history_date"]
    pk = historical_concept["id"]
    components = db_utils.getHistoryComponents(pk, history_date)

    for c in components:
        if c['component_type'] == 1:
            concept_ref_id = c["concept_ref_id"]
            concept_ref_history_id = c["concept_ref_history_id"]
            historical_child_concept = db_utils.getHistoryConcept(concept_ref_history_id)
            history_date = historical_child_concept["history_date"]
            
            component = {
                "history_id": c["history_id"],
                "name": c["name"],
                "version": concept_ref_history_id,
                "logical_type": get_logical_name(c["logical_type"]),
                "type": get_type_name(c['component_type']),
                "is_concept": True,
                "children": []
            }
            if parent is None:
                tree.append(component) 
                get_components_tree(concept_ref_history_id, parent=component["children"], tree=tree)  # tree[-1] pass reference of a parent to child
            else:
                parent.append(component)                                    
                get_components_tree(concept_ref_history_id, parent=parent[-1]["children"], tree=tree)     
        else:
            codes = c['codes']
            codes = json.dumps(codes)
            component = {
                "history_id": c["history_id"],
                "name": c["name"],
                "logical_type": get_logical_name(c["logical_type"]),
                "type": get_type_name(c['component_type']),
                "is_concept": False,
                "codes": codes
            }
            if parent is None:
                tree.append(component)
            else:
                parent.append(component)
    
    return tree



def published_concept_codes_to_csv(request, concept_history_id):
    """
        Return a csv file of distinct codes for a concept group
    """
    # check if the concept version is published    
    concept = PublishedConcept.objects.filter(concept_history_id=concept_history_id)
    if concept.count() == 0: raise PermissionDenied
        
    historical_concept = db_utils.getHistoryConcept(concept_history_id)
    
    rows = db_utils.getGroupOfCodesByConceptId_HISTORICAL(concept_id=historical_concept['id'], concept_history_id=concept_history_id)
    
    my_params = {
        'id': historical_concept['id'],
        'concept_history_id': concept_history_id,        
        'creation_date': time.strftime("%Y%m%dT%H%M%S")
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = ('attachment; filename="concept_%(id)s_ver_%(concept_history_id)s_group_codes_%(creation_date)s.csv"' % my_params)


    writer = csv.writer(response)
    titles = ['code', 'description', 'concept_id', 'concept_version_id', 'concept_name']
    writer.writerow(titles)
    
    for row in rows:
        writer.writerow([
            row['code'], #.encode('ascii', 'ignore').decode('ascii'),
            row['description'].encode('ascii', 'ignore').decode('ascii'),
            historical_concept['id'],
            concept_history_id,
            historical_concept['name'],
        ])
    return response


