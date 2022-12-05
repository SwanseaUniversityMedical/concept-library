'''
    URL Configuration for the Clinical-Code application.

    Pages appear as Working-sets, Concepts and Components within a Concept.
'''

#from cll import settings
from django.conf import settings
#from django.conf.urls import url  # , include  #, handler400
from django.urls import re_path as url
from django.contrib.auth import views as auth_views

from .views import (Admin, ComponentConcept, ComponentExpression,
                    ComponentQueryBuilder, Concept, Phenotype, View,
                    WorkingSet, SelectPhenotype, PhenotypeWorkingSet, adminTemp, site)

from django.urls import path
from django.views.generic.base import TemplateView

#from django.views.generic import RedirectView
#from django.urls import reverse_lazy, reverse

urlpatterns = [
    url(r'^$', View.index, name='concept_library_home'),
    url(r'^home/$', View.index, name='concept_library_home2'),
    url(r'^concepts/$', Concept.concept_list, name='concept_list'),
    url(r'^workingsets/$', WorkingSet.workingset_list, name='workingset_list'),
    url(r'^phenotypeworkingsets/select-concepts/$', SelectPhenotype.selection_list, name='selection_list'),
    url(r'^phenotypeworkingsets/$', PhenotypeWorkingSet.workingset_list, name='phenotypeworkingsets_list'),
    url(r'^phenotypes/$', Phenotype.phenotype_list, name='phenotype_list'),
    
    url(r'^cookies-settings/$', View.cookies_settings, name='cookies_settings'),
    url(r'^reference-data/$', View.reference_data, name='reference_data'),

    #     # redirect api root '/api' to '/api/v1'
    #     #url(r'^api/$', RedirectView.as_view(url= reverse('api:root')) , name='api_root_v1'),
]

# About pages
urlpatterns += [
    # brand/main about pages
    url(r'^about/(?P<pg_name>\w+)/$', View.about_pages, name='about_page'),
]

# HDR-UK portal redirect to CL
urlpatterns += [
    url(r'^old/phenotypes/(?P<unique_url>.+)/$', View.HDRUK_portal_redirect, name='HDRUK_portal_redirect'),
]

# (terms and conditions) and privacy/cookie policy pages
urlpatterns += [
    url(r'^terms-and-conditions/$', View.termspage, name='terms'),
    url(r'^privacy-and-cookie-policy/$', View.cookiespage, name='privacy_and_cookie_policy'),
    url(r'^technical_documentation/$', View.technicalpage, name='technical_documentation'),
]

# contact us page
#if not settings.CLL_READ_ONLY:
urlpatterns += [
    url(r'^contact-us/$', View.contact_us, name='contact_us'),
]

#======== robots.txt / sitemap ====================================================================
if settings.IS_HDRUK_EXT == "1" or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
        url(r'^robots.txt/$', site.robots_txt, name='robots.txt'),
        url(r'^sitemap.xml/$', site.get_sitemap, name='sitemap.xml'),
        
    ]
    

#======== Admin ===================================================================================
# for API testing
if not settings.CLL_READ_ONLY and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC):
    urlpatterns += [
        url(r'^adminTemp/api_remove_data/$', adminTemp.api_remove_data, name='api_remove_data'),
    ]

# for admin(developers) to mark phenotypes as deleted/restored
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^adminTemp/delete-phenotype/$', adminTemp.admin_delete_phenotypes, name='admin_delete_phenotypes'),
        url(r'^adminTemp/restore-phenotype/$', adminTemp.admin_restore_phenotypes, name='admin_restore_phenotypes'),
    ]


# saving statistics
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^admin/run-datasource-sync/$', Admin.run_datasource_sync, name='datasource_sync'),# Datasource sync
        url(r'^admin/run-stat/$',  Admin.run_statistics, name='HDRUK_run_statistics'),# HDRUK home page stat
        url(r'^admin/run-stat-filters/$', Admin.run_filter_statistics, name='collections_run_filters'),# filter stat
    ]

