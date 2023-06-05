'''
    ---------------------------------------------------------------------------
    COMMON VIEW CODE
    ---------------------------------------------------------------------------
'''
import datetime
import json
import logging

from clinicalcode import db_utils
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http.response import Http404
from django.shortcuts import redirect, render

from ..models import *

from ..forms.ContactUsForm import ContactForm
from ..permissions import allowed_to_edit, allowed_to_view

import requests
from django import forms
from django.conf import settings
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.http import HttpResponse
from django.db.models.functions import Lower

logger = logging.getLogger(__name__)


def index(request):
    '''
        Display the index homepage.
    '''

    if request.CURRENT_BRAND == "":
        return render(request, 'clinicalcode/index.html')
    elif request.CURRENT_BRAND == "BREATHE":
        return index_BREATHE(request)
    elif request.CURRENT_BRAND == "HDRUK":
        return index_HDRUK(request)
    else:
        return render(request, 'clinicalcode/index.html')


def index_HDRUK(request):
    '''
        Display the HDR UK homepage.
    '''

    from .Admin import save_statistics

    if Statistics.objects.all().filter(org__iexact='HDRUK', type__iexact='landing-page').exists():
        stat = Statistics.objects.get(org__iexact='HDRUK', type__iexact='landing-page')
        HDRUK_stat = stat.stat

    else:
        # update stat
        stat_obj = save_statistics(request)
        HDRUK_stat = stat_obj[0]

    return render(
        request,
        'clinicalcode/brand/HDRUK/index_HDRUK.html',
        {
            # ONLY PUBLISHED COUNTS HERE
            'published_concept_count': HDRUK_stat['published_concept_count'],
            'published_phenotype_count': HDRUK_stat['published_phenotype_count'],
            'published_clinical_codes': HDRUK_stat['published_clinical_codes'],
            'datasources_component_count': HDRUK_stat['datasources_component_count'],
            'clinical_terminologies': HDRUK_stat['clinical_terminologies']
        })


def index_BREATHE(request):
    return render(
        request,
        'clinicalcode/brand/BREATHE/index_BREATHE.html',
    )


def about_pages(request, pg_name=None):
    '''
        manage about pages
    '''

    # main CL about page
    if pg_name.lower() == "cl_about_page".lower():
        return render(request, 'clinicalcode/index.html', {})

    #     elif pg_name.lower() == "cl_terms".lower():
#         return render(request, 'cl-docs/terms-conditions.html', {})

# HDR-UK about pages
    if request.CURRENT_BRAND == "HDRUK":
        if pg_name.lower() == "hdruk_about_the_project".lower():
            return render(request, 'clinicalcode/brand/HDRUK/about/about-the-project.html', {})

        elif pg_name.lower() == "hdruk_about_team".lower():
            return render(request, 'clinicalcode/brand/HDRUK/about/team.html', {})

        elif pg_name.lower() == "hdruk_about_technical_details".lower():
            return technicalpage(request)

        elif pg_name.lower() == "hdruk_about_covid_19_response".lower():
            return render(request, 'clinicalcode/brand/HDRUK/about/covid-19-response.html', {})

        elif pg_name.lower() == "hdruk_about_publications".lower():
            return render(request, 'clinicalcode/brand/HDRUK/about/publications.html', {})

#         elif pg_name.lower() == "hdruk_terms".lower():
#             return render(request, 'cl-docs/terms-conditions.html', {})

        elif pg_name.lower() == "breathe".lower():
            return render(request, 'clinicalcode/brand/HDRUK/collections/breathe.html', {})

        elif pg_name.lower() == "bhf_data_science_centre".lower():
            return render(request, 'clinicalcode/brand/HDRUK/collections/bhf-data-science-centre.html', {})

#     else:
#         return render(request, 'clinicalcode/index.html', {})

    raise Http404


def HDRUK_portal_redirect(request, unique_url):
    '''
        HDR-UK portal redirect to CL
    '''

    if unique_url is not None:
        phenotype = list(
            Phenotype.objects.filter(
                Q(source_reference__iendswith=("/" + unique_url + ".md"))
                | Q(source_reference__iendswith=("/" + unique_url))).values_list('id', flat=True))
        if phenotype:
            versions = Phenotype.objects.get(pk=phenotype[0]).history.all().order_by('-history_id')
            for v in versions:
                is_this_version_published = False
                is_this_version_published = db_utils.checkIfPublished(Phenotype, v.id, v.history_id)
                if is_this_version_published:
                    return redirect('phenotype_history_detail',
                                    pk=v.id,
                                    phenotype_history_id=v.history_id)

            raise Http404
        else:
            raise Http404
    else:
        raise Http404


