"""
    ---------------------------------------------------------------------------
    COMMON VIEW CODE
    ---------------------------------------------------------------------------
"""
import logging
import sys

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import render

from ..forms.ContactUsForm import ContactForm
from ..models.Brand import Brand
from ..models.CodingSystem import CodingSystem
from ..models.DataSource import DataSource
from ..models.Statistics import Statistics
from ..models.Tag import Tag
from ..models.OntologyTag import OntologyTag
from ..entity_utils.constants import ONTOLOGY_TYPES
from ..entity_utils.permission_utils import redirect_readonly


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Brand / Homepages incl. about
# --------------------------------------------------------------------------
def get_brand_index_stats(request, brand):
    if Statistics.objects.all().filter(org__iexact=brand, type__iexact='landing-page').exists():
        stat = Statistics.objects.filter(org__iexact=brand, type__iexact='landing-page')
        if stat.exists():
            stat = stat.order_by('-modified').first()
        stats = stat.stat if stat else None
    else:
        from ..entity_utils.stats_utils import save_homepage_stats
        # update stat
        stat_obj = save_homepage_stats(request, brand)
        stats = stat_obj[0]
    return stats


def index(request):
    """
        Displays the index homepage.
        Assigns brand defined in the Django Admin Portal under "index_path".
        If brand is not available it will rely on the default index path.
    """
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
        'published_concept_count': stats.get('published_concept_count'),
        'published_phenotype_count': stats.get('published_phenotype_count'),
        'published_clinical_codes': stats.get('published_clinical_codes'),
        'datasources_component_count': stats.get('datasources_component_count'),
        'clinical_terminologies': stats.get('clinical_terminologies')
    })


def index_ADP(request, index_path):
    """
        Display the base page for ADP
    """
    return render(request, index_path)


def index_HDRUK(request, index_path):
    """
        Display the HDR UK homepage.
    """
    stats = get_brand_index_stats(request, 'HDRUK')

    return render(
        request,
        index_path,
        {
            # ONLY PUBLISHED COUNTS HERE
            'published_concept_count': stats.get('published_concept_count'),
            'published_phenotype_count': stats.get('published_phenotype_count'),
            'published_clinical_codes': stats.get('published_clinical_codes'),
            'datasources_component_count': stats.get('datasources_component_count'),
            'clinical_terminologies': stats.get('clinical_terminologies')
        })


def index_BREATHE(request, index_path):
    return render(
        request,
        index_path
    )


def brand_about_index_return(request, pg_name):
    """
        Renders the appropriate about page index based on the provided page name.

        Args:
            request: The HTTP request object.
            pg_name (str): The name of the requested about page.

        Returns:
            HttpResponse: The rendered template response.
    """
    brand = Brand.objects.filter(name__iexact=settings.CURRENT_BRAND)

    try:
        brand = brand.first()
        # Retrieve the 'about_menu' JSON from Django
        about_pages_dj_data = brand.about_menu

        # converts 'about_menu' django JSON into a dictionary with key as page_name and html index as value
        about_page_templates = {
            item['page_name'].lower(): item['index']
            for item in about_pages_dj_data if
            isinstance(item.get('index'), str) and isinstance(item.get('page_name'), str)
        }

        inner_templates = {
            group['page_name'].lower(): group['index']
            for item in about_pages_dj_data if isinstance(item.get('page_name'), list)
            for group in item.get('page_name') if
            isinstance(group.get('index'), str) and isinstance(group.get('page_name'), str)
        }

        # Get the index associated with current page name
        about_page_name = about_page_templates.get(pg_name.lower()) or inner_templates.get(pg_name.lower())
        if not about_page_name:
            raise Exception('No valid template found')
    except:
        raise Http404
    else:
        return render(request, about_page_name, {})


# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Misc. pages e.g. T&C, P&C, Technical pages, Contact us etc
# --------------------------------------------------------------------------
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
    return render(request, 'clinicalcode/brand/HDRUK/about/technical-details.html', {})


def cookies_settings(request):
    return render(request, 'cookielaw/en.html', {})

@redirect_readonly
def contact_us(request):
    """
        Generation of Contact us page/form and email send functionality.
    """

    if settings.CLL_READ_ONLY:
        raise PermissionDenied

    captcha = True
    if not settings.IGNORE_CAPTCHA:
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
                    "<strong>New Message from Concept Library Website</strong><br><br>" \
                    "<strong>Name:</strong><br>" \
                    "{name}" \
                    "<br><br>" \
                    "<strong>Email:</strong><br>" \
                    "{from_email}" \
                    "<br><br>" \
                    "<strong>Issue Type:</strong><br>" \
                    "{category}" \
                    "<br><br>" \
                    "<strong> Tell us about your Enquiry: </strong><br>" \
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
        {'form': form, 'message_sent': sent_status}
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
            proxies={'https': 'http://proxy:8080/'}
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
        'collections': list(collections),
        'ontology': OntologyTag.get_groups([x.value for x in ONTOLOGY_TYPES], default=[]),
    }

    return render(request, 'clinicalcode/about/reference_data.html', context)
