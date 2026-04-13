from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET

from clinicalcode.entity_utils import entity_db_utils, model_utils


@require_GET
def robots_txt(request):
    is_demo = settings.CLL_READ_ONLY or settings.IS_DEMO or settings.IS_DEVELOPMENT_PC
    if not settings.IS_PROD_SITE or is_demo:
        raise PermissionDenied

    response = cache.get('clgen_robots_response')
    if not isinstance(response, str):
        lines = [
            'User-Agent: *',
            'Allow: /',
        ]

        lines += ['Sitemap: ' + request.build_absolute_uri(reverse('concept_library_home')).replace('http://' , 'https://') + 'sitemap.xml']
        response = '\n'.join(lines)
        cache.set('clgen_robots_response', response, 60 * 60 * 8) # 8hrly cache

    return HttpResponse(response, content_type='text/plain')


@require_GET
def get_sitemap(request):
    is_demo = settings.CLL_READ_ONLY or settings.IS_DEMO or settings.IS_DEVELOPMENT_PC
    if not settings.IS_PROD_SITE or is_demo:
        raise PermissionDenied

    response = cache.get('clgen_sitemap_response')
    if not isinstance(response, str):
        cur_time = str(datetime.now().date())

        links = [
            # Base pages
            (request.build_absolute_uri(reverse('concept_library_home')), cur_time, '1.00'), 
            (request.build_absolute_uri(reverse('concept_library_home2')), cur_time, '1.00'),  
            (request.build_absolute_uri(reverse('search_entities')), cur_time, '1.00'),  
            (request.build_absolute_uri(reverse('reference_data')), cur_time, '1.00'),
            (request.build_absolute_uri(reverse('login')), cur_time, '1.00'),
            (request.build_absolute_uri(reverse('contact_us')), cur_time, '1.00'),
            # API pages
            (request.build_absolute_uri(reverse('api:root')), cur_time, '1.00'), 
            (request.build_absolute_uri(reverse('api:concepts')), cur_time, '1.00'), 
            (request.build_absolute_uri(reverse('api:get_generic_entities')), cur_time, '1.00'), 
            (request.build_absolute_uri(reverse('api:data_sources')), cur_time, '1.00'), 
            (request.build_absolute_uri(reverse('api:schema-swagger-ui')), cur_time, '0.80'), 
        ]

        # Dynamic, branded 'about' pages
        brand = model_utils.try_get_brand(request)
        branded_about_pages = brand.about_menu if brand is not None else None
        if isinstance(branded_about_pages, list):
            for item in branded_about_pages:
                if not isinstance(item, dict):
                    continue

                ref = item.get('page_name')
                if isinstance(ref, list):
                    for child in ref:
                        if not isinstance(child, dict):
                            continue
                        name = child.get('page_name')
                        if isinstance(name, str):
                            links.append(('%s/about/%s' % (settings.PROD_SITE_HOST, name), cur_time, '0.80'))
                elif isinstance(ref, str):
                    links.append(('%s/about/%s' % (settings.PROD_SITE_HOST, ref), cur_time, '0.80'))

        # Add links of published Concepts/Phenotypes
        links += get_published_phenotypes_and_concepts(request, cur_time)

        # Build final sitemap
        response = '''
                    <urlset
                        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
                                http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
                    '''
        for t in links:
            response += '''
                        <url>
                            <loc>''' + url_http_replace(t[0]) + '''</loc>
                            <lastmod>''' + t[1] + '''</lastmod>
                            <priority>''' + t[2] + '''</priority>        
                        </url>
                        '''

        response += '</urlset>'
        cache.set('clgen_sitemap_response', response, 60 * 60 * 8) # 8hrly cache

    return HttpResponse(response, content_type='application/xml')


def get_published_phenotypes_and_concepts(request, cur_time=None):
    """
        Add links of the published concepts/phenotypes to the sitemap
    """
    if not isinstance(cur_time, str) or len(cur_time) < 1:
        cur_time = str(datetime.now().date())

    links = []

    #--------------------------
    # published phenotypes
    published_phenotypes = entity_db_utils.get_visible_live_or_published_generic_entity_versions(
        request,
        get_live_and_or_published_ver= 2,  # 1= live only, 2= published only, 3= live+published
        exclude_deleted=True,
        filter_cond='',
        show_top_version_only=False,
    )

    published_phenotypes_ids = entity_db_utils.get_list_of_visible_entity_ids(published_phenotypes, return_id_or_history_id="id")
    for pk in published_phenotypes_ids:
        links +=[(request.build_absolute_uri(reverse('entity_detail', kwargs={'pk': pk})), cur_time, "0.80")]
        links +=[(request.build_absolute_uri(reverse('api:get_generic_entity_detail', kwargs={'phenotype_id': pk})), cur_time, "0.80")]

    #--------------------------    
    # published concepts 
    published_concepts_ids = entity_db_utils.get_concept_ids_from_phenotypes(published_phenotypes, return_id_or_history_id="id")
    for pk in published_concepts_ids:
        #links +=[(request.build_absolute_uri(reverse('concept_detail', kwargs={'pk': pk})), cur_time, "0.80")]
        links +=[(request.build_absolute_uri(reverse('api:api_concept_detail', kwargs={'concept_id': pk})), cur_time, "0.80")]

    return links


def url_http_replace(url1):
    url = url1
    if settings.IS_INSIDE_GATEWAY:
        url = url1.replace('https://' , 'http://')
    else:
        url = url1.replace('http://' , 'https://')

    return url
