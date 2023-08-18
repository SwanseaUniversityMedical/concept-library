'''
    ---------------------------------------------------------------------------
    COMMON VIEW CODE
    ---------------------------------------------------------------------------
'''
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http.response import Http404
from django.shortcuts import redirect, render
from django import forms
from django.conf import settings
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.http import HttpResponse
from django.db.models.functions import Lower

import requests
import sys
import datetime
import json
import logging

from ..models import *
from clinicalcode import db_utils
from ..forms.ContactUsForm import ContactForm
from ..permissions import allowed_to_edit, allowed_to_view


logger = logging.getLogger(__name__)

def get_brand_index_stats(request, brand):
    if Statistics.objects.all().filter(org__iexact=brand, type__iexact='landing-page').exists():
        stat = Statistics.objects.get(org__iexact=brand, type__iexact='landing-page')
        stats = stat.stat
    else:
        from ..entity_utils.stats_utils import save_homepage_stats
        # update stat
        stat_obj = save_homepage_stats(request, brand)
        stats = stat_obj[0]
    return stats

def index(request):
    '''
        Displays the index homepage.
        Assigns brand defined in the Django Admin Portal under "index_path". 
        If brand is not available it will rely on the default index path.
    '''
    index_path = settings.INDEX_PATH
    brand = Brand.objects.filter(name__iexact=settings.CURRENT_BRAND)

    # if the index_ function doesn't exist for the current brand force render of the default index_path
    try:
        if not brand.exists():
            return index_home(request, index_path)
        brand = brand.first()
        return getattr(sys.modules[__name__], "index_%s" % brand)(request, brand.index_path)
    except:
        return index_home(request, index_path)

def index_home(request, index_path):
    stats = get_brand_index_stats(request, 'ALL')
    brands = Brand.objects.all().values('name', 'description')

    return render(request, index_path, {
        'known_brands': brands,
        'published_concept_count': stats['published_concept_count'],
        'published_phenotype_count': stats['published_phenotype_count'],
        'published_clinical_codes': stats['published_clinical_codes'],
        'datasources_component_count': stats['datasources_component_count'],
        'clinical_terminologies': stats['clinical_terminologies']
    })

def index_ADP(request, index_path):
    '''
        Display the base page for ADP
    '''
    return render(request, index_path)

def index_HDRUK(request, index_path):
    '''
        Display the HDR UK homepage.
    '''
    stats = get_brand_index_stats(request, 'HDRUK')

    return render(
        request,
        index_path,
        {
            # ONLY PUBLISHED COUNTS HERE
            'published_concept_count': stats['published_concept_count'],
            'published_phenotype_count': stats['published_phenotype_count'],
            'published_clinical_codes': stats['published_clinical_codes'],
            'datasources_component_count': stats['datasources_component_count'],
            'clinical_terminologies': stats['clinical_terminologies']
        })

def index_BREATHE(request, index_path):
    return render(
        request,
        index_path
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

        elif pg_name.lower() == "eurolinkcat".lower():
            return render(request, 'clinicalcode/brand/HDRUK/collections/eurolinkcat.html', {})
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

    sent_status = None
    if request.method == 'GET':
        form = ContactForm()
    else:
        form = ContactForm(request.POST)
        if form.is_valid() and captcha is True:
            name = form.cleaned_data['name']
            from_email = form.cleaned_data['from_email']
            message = form.cleaned_data['message']
            category = form.cleaned_data['categories']
            email_subject = 'Concept Library - New Message From %s' % name

            try:
                html_content = \
                    "<strong>New Message from Concept Library Website</strong><br><br>"\
                    "<strong>Name:</strong><br>"\
                    "{name}"\
                    "<br><br>"\
                    "<strong>Email:</strong><br>"\
                    "{from_email}"\
                    "<br><br>"\
                    "<strong>Issue Type:</strong><br>"\
                    "{category}"\
                    "<br><br>"\
                    "<strong> Tell us about your Enquiry: </strong><br>"\
                    "{message}".format(
                        name=name, from_email=from_email, category=category, message=message
                    )
                
                if not settings.IS_DEVELOPMENT_PC:
                    message = EmailMultiAlternatives(
                        email_subject,
                        html_content,
                        'Helpdesk <%s>' % settings.DEFAULT_FROM_EMAIL,
                        to=[settings.HELPDESK_EMAIL],
                        cc=[from_email]
                    )
                    message.content_subtype = "html"
                    message.send()

                form = ContactForm()
                sent_status = True
            except BadHeaderError:
                return HttpResponse('Invalid header found')

    sent_status = captcha

    return render(
        request, 
        'cl-docs/contact-us.html', 
        { 'form': form, 'message_sent': sent_status }
    )

def check_recaptcha(request):
    '''
        Contact Us Recaptcha code
    '''
    if settings.IS_DEVELOPMENT_PC:
        return True

    if settings.CLL_READ_ONLY:
        raise PermissionDenied
    
    if request.method == 'POST':
        data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': request.POST.get('g-recaptcha-response')
        }
        result = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            proxies={ 'https': 'http://proxy:8080/' }
        ).json()

        if result['success']:
            return True
        
        return False


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