# check concepts not associated with phenotypes
urlpatterns += [
    url(r'^admin/uc/$',
        adminTemp.check_concepts_not_associated_with_phenotypes,
        name='check_concepts_not_associated_with_phenotypes-uc'),
    url(r'^admin/concepts_not_in_phenotypes/$',
        adminTemp.check_concepts_not_associated_with_phenotypes,
        name='check_concepts_not_associated_with_phenotypes'),
]

# get_caliberresearch_url_source
urlpatterns += [
    url(r'^admin/caliber-urls/$',
        Admin.get_caliberresearch_url_source,
        name='get_caliberresearch_url_source'),
]

# ======== Phenotypes Working Sets ==============================================================================
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    # add URLConf to create, update, and delete Phenotypes Working Sets
    urlpatterns += [
        url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/detail/$',
            PhenotypeWorkingSet.WorkingsetDetail_combined,
            name='phenotypeworkingset_detail'),
        url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/detail/$',
            PhenotypeWorkingSet.WorkingsetDetail_combined,
            name='phenotypeworkingset_history_detail'),
        url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/export/codes/$',
            PhenotypeWorkingSet.history_workingset_codes_to_csv,
            name='latestVersion_phenotypeworkingset_codes_to_csv'),
        url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
            PhenotypeWorkingSet.history_workingset_codes_to_csv,
            name='history_phenotypeworkingset_codes_to_csv'),    
        url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/uniquecodesbyversion/(?P<workingset_history_id>\d+)/concept/C(?P<target_concept_id>\d+)/(?P<target_concept_history_id>\d+)/$',
            PhenotypeWorkingSet.workingset_conceptcodesByVersion,
            name='phenotypeworkingset_conceptcodesByVersion'),
    ]
    
    if not settings.CLL_READ_ONLY:
        urlpatterns += [
            url(r'^phenotypeworkingsets/create/$',
                PhenotypeWorkingSet.WorkingSetCreate.as_view(),
                name='phenotypeworkingset_create'),
            
            # temp create test DB ws
            url(r'^phenotypeworkingsets/create-test-db/$',
                PhenotypeWorkingSet.phenotype_workingset_DB_test_create,
                name='phenotype_workingset_DB_test_create'),
    
    
            url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/update/$',
                PhenotypeWorkingSet.WorkingSetUpdate.as_view(),
                name='phenotypeworkingset_update'),
    
            url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/delete/$',
                PhenotypeWorkingSet.WorkingSetDelete.as_view(),
                name='phenotypeworkingset_delete'),
    
            url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/revert/$',
                PhenotypeWorkingSet.workingset_history_revert,
                name='phenotypeworkingset_history_revert'),
            
            url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/restore/$',
                PhenotypeWorkingSet.WorkingSetRestore.as_view(),
                name='phenotypeworkingset_create_restore'),
        ]


# ======== Phenotypes ==============================================================================
# add URLConf to create, update, and delete Phenotypes
urlpatterns += [
    url(r'^phenotypes/(?P<pk>PH\d+)/detail/$',
        Phenotype.PhenotypeDetail_combined,
        name='phenotype_detail'),
    url(r'^phenotypes/(?P<pk>PH\d+)/version/(?P<phenotype_history_id>\d+)/detail/$',
        Phenotype.PhenotypeDetail_combined,
        name='phenotype_history_detail'),
    url(r'^phenotypes/(?P<pk>PH\d+)/export/codes/$',
        Phenotype.history_phenotype_codes_to_csv,
        name='latestVersion_phenotype_codes_to_csv'),
    url(r'^phenotypes/(?P<pk>PH\d+)/version/(?P<phenotype_history_id>\d+)/export/codes/$',
        Phenotype.history_phenotype_codes_to_csv,
        name='history_phenotype_codes_to_csv'),    
    url(r'^phenotypes/(?P<pk>PH\d+)/uniquecodesbyversion/(?P<phenotype_history_id>\d+)/concept/C(?P<target_concept_id>\d+)/(?P<target_concept_history_id>\d+)/$',
        Phenotype.phenotype_conceptcodesByVersion,
        name='phenotype_conceptcodesByVersion'),
]