def build_permitted_components_list(request,
                                    concept_id,
                                    concept_history_id=None,
                                    check_published_child_concept=False):
    '''
        Look through the components that are associated with the specified
        concept ID and decide whether each has view and edit permission for
        the specified user.
    '''
    user = request.user
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

            if not allowed_to_view(request, Concept, component.concept_ref.id, set_history_id=component.concept_ref_history_id):
                component_error_msg_view[component.id] += ["no view permission"]

            if not allowed_to_edit(request, Concept, component.concept_ref.id):
                component_error_msg_edit[component.id] += ["no edit permission"]

            # check component child version is the latest
            if component.concept_ref_history_id != Concept.objects.get(id=component.concept_ref_id).history.latest().pk:
                component_concpet_version_msg[component.id] += ["newer version available"]
                component_error_msg_view[component.id] += ["newer version available"]

        else:
            user_can_view_components += [component.id]
            user_can_edit_components += [component.id]

    # clean error msg
    for cid, value in list(component_error_msg_view.items()):
        if value == []:
            component_error_msg_view.pop(cid, None)

    for cid, value in list(component_error_msg_edit.items()):
        if value == []:
            component_error_msg_edit.pop(cid, None)

    for cid, value in list(component_concpet_version_msg.items()):
        if value == []:
            component_concpet_version_msg.pop(cid, None)

    data = {
            'components': components,
            'user_can_view_component': user_can_view_components,
            'user_can_edit_component': user_can_edit_components,
            'component_error_msg_view': component_error_msg_view,
            'component_error_msg_edit': component_error_msg_edit,
            'component_concpet_version_msg': component_concpet_version_msg,
            'latest_history_id': Concept.objects.get(id=concept_id).history.latest().pk
    }
    return data


#--------------------------------------------------------------------------


