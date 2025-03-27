'''
    URL Configuration for the Clinical-Code application.

    Pages appear as Working-sets, Concepts and Components within a Concept.
'''

from django.conf import settings
from django.urls import re_path as url
from django.views.generic.base import RedirectView

from clinicalcode.views.dashboard import BrandAdmin
from clinicalcode.views.DocumentationViewer import DocumentationViewer
from clinicalcode.views import (
    site, View, Admin, adminTemp, GenericEntity,
    Publish, Decline, Moderation, Profile, Organisation
)

from clinicalcode.views.dashboard.targets import TemplateTarget, TagTarget

# Main
urlpatterns = [
    # Base
    ## Home
    url(r'^$', View.index, name='concept_library_home'),
    url(r'^$', GenericEntity.EntitySearchView.as_view(), name='concept_library_home'),
    url(r'^home/$', GenericEntity.EntitySearchView.as_view(), name='concept_library_home2'),

    ## Terms & Conditions and Privacy policy
    url(r'^terms-and-conditions/$', View.termspage, name='terms'),
    url(r'^privacy-and-cookie-policy/$', View.cookiespage, name='privacy_and_cookie_policy'),

    ## Technical
    url(r'^reference-data/$', View.reference_data, name='reference_data'),
    url(r'^technical_documentation/$', View.technicalpage, name='technical_documentation'),

    ## Cookies
    url(r'^cookies-settings/$', View.cookies_settings, name='cookies_settings'),
    
    ## About pages
    url(r'^about/(?P<pg_name>([A-Za-z0-9\-\_]+))/$', View.brand_about_index_return, name='about_page'),

    ## Moderation
    url(r'^moderation/$', Moderation.EntityModeration.as_view(), name='moderation_page'),

    ## Contact
    url(r'^contact-us/$', View.contact_us, name='contact_us'),

    # User
    ## Profile
    url(r'^profile/$', Profile.MyCollection.as_view(), name='my_profile'),
    url(r'^profile/collection/$', Profile.MyCollection.as_view(), name='my_collection'),

    ## Organisation
    url(r'^org/view/(?P<slug>([\w\d\-\_]+))/?$', Organisation.OrganisationView.as_view(), name='view_organisation'),
    url(r'^org/create/?$', Organisation.OrganisationCreateView.as_view(), name='create_organisation'),
    url(r'^org/manage/(?P<slug>([\w\d\-\_]+))/?$', Organisation.OrganisationManageView.as_view(), name='manage_organisation'),

    # Brand
    ## Brand Administration
    ### Endpoints: dashboard view controllers
    url(r'^dashboard/$', BrandAdmin.BrandDashboardView.as_view(), name=BrandAdmin.BrandDashboardView.reverse_name),
    url(r'^dashboard/brand/$', BrandAdmin.BrandConfigurationView.as_view(), name=BrandAdmin.BrandConfigurationView.reverse_name),
    url(r'^dashboard/people/$', BrandAdmin.BrandPeopleView.as_view(), name=BrandAdmin.BrandPeopleView.reverse_name),
    url(r'^dashboard/inventory/$', BrandAdmin.BrandInventoryView.as_view(), name=BrandAdmin.BrandInventoryView.reverse_name),
    url(r'^dashboard/stats-summary/$', BrandAdmin.BrandStatsSummaryView.as_view(), name=BrandAdmin.BrandStatsSummaryView.reverse_name),
    ### Endpoints: dashboard model administration
    url(r'^dashboard/target/template/$', TemplateTarget.TemplateEndpoint.as_view(), name=TemplateTarget.TemplateEndpoint.reverse_name_default),
    url(r'^dashboard/target/template/(?P<pk>\w+)/$', TemplateTarget.TemplateEndpoint.as_view(), name=TemplateTarget.TemplateEndpoint.reverse_name_retrieve),
    url(r'^dashboard/target/tag/$', TagTarget.TagEndpoint.as_view(), name=TagTarget.TagEndpoint.reverse_name_default),
    url(r'^dashboard/target/tag/(?P<pk>\w+)/$', TagTarget.TagEndpoint.as_view(), name=TagTarget.TagEndpoint.reverse_name_retrieve),
    # GenericEnities (Phenotypes)
    ## Search
    url(r'^phenotypes/$', GenericEntity.EntitySearchView.as_view(), name='search_phenotypes'),
    # url(r'^phenotypes/(?P<entity_type>([A-Za-z0-9\-]+))/?$', GenericEntity.EntitySearchView.as_view(), name='search_phenotypes'),
    
    ## Detail
    url(r'^phenotypes/(?P<pk>\w+)/$', RedirectView.as_view(pattern_name='entity_detail'), name='entity_detail_shortcut'),
    url(r'^phenotypes/(?P<pk>\w+)/detail/$', GenericEntity.generic_entity_detail, name='entity_detail'),
    url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$', GenericEntity.generic_entity_detail, name='entity_history_detail'),

    url(r'^phenotypes/(?P<pk>\w+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_latest_version_codes_to_csv'),
    url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_version_codes_to_csv'),   

    ## Selection service(s)
    url(r'^query/(?P<template_id>\w+)/?$', GenericEntity.EntityDescendantSelection.as_view(), name='entity_descendants'),

    ## Support legacy Concept redirects
    url(r'^concepts/C(?P<pk>\d+)/detail/$', GenericEntity.RedirectConceptView.as_view(), name='redirect_concept_detail'),
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<history_id>\d+)/detail/$', GenericEntity.RedirectConceptView.as_view(), name='redirect_concept_detail_with_version'),

    ## Documentation for create
    url(r'^documentation/(?P<documentation>([A-Za-z0-9\-]+))/?$', DocumentationViewer.as_view(), name='documentation_viewer'),

    # GenericEnities (Phenotypes)
    ## Create / Update
    url(r'^create/$', GenericEntity.CreateEntityView.as_view(), name='create_phenotype'),
    url(r'^create/(?P<template_id>[\d]+)/?$', GenericEntity.CreateEntityView.as_view(), name='create_phenotype'),
    url(r'^update/(?P<entity_id>\w+)/(?P<entity_history_id>\d+)/?$', GenericEntity.CreateEntityView.as_view(), name='update_phenotype'),

    ## Publication
    url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/publish/$', Publish.Publish.as_view(),name='generic_entity_publish'),
    url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/decline/$', Decline.EntityDecline.as_view(),name='generic_entity_decline'),
    url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/submit/$', Publish.RequestPublish.as_view(),name='generic_entity_request_publish'),
]

