'''
    URL Configuration for the Generic Entity.
'''

from django.conf import settings
from django.urls import re_path as url
from django.contrib.auth import views as auth_views

from .views import (GenericEntity, adminTemp, Profile, Moderation)
from clinicalcode.views import Publish
from clinicalcode.views import Decline

from django.urls import path
from django.views.generic.base import TemplateView

#from django.views.generic import RedirectView
#from django.urls import reverse_lazy, reverse

urlpatterns = []
 
 
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [  

        url(r'^search/$', GenericEntity.EntitySearchView.as_view(), name='search_entity'),
        url(r'^search/(?P<entity_type>([A-Za-z0-9\-]+))/?$', GenericEntity.EntitySearchView.as_view(), name='search_entity'),
        

        url(r'^phenotypes/(?P<pk>\w+)/detail/$', GenericEntity.generic_entity_detail, name='entity_detail'),
        url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$', GenericEntity.generic_entity_detail, name='entity_history_detail'),

        url(r'^phenotypes/(?P<pk>\w+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_latest_version_codes_to_csv'),
        url(r'^phenotypes/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$', GenericEntity.export_entity_codes_to_csv, name='export_entity_version_codes_to_csv'),   

        url(r'^phenotypes/(?P<pk>\w+)/uniquecodesbyversion/(?P<history_id>\d+)/concept/C(?P<target_concept_id>\d+)/(?P<target_concept_history_id>\d+)/$',
            GenericEntity.phenotype_concept_codes_by_version,
            name='ge_phenotype_concept_codes_by_version'),            
 
        # Profile
        url(r'profile/$', Profile.MyProfile.as_view(), name='my_profile'),
        url(r'profile/collection/$', Profile.MyCollection.as_view(), name='my_collection'),

        url(r'moderation/$', Moderation.EntityModeration.as_view(), name='moderation_page'),        

        # Example - remove at production
        url(r'^ge/example/$', GenericEntity.ExampleSASSView.as_view(), name='example_phenotype'),
        url(r'^ge/search/temp/$', GenericEntity.generic_entity_list_temp, name='generic_entity_list_temp'),


    ]




    # for create/update - not to work in Read-only mode
    if not settings.CLL_READ_ONLY:
        urlpatterns += [
            url(r'^create/$', GenericEntity.CreateEntityView.as_view(), name='create_entity'),
            url(r'^create/(?P<template_id>[\d]+)/?$', GenericEntity.CreateEntityView.as_view(), name='create_entity'),
            url(r'^update/(?P<entity_id>\w+)/(?P<entity_history_id>\d+)/?$', GenericEntity.CreateEntityView.as_view(), name='update_entity'),

            # publish
            url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/publish/$',Publish.Publish.as_view(),name='generic_entity_publish'),
            url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/decline/$',Decline.EntityDecline.as_view(),name='generic_entity_decline'),
            url(r'^phenotypes/(?P<pk>\w+)/(?P<history_id>\d+)/submit/$',Publish.RequestPublish.as_view(),name='generic_entity_request_publish'),
        ]

    # Add admin tools
    if not settings.CLL_READ_ONLY:
        urlpatterns += [
            url(r'^admin/run-stats/$', GenericEntity.EntityStatisticsView.as_view(), name='run_entity_statistics'),
        ]

    # for admin(developers) to migrate phenotypes into dynamic template       
    if not settings.CLL_READ_ONLY:
        urlpatterns += [
            url(r'^adminTemp/admin_mig_phenotypes_dt/$', adminTemp.admin_mig_phenotypes_dt, name='admin_mig_phenotypes_dt'),
        ]
