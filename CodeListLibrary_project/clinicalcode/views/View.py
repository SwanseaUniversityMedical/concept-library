"""
    ---------------------------------------------------------------------------
    COMMON VIEW CODE
    ---------------------------------------------------------------------------
"""
from django.conf import settings
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import render
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.core.cache import cache
from django.http.response import Http404
from django.core.exceptions import PermissionDenied

import sys
import logging
import requests

from ..forms.ContactUsForm import ContactForm

from ..models.Tag import Tag
from ..models.Brand import Brand
from ..models.CodingSystem import CodingSystem
from ..models.DataSource import DataSource
from ..models.Statistics import Statistics

from ..entity_utils import (
    gen_utils, template_utils,
    constants, model_utils, sanitise_utils
)

from ..entity_utils.constants import ONTOLOGY_TYPES
from ..entity_utils.permission_utils import redirect_readonly

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Brand / Homepages incl. about
# --------------------------------------------------------------------------
def get_brand_index_stats(request, brand_name='ALL'):
    """
      Attempts to resolve the index page statistics for the given Brand; defaults to `ALL`

      Args:
        request    (RequestContext): the HTTP request context
        brand_name            (str): the name of the brand to query

      Returns:
        A (dict) containing the statistics for the specified brand
    """
    cache_key = f'idx_stats__{brand_name}__cache'

    brand_stats = cache.get(cache_key)
    if brand_stats is None:
        brand_stats = Statistics.objects.filter(org__iexact=brand_name, type__iexact='landing-page')
        if brand_stats.exists():
            brand_stats = brand_stats.order_by('-modified').first().stat

        if not isinstance(brand_stats, dict):
            from ..entity_utils.stats_utils import save_homepage_stats
            brand_stats = save_homepage_stats(request, brand_name)
            brand_stats = brand_stats[0]

        cache.set(cache_key, brand_stats, 3600)

    return brand_stats


def index(request):
    """
        Displays the index homepage.
        Assigns brand defined in the Django Admin Portal under "index_path".
        If brand is not available it will rely on the default index path.
    """
    brand = request.BRAND_OBJECT
    index_path = settings.INDEX_PATH

    # if the index_ function doesn't exist for the current brand force render of the default index_path
    try:
        if not brand or not isinstance(brand, Brand):
            return index_home(request, index_path)
        return getattr(sys.modules[__name__], 'index_%s' % brand)(request, brand.index_path)
    except:
        return index_home(request, index_path)


def index_home(request, index_path):
    stats = get_brand_index_stats(request, 'ALL')

    brand_descriptors = cache.get('idx_brand__cache')
    if brand_descriptors is None:
        brand_descriptors = Brand.objects.all().all().values('name', 'description')
        cache.set('idx_brand__desc__cache', brand_descriptors, 3600)

    return render(request, index_path, {
        'known_brands': brand_descriptors,
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
    brand = request.BRAND_OBJECT
    try:
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
# Custom err / msg views
# --------------------------------------------------------------------------
def notify_err(request, title=None, status_code=None, details=None):
    if gen_utils.is_empty_string(title):
        title = None

    if not isinstance(status_code, int):
        status_code = 400

    if isinstance(details, list):
        for group in details:
            if isinstance(group, dict):
                try:
                    messages.add_message(request, **group)
                except Exception as e:
                    logger.warning(f'Failed to pass message to FmtError<title: {title}, status_code: {status_code} view with err: {str(e)}')
            elif group is not None:
                messages.add_message(request, messages.INFO, str(group))

    return render(
        status=status_code,
        request=request,
        context={ 'errheader': { 'title': title, 'status_code': status_code } },
        content_type='text/html',
        template_name='fmt-error.html'
    )

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

    if settings.CLL_READ_ONLY or settings.IS_GATEWAY_PC:
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

            brand_title = model_utils.try_get_brand_string(request.BRAND_OBJECT, 'site_title', default='Concept Library')
            email_subject = '%s - New Message From %s' % (brand_title, name)

            try:
                html_content = \
                    '<strong>New Message from {site} Website</strong><br><br>' \
                    '<strong>Name:</strong><br>' \
                    '{name}' \
                    '<br><br>' \
                    '<strong>Email:</strong><br>' \
                    '{from_email}' \
                    '<br><br>' \
                    '<strong>Issue Type:</strong><br>' \
                    '{category}' \
                    '<br><br>' \
                    '<strong> Tell us about your Enquiry: </strong><br>' \
                    '{message}'.format(
                        site=brand_title,
                        name=name,
                        from_email=from_email,
                        category=category,
                        message=sanitise_utils.sanitise_value(message, default='[Sanitisation failure]')
                    )

                if not settings.IS_DEVELOPMENT_PC or settings.HAS_MAILHOG_SERVICE:
                    message = EmailMultiAlternatives(
                        email_subject,
                        html_content,
                        'Helpdesk <%s>' % settings.DEFAULT_FROM_EMAIL,
                        to=[settings.HELPDESK_EMAIL],
                        cc=[from_email]
                    )
                    message.content_subtype = 'html'
                    message.send()

                form = ContactForm()
                sent_status = True
            except BadHeaderError:
                return HttpResponse('Invalid header found')
            except Exception as e:
                logger.error('Failed to process ContactUsForm<src: %s> with error: %s' % (str(from_email), str(e), ))

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
    tags = template_utils.get_template_sourced_values(constants.metadata, 'tags', request=request, default=[])
    collections = template_utils.get_template_sourced_values(constants.metadata, 'collections', request=request, default=[])

    context = {
        'data_sources': list(DataSource.objects.all().order_by('id').values('id', 'name')),
        'coding_system': list(CodingSystem.objects.all().order_by('id').values('id', 'name')),
        'tags': tags,
        'collections': collections,
        'ontology_groups': [x.value for x in ONTOLOGY_TYPES]
    }

    return render(request, 'clinicalcode/about/reference_data.html', context)