# if not settings.CLL_READ_ONLY:
#     urlpatterns += [
#         url(r'^phenotypes/create/$',
#             Phenotype.phenotype_create,
#             name='phenotype_create'),
#
#         url(r'^phenotypes/(?P<pk>PH\d+)/update/$',
#             Phenotype.PhenotypeUpdate.as_view(),
#             name='phenotype_update'),
#
#         url(r'^phenotypes/(?P<pk>PH\d+)/delete/$',
#             Phenotype.PhenotypeDelete.as_view(),
#             name='phenotype_delete'),
#
#         # url(r'^phenotypes/(?P<pk>PH\d+)/version/(?P<phenotype_history_id>\d+)/revert/$',
#         #     Phenotype.phenotype_history_revert,
#         #     name='phenotype_history_revert'),
#         #
#         # url(r'^phenotypes/(?P<pk>PH\d+)/restore/$',
#         #     Phenotype.PhenotypeRestore.as_view(),
#         #     name='phenotype_restore'),
#     ]

#======== WorkingSets ==============================================================================
# add URLConf to create, update, and delete working sets
urlpatterns += [
    url(r'^workingsets/WS(?P<pk>\d+)/detail/$',
        WorkingSet.WorkingSetDetail.as_view(),
        name='workingset_detail'),
    url(r'^workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/detail/$',
        WorkingSet.workingset_history_detail,
        name='workingset_history_detail'),
    url(r'^workingsets/WS(?P<pk>\d+)/export/codes/$',
        WorkingSet.workingset_to_csv,
        name='workingset_to_csv'),
    url(r'^workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
        WorkingSet.history_workingset_to_csv,
        name='history_workingset_to_csv'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^workingsets/create/$',
            WorkingSet.workingset_create,
            name='workingset_create'),
        url(r'^workingsets/WS(?P<pk>\d+)/update/$',
            WorkingSet.WorkingSetUpdate.as_view(),
            name='workingset_update'),
        url(r'^workingsets/WS(?P<pk>\d+)/delete/$',
            WorkingSet.WorkingSetDelete.as_view(),
            name='workingset_delete'),
        url(r'^workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/revert/$',
            WorkingSet.workingset_history_revert,
            name='workingset_history_revert'),
        url(r'^workingsets/WS(?P<pk>\d+)/restore/$',
            WorkingSet.WorkingSetRestore.as_view(),
            name='workingset_restore'),
    ]

#======== Concepts ==============================================================================
# add URLConf to create, update, and delete concepts
urlpatterns += [
    url(r'^concepts/C(?P<pk>\d+)/detail/$',
        Concept.ConceptDetail_combined,
        name='concept_detail'),
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/detail/$',
        Concept.ConceptDetail_combined,
        name='concept_history_detail'),
    url(r'^concepts/C(?P<pk>\d+)/export/codes/$',
        Concept.concept_codes_to_csv,
        name='concept_codes_to_csv'),
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/export/codes/$',
        Concept.history_concept_codes_to_csv,
        name='history_concept_codes_to_csv'),

    #     url(r'^concepts/C(?P<pk>\d+)/tree/$',
    #         Concept.concept_tree,
    #         name='concept_tree'),
    url(r'^concepts/C(?P<pk>\d+)/components/$',
        Concept.concept_components,
        name='concept_components'),
    url(r'^concepts/C(?P<pk>\d+)/uniquecodes/$',
        Concept.concept_uniquecodes,
        name='concept_uniquecodes'),
    url(r'^concepts/C(?P<pk>\d+)/uniquecodesbyversion/(?P<concept_history_id>\d+)/$',
        Concept.concept_uniquecodesByVersion,
        name='concept_uniquecodesByVersion'),
    url(r'^concepts/choose_concepts_to_compare/$',
        Concept.choose_concepts_to_compare,
        name='choose_concepts_to_compare'),
    url(r'^concepts/C(?P<concept_id>\d+)/(?P<version_id>\d+)/compare/C(?P<concept_ref_id>\d+)/(?P<version_ref_id>\d+)/$',
        Concept.compare_concepts_codes,
        name='compare_concepts_codes'),
    url(r'^concepts/C(?P<pk>\d+)/conceptversions/(?P<concept_history_id>\d+)/(?P<indx>\d+)/$',
        Concept.conceptversions,
        name='conceptversions'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^concepts/create/$',
            Concept.ConceptCreate.as_view(),
            name='concept_create'),
        url(r'^concepts/C(?P<pk>\d+)/update/$',
            Concept.ConceptUpdate.as_view(),
            name='concept_update'),
        url(r'^concepts/C(?P<pk>\d+)/delete/$',
            Concept.ConceptDelete.as_view(),
            name='concept_delete'),
        url(r'^concepts/C(?P<pk>\d+)/fork/$',
            Concept.ConceptFork.as_view(),
            name='concept_fork'),
        url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/fork/$',
            Concept.concept_history_fork,
            name='concept_history_fork'),
        url(r'^concepts/C(?P<pk>\d+)/restore/$',
            Concept.ConceptRestore.as_view(),
            name='concept_restore'),
        url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/revert/$',
            Concept.concept_history_revert,
            name='concept_history_revert'),
        url(r'^concepts/C(?P<pk>\d+)/upload/codes/$',
            Concept.concept_upload_codes,
            name='concept_upload_codes'),
    ]