# Add sitemaps & robots if required (only for HDRUK .org site (or local dev.) -- check is done in site.py)
urlpatterns += [
    url(r'^robots.txt/$', site.robots_txt, name='robots.txt'),
    url(r'^sitemap.xml/$', site.get_sitemap, name='sitemap.xml'),
]

# Add non-readonly pages
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        ## Data Source syncing with HDRUK
        url(r'^admin/run-datasource-sync/$', Admin.run_datasource_sync, name='datasource_sync'),
    ]

# Tooling
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        # Add admin tools
        url(r'^admin/run-stats/$', Admin.EntityStatisticsView.as_view(), name='run_entity_statistics'),
        url(r'^admin/run-homepage-stats/$', Admin.run_homepage_statistics, name='run_homepage_statistics'),
        # # Temporary admin tools
        # url(r'^adminTemp/admin_mig_phenotypes_dt/$', adminTemp.admin_mig_phenotypes_dt, name='admin_mig_phenotypes_dt'),
        # url(r'^adminTemp/admin_fix_read_codes_dt/$', adminTemp.admin_fix_read_codes_dt, name='admin_fix_read_codes_dt'),
        # url(r'^adminTemp/admin_mig_concepts_dt/$', adminTemp.admin_mig_concepts_dt, name='admin_mig_concepts_dt'),
        # url(r'^adminTemp/admin_force_links_dt/$', adminTemp.admin_force_concept_linkage_dt, name='admin_force_links_dt'),
        # url(r'^adminTemp/admin_fix_breathe_dt/$', adminTemp.admin_fix_breathe_dt, name='admin_fix_breathe_dt'),
        # url(r'^adminTemp/admin_fix_malformed_codes/$', adminTemp.admin_fix_malformed_codes, name='admin_fix_malformed_codes'),
        #url(r'^adminTemp/admin_update_phenoflowids/$', adminTemp.admin_update_phenoflowids, name='admin_update_phenoflowids'),
        url(r'^adminTemp/admin_force_adp_links/$', adminTemp.admin_force_adp_linkage, name='admin_force_adp_links'),
        url(r'^adminTemp/admin_fix_coding_system_linkage/$', adminTemp.admin_fix_coding_system_linkage, name='admin_fix_coding_system_linkage'),
        url(r'^adminTemp/admin_fix_concept_linkage/$', adminTemp.admin_fix_concept_linkage, name='admin_fix_concept_linkage'),
        url(r'^adminTemp/admin_force_brand_links/$', adminTemp.admin_force_brand_links, name='admin_force_brand_links'),
        url(r'^adminTemp/admin_update_phenoflow_targets/$', adminTemp.admin_update_phenoflow_targets, name='admin_update_phenoflow_targets'),
        url(r'^adminTemp/admin_upload_hdrn_assets/$', adminTemp.admin_upload_hdrn_assets, name='admin_upload_hdrn_assets'),
    ]
