'''
    URL Configuration for the Clinical-Code application.

    Pages appear as Working-sets, Concepts and Components within a Concept.
'''

from django.conf import settings
from django.urls import re_path as url
from django.contrib.auth import views as auth_views

from clinicalcode.views.DocumentationViewer import DocumentationViewer
from clinicalcode.views import (View, Admin, adminTemp,
                                GenericEntity, Profile, Moderation,
                                Publish, Decline, site)

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
    
    ## Changing password(s)
    url(
        route='^change-password/$',
        view=auth_views.PasswordChangeView.as_view(),
        name='password_change',
        kwargs={ 'post_change_redirect': 'concept_library_home' }
    ),

    # GenericEnities (Phenotypes)
    ## Search
    url(r'^phenotypes/$', GenericEntity.EntitySearchView.as_view(), name='search_phenotypes'),
    url(r'^phenotypes/(?P<entity_type>([A-Za-z0-9\-]+))/?$', GenericEntity.EntitySearchView.as_view(), name='search_phenotypes'),
    
    ## Detail
    url(r'^phenotypes/(?P<pk>\w+)/detail/$', GenericEntity.generic_entity_detail, name='entity_detail'),
    url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$', GenericEntity.generic_entity_detail, name='entity_history_detail'),

    url(r'^phenotypes/(?P<pk>\w+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_latest_version_codes_to_csv'),
    url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_version_codes_to_csv'),   

    ## Profile
    url(r'profile/$', Profile.MyProfile.as_view(), name='my_profile'),
    url(r'profile/collection/$', Profile.MyCollection.as_view(), name='my_collection'),
    url(r'moderation/$', Moderation.EntityModeration.as_view(), name='moderation_page'),

    ## Selection service(s)
    url(r'^query/(?P<template_id>\w+)/?$', GenericEntity.EntityDescendantSelection.as_view(), name='entity_descendants'),

    ## Support legacy Concept redirects
    url(r'^concepts/C(?P<pk>\d+)/detail/$', GenericEntity.RedirectConceptView.as_view(), name='redirect_concept_detail'),
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<history_id>\d+)/detail/$', GenericEntity.RedirectConceptView.as_view(), name='redirect_concept_detail_with_version'),

    ## Documentation for create
    url(r'^documentation/(?P<documentation>([A-Za-z0-9\-]+))/?$', DocumentationViewer.as_view(), name='documentation_viewer'),
]

# Add sitemaps & robots if required
if settings.IS_HDRUK_EXT == "1" or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
        url(r'^robots.txt/$', site.robots_txt, name='robots.txt'),
        url(r'^sitemap.xml/$', site.get_sitemap, name='sitemap.xml'),
    ]

# Add non-readonly pages
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        # Base
        ## Contact
        url(r'^contact-us/$', View.contact_us, name='contact_us'),

        ## Data Source syncing with HDRUK
        url(r'^admin/run-datasource-sync/$', Admin.run_datasource_sync, name='datasource_sync'),

        # GenericEnities (Phenotypes)
        ## Create / Update
        url(r'^create/$', GenericEntity.CreateEntityView.as_view(), name='create_phenotype'),
        url(r'^create/(?P<template_id>[\d]+)/?$', GenericEntity.CreateEntityView.as_view(), name='create_phenotype'),
        url(r'^update/(?P<entity_id>\w+)/(?P<entity_history_id>\d+)/?$', GenericEntity.CreateEntityView.as_view(), name='update_phenotype'),

        ## Publication
        url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/publish/$', Publish.Publish.as_view(),name='generic_entity_publish'),
        url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/decline/$', Decline.EntityDecline.as_view(),name='generic_entity_decline'),
        url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/submit/$', Publish.RequestPublish.as_view(),name='generic_entity_request_publish'),
        url(r'email-preview/', Publish.RequestPublish.email_preview, name='email_preview'),
    ]

# Tooling
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        # Add admin tools
        url(r'^admin/run-stats/$', Admin.EntityStatisticsView.as_view(), name='run_entity_statistics'),
        url(r'^admin/run-homepage-stats/$', Admin.run_homepage_statistics, name='run_homepage_statistics'),

        # Temporary admin tools
        url(r'^adminTemp/admin_mig_phenotypes_dt/$', adminTemp.admin_mig_phenotypes_dt, name='admin_mig_phenotypes_dt'),
        url(r'^adminTemp/admin_fix_read_codes_dt/$', adminTemp.admin_fix_read_codes_dt, name='admin_fix_read_codes_dt'),
        url(r'^adminTemp/admin_mig_concepts_dt/$', adminTemp.admin_mig_concepts_dt, name='admin_mig_concepts_dt'),
        url(r'^adminTemp/admin_force_links_dt/$', adminTemp.admin_force_concept_linkage_dt, name='admin_force_links_dt'),
        url(r'^adminTemp/admin_fix_breathe_dt/$', adminTemp.admin_fix_breathe_dt, name='admin_fix_breathe_dt'),
    ]