# No authentication for this function
def customRoot(request):
    '''
        Custom API Root page.
        Replace pk=0 (i.e.'/0/' in the url) with the relevant id.
        Replace history=0 (i.e.'/0/' in the url) with the relevant version_id.
    '''
    from django.shortcuts import render
    from rest_framework.reverse import reverse
    from rest_framework.views import APIView

    #api_absolute_ip = str(request.build_absolute_uri(reverse('api:api_export_concept_codes', kwargs={'pk': 0}))).split('/')[2]

    urls_available = {
        'export_concept_codes': reverse('api:api_export_concept_codes', kwargs={'pk': 0}),
        'export_concept_codes_byVersionID': reverse('api:api_export_concept_codes_byVersionID', kwargs={'pk': 0, 'concept_history_id': 123}),
        'api_export_published_concept_codes_latestVersion': reverse('api:api_export_published_concept_codes_latestVersion', kwargs={'pk': 0}),
        'api_export_published_concept_codes': reverse('api:api_export_published_concept_codes', kwargs={'pk': 0, 'concept_history_id': 123}),
        'concepts': reverse('api:concepts', kwargs={}),
        'api_concept_detail': reverse('api:api_concept_detail', kwargs={'pk': 0}),
        'api_concept_detail_version': reverse('api:api_concept_detail_version', kwargs={'pk': 0, 'concept_history_id': 123}),
        'api_published_concepts': reverse('api:api_published_concepts', kwargs={}),
        'api_concept_detail_public': reverse('api:api_concept_detail_public', kwargs={'pk': 0}),
        'api_concept_detail_version_public': reverse('api:api_concept_detail_version_public', kwargs={'pk': 0, 'concept_history_id': 123}),
        'get_concept_versions': reverse('api:get_concept_versions', kwargs={'pk': 0}),
        'get_concept_versions_public': reverse('api:get_concept_versions_public', kwargs={'pk': 0}),
        'concept_by_id': reverse('api:concept_by_id', kwargs={'pk': 0}),
        'api_published_concept_by_id': reverse('api:api_published_concept_by_id', kwargs={'pk': 0}),
        'export_workingset_codes': reverse('api:api_export_workingset_codes', kwargs={'pk': 0}),
        'export_workingset_codes_byVersionID': reverse('api:api_export_workingset_codes_byVersionID', kwargs={'pk': 0, 'workingset_history_id': 123}),
        'workingsets': reverse('api:workingsets', kwargs={}),
        'api_workingset_detail': reverse('api:api_workingset_detail', kwargs={'pk': 0}),
        'api_workingset_detail_version': reverse('api:api_workingset_detail_version', kwargs={'pk': 0, 'workingset_history_id': 123}),
        'get_workingset_versions': reverse('api:get_workingset_versions', kwargs={'pk': 0}),
        'workingset_by_id': reverse('api:workingset_by_id', kwargs={'pk': 0}),

        # not implemented yet, will be done when creating/updating phenotype
        #'export_phenotype_codes': reverse('api:api_export_phenotype_codes', kwargs={'pk': 'PH0'}),
        'api_export_phenotype_codes_byVersionID': reverse('api:api_export_phenotype_codes_byVersionID', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'phenotypes': reverse('api:phenotypes', kwargs={}),
        'api_phenotype_detail': reverse('api:api_phenotype_detail', kwargs={'pk': 'PH0'}),
        'api_phenotype_detail_version': reverse('api:api_phenotype_detail_version', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'api_published_phenotypes': reverse('api:api_published_phenotypes', kwargs={}),
        # not needed to be public
        #'api_phenotype_detail_public': reverse('api:api_phenotype_detail_public', kwargs={'pk': 'PH0'}),
        'api_phenotype_detail_version_public': reverse('api:api_phenotype_detail_version_public', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'api_export_published_phenotype_codes_latestVersion': reverse('api:api_export_published_phenotype_codes_latestVersion', kwargs={'pk': 'PH0'}),
        'api_export_published_phenotype_codes': reverse('api:api_export_published_phenotype_codes', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'get_phenotype_versions': reverse('api:get_phenotype_versions', kwargs={'pk': 'PH0'}),
        'get_phenotype_versions_public': reverse('api:get_phenotype_versions_public', kwargs={'pk': 'PH0'}),
        'phenotype_by_id': reverse('api:phenotype_by_id', kwargs={'pk': 'PH0'}),
        'api_published_phenotype_by_id': reverse('api:api_published_phenotype_by_id', kwargs={'pk': 'PH0'}),
        'api_phenotype_detail_public': reverse('api:api_phenotype_detail_public', kwargs={'pk': 'PH0'}),
        'api_phenotype_detail_version': reverse('api:api_phenotype_detail_version', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'api_phenotype_detail_version_public': reverse('api:api_phenotype_detail_version_public', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'api_export_phenotype_codes_byVersionID': reverse('api:api_export_phenotype_codes_byVersionID', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
        'api_export_phenotype_codes_latestVersion': reverse('api:api_export_phenotype_codes_latestVersion', kwargs={'pk': 'PH0'}),
        'api_export_published_phenotype_codes': reverse('api:api_export_published_phenotype_codes', kwargs={'pk': 'PH0', 'phenotype_history_id': 123}),
                
        'get_phenotype_versions': reverse('api:get_phenotype_versions', kwargs={'pk': 'PH0'}),
        'get_phenotype_versions_public':  reverse('api:get_phenotype_versions_public', kwargs={'pk': 'PH0'}),
        'tags':  reverse('api:tag_list_public'),
        'collections':  reverse('api:collection_list_public'),
        'datasource-list':  reverse('api:datasource-list'),
    }
    
    if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
        urls_available.update({
            'phenotypeworkingset_by_id': reverse('api:api_phenotypeworkingset_by_id', kwargs={'pk': 'WS0'}),
            'api_phenotypeworkingset_detail': reverse('api:api_phenotypeworkingset_detail', kwargs={'pk': 'WS0'}),
            'api_phenotypeworkingset_detail_version': reverse('api:api_phenotypeworkingset_detail_version', kwargs={'pk': 'WS0', 'workingset_history_id': 123}),
            'get_phenotypeworkingset_versions': reverse('api:get_phenotypeworkingset_versions', kwargs={'pk': 'WS0'}),
            'api_export_phenotypeworkingset_codes_latestVersion': reverse('api:api_export_phenotypeworkingset_codes_latestVersion', kwargs={'pk': 'WS0'}),
            'api_export_phenotypeworkingset_codes_byVersionID': reverse('api:api_export_phenotypeworkingset_codes_byVersionID', kwargs={'pk': 'WS0', 'workingset_history_id': 123}),
            'api_export_published_phenotypeworkingset_codes_latestVersion': reverse('api:api_export_published_phenotypeworkingset_codes_latestVersion', kwargs={'pk': 'WS0'}),
            'api_export_published_phenotypeworkingset_codes': reverse('api:api_export_published_phenotypeworkingset_codes', kwargs={'pk': 'WS0', 'workingset_history_id': 123}),
        })

    if not settings.CLL_READ_ONLY:
        urls_available.update({
            'api_concept_create':       reverse('api:api_concept_create', kwargs={}),
            'api_concept_update':       reverse('api:api_concept_update', kwargs={}),
            'api_workingset_create':    reverse('api:api_workingset_create', kwargs={}),
            'api_workingset_update':    reverse('api:api_workingset_update', kwargs={}),
            'api_phenotype_create':     reverse('api:api_phenotype_create', kwargs={}),
            'api_phenotype_update':     reverse('api:api_phenotype_update', kwargs={}),
            'api_datasource_create':    reverse('api:api_datasource_create', kwargs={})
        })

    # replace 0/123 by {id}/{version_id}
    for k, v in list(urls_available.items()):
        new_url = urls_available[k].replace('C0', '{id}').replace('PH0', '{id}').replace('WS0', '{id}').replace('123', '{version_id}')
        urls_available[k] = new_url

    return render(request, 'rest_framework/API-root-pg.html', urls_available)


def termspage(request):
    """
        terms and conditions page
    """
    return render(request, 'cl-docs/terms-conditions.html', {})


def cookiespage(request):
    """
        privacy and cookie policy page
    """
    return render(request, 'cl-docs/privacy-cookie-policy.html', {})


def technicalpage(request):
    """
        HDRUK Documentation outside of HDRUK Brand

    """

    phenotype_bronheostasis = db_utils.get_visible_live_or_published_phenotype_versions(request,show_top_version_only = True,
                                                                                           filter_cond="(phenotype_uuid='ZckoXfUWNXn8Jn7fdLQuxj')")
    bron_id = phenotype_bronheostasis[0]['id']
    bron_version = phenotype_bronheostasis[0]['history_id']



    return render(request, 'clinicalcode/brand/HDRUK/about/technical-details.html', {'bron_id':bron_id,'bron_version':bron_version})


def cookies_settings(request):
    return render(request, 'cookielaw/en.html', {})


def contact_us(request):
    """
        Generation of Contact us page/form and email send functionality.
    """
    
    if settings.CLL_READ_ONLY:
        raise PermissionDenied
    
    captcha = check_recaptcha(request)
    status = []
    if request.method == 'GET':
        form = ContactForm()
    else:
        form = ContactForm(request.POST)
        if form.is_valid() and captcha is True:
            name = form.cleaned_data['name']
            from_email = form.cleaned_data['from_email']
            message = form.cleaned_data['message']
            category = form.cleaned_data['categories']
            email_subject = ('Concept Library - New Message From ' + name)

            try:
                html_content = ('<strong>New Message from Concept Library Website</strong> <br><br> <strong>Name:</strong><br>' 
                                + name 
                                + '<br><br> <strong>Email:</strong><br>' 
                                + from_email 
                                + '<br><br> <strong>Issue Type:</strong><br>' 
                                + category 
                                + '<br><br><strong> Tell us about your Enquiry: </strong><br>' 
                                + message)
                
                msg = EmailMultiAlternatives(email_subject,
                                             html_content,
                                             'Helpdesk <%s>' %
                                             settings.DEFAULT_FROM_EMAIL,
                                             to=[settings.HELPDESK_EMAIL],
                                             cc=[from_email])
                msg.content_subtype = "html"  # Main content is now text/html
                msg.send()

                form = ContactForm()
                status.append({'SUCCESS': 'Issue Reported Successfully.'})
            except BadHeaderError:
                return HttpResponse('Invalid header found.')

        if captcha == False:
            status.append({'FAIL': 'Please verify using the Captcha'})

    return render(request, 
                  'cl-docs/contact-us.html', 
                  {
                    'form': form,
                    'message': status,
                  }
                )

def check_recaptcha(request):
    '''
        Contact Us Recaptcha code
    '''
    if settings.CLL_READ_ONLY:
        raise PermissionDenied
    
    if request.method == 'POST':
        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        r = requests.post(
                            'https://www.google.com/recaptcha/api/siteverify',
                            data=data,
                            proxies={'https': 'http://proxy:8080/'}
                        )
        result = r.json()
        if result['success']:
            recaptcha_is_valid = True
        else:
            recaptcha_is_valid = False
        return recaptcha_is_valid


def reference_data(request):
    """
        Open page to list Data sources, Coding systems, Tags, Collections, Phenotype types, etc 
    """

    tags = Tag.objects.extra(select={
        'name': 'description'
    }).order_by('id')
    collections = tags.filter(tag_type=2).values('id', 'name')
    tags = tags.filter(tag_type=1).values('id', 'name')

    context = {
        'data_sources': list(DataSource.objects.all().order_by('id').values('id', 'name')),
        'coding_system': list(CodingSystem.objects.all().order_by('id').values('id', 'name')),
        'tags': list(tags),
        'collections': list(collections)
    }
    
    return render(request, 'clinicalcode/about/reference_data.html', context)