#======== concept component ==============================================================================
# urlConf for concept component
urlpatterns += [
    url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/concept/(?P<pk>\d+)/detail/$',
        ComponentConcept.component_history_concept_detail_combined,
        name='component_history_concept_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/detail/$',
    #         ComponentConcept.ComponentConceptDetail.as_view(),
    #         name='component_concept_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/concept/(?P<pk>\d+)/detail/$',
    #         ComponentConcept.component_history_concept_detail,
    #         name='component_history_concept_detail'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^components/C(?P<concept_id>\d+)/concept/create/$',
            ComponentConcept.ComponentConceptCreate.as_view(),
            name='component_concept_create'),
        url(r'^components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/(?P<update_to_latest_version>\d+)/update/$',
            ComponentConcept.ComponentConceptUpdate.as_view(),
            name='component_concept_update'),
        url(r'^components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/delete/$',
            ComponentConcept.ComponentConceptDelete.as_view(),
            name='component_concept_delete'),
    ]

#======== query builder component ==============================================================================
# urlConf for query builder component
urlpatterns += [
    url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
        ComponentQueryBuilder.component_history_querybuilder_detail_combined,
        name='component_history_querybuilder_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
    #         ComponentQueryBuilder.ComponentQueryBuilderDetail.as_view(),
    #         name='component_querybuilder_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
    #         ComponentQueryBuilder.component_history_querybuilder_detail,
    #         name='component_history_querybuilder_detail'),
    url(r'^components/C(?P<concept_id>\d+)/querybuilder/search/$',
        ComponentQueryBuilder.component_querybuilder_search,
        name='component_querybuilder_search'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^components/C(?P<concept_id>\d+)/querybuilder/create/$',
            ComponentQueryBuilder.ComponentQueryBuilderCreate.as_view(),
            name='component_querybuilder_create'),
        url(r'^components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/update/$',
            ComponentQueryBuilder.ComponentQueryBuilderUpdate.as_view(),
            name='component_querybuilder_update'),
        url(r'^components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/delete/$',
            ComponentQueryBuilder.ComponentQueryBuilderDelete.as_view(),
            name='component_querybuilder_delete'),
    ]

