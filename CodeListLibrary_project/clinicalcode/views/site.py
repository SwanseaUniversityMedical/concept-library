from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from django.urls import reverse
#import xml.etree.ElementTree as ET
from .. import db_utils
from datetime import datetime

cur_time = str(datetime.now().date())


@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Allow: /",
    ]
    
    # sitemap 
    # site = "https://conceptlibrary.saildatabank.com"
    # if settings.IS_HDRUK_EXT == "1":
    #     site = "https://phenotypes.healthdatagateway.org"
    #
    # lines += ["Sitemap22: " + site + "/sitemap.xml"]

    lines += ["Sitemap: " + request.build_absolute_uri(reverse('concept_library_home')).replace('http://' , 'https://') + "sitemap.xml"]


    return HttpResponse("\n".join(lines), content_type="text/plain")

@require_GET
def get_sitemap(request):

    links = [
        (request.build_absolute_uri(reverse('concept_library_home')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('concept_library_home2')), cur_time, "1.00"),  
        (request.build_absolute_uri(reverse('concept_list')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('phenotype_list')), cur_time, "1.00"),  
        (request.build_absolute_uri(reverse('reference_data')), cur_time, "1.00"),
        (request.build_absolute_uri(reverse('login')), cur_time, "1.00"),
    ]
    
    
    # About pages
    # brand/main about pages
    if settings.IS_HDRUK_EXT == "1" or settings.IS_DEVELOPMENT_PC:
        links += [
            ('https://phenotypes.healthdatagateway.org/about/hdruk_about_the_project/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/hdruk_about_team/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/hdruk_about_technical_details/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/hdruk_about_covid_19_response/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/hdruk_about_publications/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/breathe/', cur_time, "0.80"),
            ('https://phenotypes.healthdatagateway.org/about/bhf_data_science_centre/', cur_time, "0.80"),
        ]
    
    # # privacy /terms /cookies
    # links += [
    #     (request.build_absolute_uri(reverse('cookies_settings')), cur_time, "0.40"),      
    #     (request.build_absolute_uri(reverse('terms')), cur_time, "0.40"), 
    #     (request.build_absolute_uri(reverse('privacy_and_cookie_policy')), cur_time, "0.40"),
    #     (request.build_absolute_uri(reverse('technical_documentation')), cur_time, "0.40"),
    # ]

    # contact us page
    links += [
        (request.build_absolute_uri(reverse('contact_us')), cur_time, "1.00"), 
    ]
    
    # API
    links += [
        (request.build_absolute_uri(reverse('api:root')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('api:api_published_concepts')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('api:api_published_phenotypes')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('api:data_sources_public')), cur_time, "1.00"), 
        (request.build_absolute_uri(reverse('api:schema-swagger-ui')), cur_time, "0.80"), 
    ]

    # add links of published concepts/phenotypes
    if settings.CURRENT_BRAND != "":
        links += get_published_phenotypes_and_concepts(request)
    
    links_str = """
                <urlset
                      xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
                            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
                """
    for t in links:
        links_str += """
                    <url>
                        <loc>""" + t[0].replace('http://' , 'https://') + """"</loc>
                        <lastmod>""" + t[1] + """</lastmod>
                        <priority>""" + t[2] + """</priority>        
                    </url>
                    """
        
    links_str += "</urlset>"

    
    return HttpResponse(links_str, content_type="application/xml")



def get_published_phenotypes_and_concepts(request):
    """
        add links of the published concepts/phenotypes to the sitemap
    """
    
    links = []
    
    # published concepts
    
    published_concepts = db_utils.get_visible_live_or_published_concept_versions(request,
                                                                                get_live_and_or_published_ver= 2,  # 1= live only, 2= published only, 3= live+published 
                                                                                exclude_deleted=True,
                                                                                show_top_version_only=False,
                                                                                )

    published_concepts_ids = db_utils.get_list_of_visible_entity_ids(published_concepts, return_id_or_history_id="id")
    for pk in published_concepts_ids:
        links +=[(request.build_absolute_uri(reverse('api:api_concept_detail_public', kwargs={'pk': pk})), cur_time, "0.80")]


    #--------------------------
    # published phenotypes
    
    published_phenotypes = db_utils.get_visible_live_or_published_phenotype_versions(request,
                                                                                    get_live_and_or_published_ver= 2,  # 1= live only, 2= published only, 3= live+published
                                                                                    exclude_deleted=True,
                                                                                    show_top_version_only=False,
                                                                                    )


    published_phenotypes_ids = db_utils.get_list_of_visible_entity_ids(published_phenotypes, return_id_or_history_id="id")
    for pk in published_phenotypes_ids:
        links +=[(request.build_absolute_uri(reverse('api:api_phenotype_detail_public', kwargs={'pk': pk})), cur_time, "0.80")]

    return links


