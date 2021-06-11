'''
    ---------------------------------------------------------------------------
    COMMON VIEW CODE
    ---------------------------------------------------------------------------
'''
import logging
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import Group
from ..models.Concept import Concept
from ..models.Component import Component
from ..models.DataSource import DataSource
from ..models.Phenotype import Phenotype
from ..models.PublishedConcept import PublishedConcept
from ..models.PublishedPhenotype import PublishedPhenotype
from ..models.Statistics import Statistics

from ..permissions import (
    allowed_to_view, allowed_to_edit
)

logger = logging.getLogger(__name__)


def index(request):
    '''
        Display the index homepage.
    '''   
    
    if request.CURRENT_BRAND == "":
        return render(request, 'clinicalcode/index.html')
    elif request.CURRENT_BRAND == "HDRUK":
        return index_HDRUK(request)
    else:
        return render(request, 'clinicalcode/index.html')
    

def index_HDRUK(request):
    '''
        Display the HDR UK homepage.
    '''   
    
    if Statistics.objects.all().filter(org__iexact = 'HDRUK', type__iexact = 'landing-page').exists():
        HDRUK_stat = Statistics.objects.get(org__iexact = 'HDRUK', type__iexact = 'landing-page').stat
    else:
        HDRUK_stat = {
                        'published_concept_count': -1, 
                        'published_phenotype_count': -1, 
                        'published_clinical_codes': -1, 
                        'datasources_component_count': -1,
                        'clinical_terminologies': -1
                    }
    
    return render(request,
                  'clinicalcode/HDRUK/index_HDRUK.html',
                  {
                    # ONLY PUBLISHED COUNTS HERE
                    'published_concept_count': HDRUK_stat['published_concept_count'], 
                    'published_phenotype_count': HDRUK_stat['published_phenotype_count'], 
                    'published_clinical_codes': HDRUK_stat['published_clinical_codes'], 
                    'datasources_component_count': HDRUK_stat['datasources_component_count'],
                    'clinical_terminologies': HDRUK_stat['clinical_terminologies']
                  }
                )



def about_pages(request, pg_name=None):
    '''
        manage about pages
    '''   

    # main CL about page
    if pg_name.lower() == "cl_about_page":
        return render(request, 'clinicalcode/cl-about.html', {})
    
    # HDR-UK about pages                    
    if pg_name.lower() == "hdruk_about_the_project":
        return render(request, 'clinicalcode/HDRUK/about/about-the-project.html', {})
    
    elif pg_name.lower() == "hdruk_about_team":
        return render(request, 'clinicalcode/HDRUK/about/team.html', {})
    
    elif pg_name.lower() == "hdruk_about_technical_details":
        return render(request, 'clinicalcode/HDRUK/about/technical-details.html', {})
    
    elif pg_name.lower() == "hdruk_about_covid_19_response":
        return render(request, 'clinicalcode/HDRUK/about/covid-19-response.html', {})
    
    elif pg_name.lower() == "hdruk_about_publications":
        return render(request, 'clinicalcode/HDRUK/about/publications.html', {})
    
    else:
        return render(request,
                    'clinicalcode/cl-about.html',
                    {}
                )




def build_permitted_components_list(user, concept_id, concept_history_id=None, check_published_child_concept=False):
    '''
        Look through the components that are associated with the specified
        concept ID and decide whether each has view and edit permission for
        the specified user.
    '''
    user_can_view_components = []
    user_can_edit_components = []
    component_error_msg_view = {}
    component_error_msg_edit = {}
    component_concpet_version_msg = {}
    
    components = Component.objects.filter(concept=concept_id)
    for component in components:
        # add this from latest version (concept_history_id, component_history_id)
        component.concept_history_id = Concept.objects.get(id=concept_id).history.latest().pk
        component.component_history_id = Component.objects.get(id=component.id).history.latest().pk
        
        component_error_msg_view[component.id] = []
        component_error_msg_edit[component.id] = []
        component_concpet_version_msg[component.id] = []
        
        if component.component_type == 1:
            user_can_view_components += [component.id]
            user_can_edit_components += [component.id]
            # if child concept, check if this version is published
            if check_published_child_concept:
                from ..permissions import checkIfPublished
                component.is_published = checkIfPublished(Concept, component.concept_ref_id, component.concept_ref_history_id)
            
            # Adding extra data here to indicate which group the component
            # belongs to (only for concepts).
            component_group_id = Concept.objects.get(id=component.concept_ref_id).group_id
            if component_group_id is not None:
                component.group = Group.objects.get(id=component_group_id).name
                            
            
            if Concept.objects.get(pk=component.concept_ref_id).is_deleted == True:
                component_error_msg_view[component.id] += ["concept deleted"]
                component_error_msg_edit[component.id] += ["concept deleted"]

            if not allowed_to_view(user, Concept, component.concept_ref.id, set_history_id=component.concept_ref_history_id):
                component_error_msg_view[component.id] += ["no view permission"]
                
            if not allowed_to_edit(user, Concept, component.concept_ref.id):
                component_error_msg_edit[component.id] += ["no edit permission"]
                
            # check component child version is the latest
            if component.concept_ref_history_id != Concept.objects.get(id=component.concept_ref_id).history.latest().pk:
                component_concpet_version_msg[component.id] += ["newer version available"]
                component_error_msg_view[component.id] += ["newer version available"]
               
            
        else:
            user_can_view_components += [component.id]
            user_can_edit_components += [component.id]

    # clean error msg
    for cid, value in component_error_msg_view.items():
        if value ==[]:
            component_error_msg_view.pop(cid, None)
        
    for cid, value in component_error_msg_edit.items():
        if value ==[]:
            component_error_msg_edit.pop(cid, None)
        
    for cid, value in component_concpet_version_msg.items():
        if value ==[]:
            component_concpet_version_msg.pop(cid, None)
                
    data = {'components': components,
            'user_can_view_component': user_can_view_components,
            'user_can_edit_component': user_can_edit_components,
            'component_error_msg_view': component_error_msg_view,
            'component_error_msg_edit': component_error_msg_edit,
            'component_concpet_version_msg': component_concpet_version_msg,
            'latest_history_id':  Concept.objects.get(id=concept_id).history.latest().pk
            }
    return data