#======== Match Code With An Expression Component ==============================================================================
# urlConf for Match Code With An Expression Component
urlpatterns += [
    url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expression/(?P<pk>\d+)/detail/$',
        ComponentExpression.component_history_expression_detail_combined,
        name='component_history_expression_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/detail/$',
    #         ComponentExpression.ComponentExpressionDetail.as_view(),
    #         name='component_expression_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expression/(?P<pk>\d+)/detail/$',
    #         ComponentExpression.component_history_expression_detail,
    #         name='component_history_expression_detail'),
    url(r'^components/C(?P<concept_id>\d+)/searchcodes/$',
        ComponentExpression.component_expression_searchcodes,
        name='component_expression_searchcodes'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^components/C(?P<concept_id>\d+)/expression/create/$',
            ComponentExpression.ComponentExpressionCreate.as_view(),
            name='component_expression_create'),
        url(r'^components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/update/$',
            ComponentExpression.ComponentExpressionUpdate.as_view(),
            name='component_expression_update'),
        url(r'^components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/delete/$',
            ComponentExpression.ComponentExpressionDelete.as_view(),
            name='component_expression_delete'),
    ]

#======== code list component ==============================================================================
# urlConf for code list component
urlpatterns += [
    url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
        ComponentExpression.component_history_expressionselect_detail_combined,
        name='component_history_expressionselect_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
    #         ComponentExpression.ComponentExpressionSelectDetail.as_view(),
    #         name='component_expressionselect_detail'),

    #     url(r'^components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
    #         ComponentExpression.component_history_expressionselect_detail,
    #         name='component_history_expressionselect_detail'),
    url(r'^components/C(?P<concept_id>\d+)/expressionselect/search/$',
        ComponentExpression.component_expressionselect_search_codes,
        name='component_expressionselect_search_codes'),
    url(r'^components/C(?P<concept_id>\d+)/expressionselect/(?P<code_list_id>\d+)/codes/$',
        ComponentExpression.component_expressionselect_codes,
        name='component_expressionselect_codes'),
]

if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^components/C(?P<concept_id>\d+)/expressionselect/create/$',
            ComponentExpression.ComponentExpressionSelectCreate.as_view(),
            name='component_expressionselect_create'),
        url(r'^components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/update/$',
            ComponentExpression.ComponentExpressionSelectUpdate.as_view(),
            name='component_expressionselect_update'),

        #         url(r'^components/C(?P<concept_id>\d+)/expressionselect/(?P<code_list_id>\d+)/code/create/$',
        #             ComponentExpression.ComponentExpressionSelectCodeCreate.as_view(),
        #             name='component_expressionselect_code_create'),
        url(r'^components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/delete/$',
            ComponentExpression.ComponentExpressionSelectDelete.as_view(),
            name='component_expressionselect_delete'),
    ]

#======== change password ==============================================================================
# use Django form
urlpatterns += [
    url(
        '^change-password/$',
        auth_views.PasswordChangeView.as_view(),  #.password_change, 
        {'post_change_redirect': 'concept_library_home'},
        name='password_change'),
]

#======== Check concurrent update =======================================================================
if not settings.CLL_READ_ONLY:
    # for Ajax
    urlpatterns += [
        url(r'^concepts/C(?P<pk>\d+)/check_concurrent_concept_update/$',
            Concept.check_concurrent_concept_update,
            name='check_concurrent_concept_update'),
    ]

#======== Publish Concept =========================================================================
if settings.ENABLE_PUBLISH:
    urlpatterns += [
        url(r'^concepts/C(?P<pk>\d+)/(?P<concept_history_id>\d+)/publish/$',
            Concept.ConceptPublish.as_view(),
            name='concept_publish'),
        url(r'^phenotypes/(?P<pk>PH\d+)/(?P<phenotype_history_id>\d+)/publish/$',
            Phenotype.PhenotypePublish.as_view(),
            name='phenotype_publish'),
        url(r'^phenotypeworkingset/(?P<pk>WS\d+)/(?P<workingset_history_id>\d+)/publish/$',
            PhenotypeWorkingSet.WorkingSetPublish.as_view(),
            name='workingset_publish'),
        url(r'^phenotypeworkingset/(?P<pk>WS\d+)/(?P<workingset_history_id>\d+)/submit/$',
            PhenotypeWorkingSet.WorkingSetSubmit.as_view(),
            name='workingset_submit')
    ]

# handler400 = 'clinicalcode.views.bad_request'
# handler403 = 'clinicalcode.views.permission_denied'
# handler404 = 'clinicalcode.views.page_not_found'
# handler500 = 'clinicalcode.views.server_error'
