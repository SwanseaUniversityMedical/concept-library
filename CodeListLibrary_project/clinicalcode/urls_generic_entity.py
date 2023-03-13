'''
    URL Configuration for the Generic Entity.
'''

from django.conf import settings
from django.urls import re_path as url
from django.contrib.auth import views as auth_views

from clinicalcode.views import Publish
from clinicalcode.views import Decline



from .views import (GenericEntity, adminTemp)

from django.urls import path
from django.views.generic.base import TemplateView

#from django.views.generic import RedirectView
#from django.urls import reverse_lazy, reverse

urlpatterns = []
 
 
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [       
        url(r'^ge/(?P<pk>PH\d+)/version/(?P<history_id>\d+)/detail/$',
            GenericEntity.generic_entity_detail,
            name='generic_entity_history_detail'),


        url(r'^ge/(?P<pk>PH\d+)/(?P<history_id>\d+)/publish/$',Publish.Publish.as_view(),name='generic_entity_publish'),

        url(r'^ge/(?P<pk>PH\d+)/(?P<history_id>\d+)/decline/$',Decline.EntityDecline.as_view(),name='generic_entity_decline'),


        url(r'^ge/(?P<pk>PH\d+)/(?P<history_id>\d+)/submit/$',Publish.RequestPublish.as_view(),name='generic_entity_request_publish'),
            
        url(r'^search/$', GenericEntity.EntitySearchView.as_view(), name='entity_search_page'),

        url(r'^ge/create/$', GenericEntity.CreateEntityView.as_view(), name='create_phenotype'),
        url(r'^ge/run-stats/$', GenericEntity.EntityStatisticsView.as_view(), name='run_entity_statistics'),

        url(r'^ge/(?P<pk>PH\d+)/uniquecodesbyversion/(?P<phenotype_history_id>\d+)/concept/C(?P<target_concept_id>\d+)/(?P<target_concept_history_id>\d+)/$',
            GenericEntity.phenotype_concept_codes_by_version,
            name='ge_phenotype_concept_codes_by_version'),
    ]

    # for admin(developers) to migrate phenotypes into dynamic template
    if not settings.CLL_READ_ONLY:
        urlpatterns += [
            url(r'^adminTemp/admin_mig_phenotypes_dt/$', adminTemp.admin_mig_phenotypes_dt, name='admin_mig_phenotypes_dt'),
        ]






# ======== Generic Entity ==============================================================================
# if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
#     # add URLConf to create, update, and delete Phenotypes Working Sets
#     urlpatterns += [
#         url(r'^ge/(?P<pk>WS\d+)/detail/$',
#             GenericEntity.WorkingsetDetail_combined,
#             name='phenotypeworkingset_detail'),

#         url(r'^ge/(?P<pk>WS\d+)/export/codes/$',
#             GenericEntity.history_workingset_codes_to_csv,
#             name='latestVersion_phenotypeworkingset_codes_to_csv'),
#         url(r'^ge/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
#             GenericEntity.history_workingset_codes_to_csv,
#             name='history_phenotypeworkingset_codes_to_csv'),    
#         url(r'^ge/(?P<pk>WS\d+)/uniquecodesbyversion/(?P<workingset_history_id>\d+)/concept/C(?P<target_concept_id>\d+)/(?P<target_concept_history_id>\d+)/$',
#             GenericEntity.workingset_conceptcodesByVersion,
#             name='phenotypeworkingset_conceptcodesByVersion'),
#     ]
#
#     if not settings.CLL_READ_ONLY:
#         urlpatterns += [
#             url(r'^ge/create/$',
#                 GenericEntity.WorkingSetCreate.as_view(),
#                 name='phenotypeworkingset_create'),
#
#             # temp create test DB ws
#             url(r'^ge/create-test-db/$',
#                 GenericEntity.phenotype_workingset_DB_test_create,
#                 name='phenotype_workingset_DB_test_create'),
#
#
#             url(r'^ge/(?P<pk>WS\d+)/update/$',
#                 GenericEntity.WorkingSetUpdate.as_view(),
#                 name='phenotypeworkingset_update'),
#
#             url(r'^ge/(?P<pk>WS\d+)/delete/$',
#                 GenericEntity.WorkingSetDelete.as_view(),
#                 name='phenotypeworkingset_delete'),
#
#             url(r'^ge/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/revert/$',
#                 GenericEntity.workingset_history_revert,
#                 name='phenotypeworkingset_history_revert'),
#
#             url(r'^ge/(?P<pk>WS\d+)/restore/$',
#                 GenericEntity.WorkingSetRestore.as_view(),
#                 name='phenotypeworkingset_create_restore'),
#         ]

       


