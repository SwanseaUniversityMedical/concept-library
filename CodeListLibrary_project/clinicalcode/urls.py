'''
    URL Configuration for the Clinical-Code application.

    Pages appear as Working-sets, Concepts and Components within a Concept.
'''

from django.conf.urls import url #, include  #, handler400 
from django.contrib.auth import views as auth_views

#from cll import settings
from django.conf import settings

from views import (
    View, Concept, ComponentConcept, ComponentExpression,
    ComponentQueryBuilder, WorkingSet, adminTemp, Phenotype, Admin
)

from api.views import View as api_view
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy, reverse

urlpatterns = [
    url(r'^$', View.index, name='concept_library_home' ),
    url(r'^(?i)home/$', View.index, name='concept_library_home' ),

    url(r'^(?i)concepts/$', Concept.concept_list, name='concept_list'),
    url(r'^(?i)workingsets/$', WorkingSet.workingset_list, name='workingset_list'),
    url(r'^(?i)phenotypes/$', Phenotype.phenotype_list, name='phenotype_list'),
    
    # redirect api root '/api' to '/api/v1'
    url(r'^(?i)api/$', RedirectView.as_view(url= reverse('api:root')) , name='api_root_v1'),
]

 
# About pages
urlpatterns += [
    # brand/main about pages
    url(r'^(?i)about/(?P<pg_name>\w+)/$', View.about_pages, name='about_page' ),
]

# HDR-UK portal redirect to CL
urlpatterns += [
    url(r'^(?i)old/phenotypes/(?P<unique_url>.+)/$', View.HDRUK_portal_redirect, name='HDRUK_portal_redirect' ),
]

# (terms and conditions) and privacy/cookie policy pages 
urlpatterns += [
    url(r'^(?i)terms-and-conditions/$', View.termspage, name='terms'),
    url(r'^(?i)privacy-and-cookie-policy/$', View.cookiespage, name='privacy_and_cookie_policy'),
]
#======== Admin ===================================================================================
# for API testing 
if not settings.CLL_READ_ONLY:# and (settings.IS_DEMO or settings.IS_DEVELOPMENT_PC): 
    urlpatterns += [
        url(r'^(?i)adminTemp/api_remove_data/$', 
            adminTemp.api_remove_data, 
            name='api_remove_data'),      
    ]
    
# saving statistics 
if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)admin/run-stat/$',    # HDRUK stat
            Admin.run_statistics, 
            name='HDRUK_run_statistics'),      

        url(r'^(?i)admin/run-stat-collections/$',    # collections filter stat
            Admin.run_statistics_collections,
            name='collections_run_statistics'),
    ]      

# check concepts not associated with phenotypes
urlpatterns += [
    url(r'^(?i)admin/uc/$',
        adminTemp.check_concepts_not_associated_with_phenotypes,
        name='check_concepts_not_associated_with_phenotypes-uc'),

    url(r'^(?i)admin/concepts_not_in_phenotypes/$',
        adminTemp.check_concepts_not_associated_with_phenotypes,
        name='check_concepts_not_associated_with_phenotypes'),    
    ]  


# ======== Phenotypes ==============================================================================
# add URLConf to create, update, and delete Phenotypes
urlpatterns += [
    url(r'^(?i)phenotypes/PH(?P<pk>\d+)/detail/$',
        Phenotype.PhenotypeDetail_combined,
        name='phenotype_detail'),

    url(r'^(?i)phenotypes/PH(?P<pk>\d+)/version/(?P<phenotype_history_id>\d+)/detail/$',
        Phenotype.PhenotypeDetail_combined,
        name='phenotype_history_detail'),
    
    url(r'^(?i)phenotypes/PH(?P<pk>\d+)/version/(?P<phenotype_history_id>\d+)/export/concepts/$',
        Phenotype.history_phenotype_codes_to_csv,
        name='history_phenotype_codes_to_csv'),
    
    url(r'^(?i)phenotypes/PH(?P<pk>\d+)/uniquecodesbyversion/(?P<phenotype_history_id>\d+)/$',
        Phenotype.phenotype_conceptcodesByVersion,
        name='phenotype_conceptcodesByVersion'),
]

# if not settings.CLL_READ_ONLY:
#     urlpatterns += [
#         url(r'^(?i)phenotypes/create/$',
#             Phenotype.phenotype_create,
#             name='phenotype_create'),
# 
#         url(r'^(?i)phenotypes/PH(?P<pk>\d+)/update/$',
#             Phenotype.PhenotypeUpdate.as_view(),
#             name='phenotype_update'),
# 
#         url(r'^(?i)phenotypes/PH(?P<pk>\d+)/delete/$',
#             Phenotype.PhenotypeDelete.as_view(),
#             name='phenotype_delete'),
# 
#         # url(r'^(?i)phenotypes/PH(?P<pk>\d+)/version/(?P<phenotype_history_id>\d+)/revert/$',
#         #     Phenotype.phenotype_history_revert,
#         #     name='phenotype_history_revert'),
#         #
#         # url(r'^(?i)phenotypes/PH(?P<pk>\d+)/restore/$',
#         #     Phenotype.PhenotypeRestore.as_view(),
#         #     name='phenotype_restore'),
#     ]


#======== WorkingSets ==============================================================================
# add URLConf to create, update, and delete working sets
urlpatterns += [
    url(r'^(?i)workingsets/WS(?P<pk>\d+)/detail/$',
        WorkingSet.WorkingSetDetail.as_view(),
        name='workingset_detail'),

    url(r'^(?i)workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/detail/$',
        WorkingSet.workingset_history_detail,
        name='workingset_history_detail'),

    url(r'^(?i)workingsets/WS(?P<pk>\d+)/export/codes/$',
        WorkingSet.workingset_to_csv,
        name='workingset_to_csv'),
    
    url(r'^(?i)workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
        WorkingSet.history_workingset_to_csv,
        name='history_workingset_to_csv'),
]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)workingsets/create/$', 
            WorkingSet.workingset_create, 
            name='workingset_create'),
    
        url(r'^(?i)workingsets/WS(?P<pk>\d+)/update/$',
            WorkingSet.WorkingSetUpdate.as_view(),
            name='workingset_update'),
       
        url(r'^(?i)workingsets/WS(?P<pk>\d+)/delete/$',
            WorkingSet.WorkingSetDelete.as_view(),
            name='workingset_delete'),
    
        url(r'^(?i)workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/revert/$',
            WorkingSet.workingset_history_revert,
            name='workingset_history_revert'),
    
        url(r'^(?i)workingsets/WS(?P<pk>\d+)/restore/$',
            WorkingSet.WorkingSetRestore.as_view(),
            name='workingset_restore'),         
    ]


#======== Concepts ==============================================================================
# add URLConf to create, update, and delete concepts
urlpatterns += [
    url(r'^(?i)concepts/C(?P<pk>\d+)/detail/$',
        Concept.ConceptDetail_combined,
        name='concept_detail'),

    url(r'^(?i)concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/detail/$',
        Concept.ConceptDetail_combined,
        name='concept_history_detail'),

    url(r'^(?i)concepts/C(?P<pk>\d+)/export/codes/$',
        Concept.concept_codes_to_csv,
        name='concept_codes_to_csv'),
    
    url(r'^(?i)concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/export/codes/$',
        Concept.history_concept_codes_to_csv,
        name='history_concept_codes_to_csv'),
    
#     url(r'^(?i)concepts/C(?P<pk>\d+)/tree/$',
#         Concept.concept_tree,
#         name='concept_tree'),

    url(r'^(?i)concepts/C(?P<pk>\d+)/components/$',
        Concept.concept_components,
        name='concept_components'),
    
    url(r'^(?i)concepts/C(?P<pk>\d+)/uniquecodes/$',
        Concept.concept_uniquecodes,
        name='concept_uniquecodes'),
    
    url(r'^(?i)concepts/C(?P<pk>\d+)/uniquecodesbyversion/(?P<concept_history_id>\d+)/$',
        Concept.concept_uniquecodesByVersion,
        name='concept_uniquecodesByVersion'),
                
    url(r'^(?i)concepts/choose_concepts_to_compare/$',
        Concept.choose_concepts_to_compare,
        name='choose_concepts_to_compare'),  
              
    url(r'^(?i)concepts/C(?P<concept_id>\d+)/(?P<version_id>\d+)/compare/C(?P<concept_ref_id>\d+)/(?P<version_ref_id>\d+)/$',
        Concept.compare_concepts_codes,
        name='compare_concepts_codes'),    
       
    url(r'^(?i)concepts/C(?P<pk>\d+)/conceptversions/(?P<concept_history_id>\d+)/(?P<indx>\d+)/$',
        Concept.conceptversions,
        name='conceptversions'),             
]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)concepts/create/$',
            Concept.ConceptCreate.as_view(),
            name='concept_create'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/update/$',
            Concept.ConceptUpdate.as_view(),
            name='concept_update'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/delete/$',
            Concept.ConceptDelete.as_view(),
            name='concept_delete'),
                        
        url(r'^(?i)concepts/C(?P<pk>\d+)/fork/$',
            Concept.ConceptFork.as_view(),
            name='concept_fork'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/fork/$',
            Concept.concept_history_fork,
            name='concept_history_fork'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/restore/$',
            Concept.ConceptRestore.as_view(),
            name='concept_restore'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/revert/$',
            Concept.concept_history_revert,
            name='concept_history_revert'),
    
        url(r'^(?i)concepts/C(?P<pk>\d+)/upload/codes/$',
            Concept.concept_upload_codes,
            name='concept_upload_codes'),

    ]

#======== concept component ==============================================================================
# urlConf for concept component
urlpatterns += [
    url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/concept/(?P<pk>\d+)/detail/$',
        ComponentConcept.component_history_concept_detail_combined,
        name='component_history_concept_detail'),
    
#     url(r'^(?i)components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/detail/$',
#         ComponentConcept.ComponentConceptDetail.as_view(),
#         name='component_concept_detail'),

#     url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/concept/(?P<pk>\d+)/detail/$',
#         ComponentConcept.component_history_concept_detail,
#         name='component_history_concept_detail'),
]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)components/C(?P<concept_id>\d+)/concept/create/$',
        ComponentConcept.ComponentConceptCreate.as_view(),
        name='component_concept_create'),
                    
        url(r'^(?i)components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/(?P<update_to_latest_version>\d+)/update/$',
        ComponentConcept.ComponentConceptUpdate.as_view(),
        name='component_concept_update'),          
                    
        url(r'^(?i)components/C(?P<concept_id>\d+)/concept/(?P<pk>\d+)/delete/$',
        ComponentConcept.ComponentConceptDelete.as_view(),
        name='component_concept_delete'),                  
    ]

#======== query builder component ==============================================================================
# urlConf for query builder component
urlpatterns += [        
    url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
        ComponentQueryBuilder.component_history_querybuilder_detail_combined,
        name='component_history_querybuilder_detail'),
    
#     url(r'^(?i)components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
#         ComponentQueryBuilder.ComponentQueryBuilderDetail.as_view(),
#         name='component_querybuilder_detail'),

#     url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/querybuilder/(?P<pk>\d+)/detail/$',
#         ComponentQueryBuilder.component_history_querybuilder_detail,
#         name='component_history_querybuilder_detail'),
    
    url(r'^(?i)components/C(?P<concept_id>\d+)/querybuilder/search/$',
        ComponentQueryBuilder.component_querybuilder_search,
        name='component_querybuilder_search'),
    ]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)components/C(?P<concept_id>\d+)/querybuilder/create/$',
        ComponentQueryBuilder.ComponentQueryBuilderCreate.as_view(),
        name='component_querybuilder_create'),

        url(r'^(?i)components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/update/$',
            ComponentQueryBuilder.ComponentQueryBuilderUpdate.as_view(),
            name='component_querybuilder_update'),
    
        url(r'^(?i)components/C(?P<concept_id>\d+)/querybuilder/(?P<pk>\d+)/delete/$',
            ComponentQueryBuilder.ComponentQueryBuilderDelete.as_view(),
            name='component_querybuilder_delete'),
                    
    ]

#======== Match Code With An Expression Component ==============================================================================
# urlConf for Match Code With An Expression Component
urlpatterns += [
    url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expression/(?P<pk>\d+)/detail/$',
        ComponentExpression.component_history_expression_detail_combined,
        name='component_history_expression_detail'),
        
#     url(r'^(?i)components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/detail/$',
#         ComponentExpression.ComponentExpressionDetail.as_view(),
#         name='component_expression_detail'),

#     url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expression/(?P<pk>\d+)/detail/$',
#         ComponentExpression.component_history_expression_detail,
#         name='component_history_expression_detail'),

    url(r'^(?i)components/C(?P<concept_id>\d+)/searchcodes/$',
        ComponentExpression.component_expression_searchcodes,
        name='component_expression_searchcodes'),
]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)components/C(?P<concept_id>\d+)/expression/create/$',
            ComponentExpression.ComponentExpressionCreate.as_view(),
            name='component_expression_create'),
    
        url(r'^(?i)components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/update/$',
            ComponentExpression.ComponentExpressionUpdate.as_view(),
            name='component_expression_update'),
    
        url(r'^(?i)components/C(?P<concept_id>\d+)/expression/(?P<pk>\d+)/delete/$',
            ComponentExpression.ComponentExpressionDelete.as_view(),
            name='component_expression_delete'),
    ]
    
#======== code list component ==============================================================================
# urlConf for code list component
urlpatterns += [    
    url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
        ComponentExpression.component_history_expressionselect_detail_combined,
        name='component_history_expressionselect_detail'),
    
#     url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
#         ComponentExpression.ComponentExpressionSelectDetail.as_view(),
#         name='component_expressionselect_detail'),

#     url(r'^(?i)components/C(?P<concept_id>\d+)/version/(?P<concept_history_id>\d+)/historycomponent/(?P<component_history_id>\d+)/expressionselect/(?P<pk>\d+)/detail/$',
#         ComponentExpression.component_history_expressionselect_detail,
#         name='component_history_expressionselect_detail'),

   
   url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/search/$',
        ComponentExpression.component_expressionselect_search_codes,
        name='component_expressionselect_search_codes'),

    url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/(?P<code_list_id>\d+)/codes/$',
        ComponentExpression.component_expressionselect_codes,
        name='component_expressionselect_codes'),

]

if not settings.CLL_READ_ONLY: 
    urlpatterns += [
        url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/create/$',
            ComponentExpression.ComponentExpressionSelectCreate.as_view(),
            name='component_expressionselect_create'),
    
        url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/update/$',
            ComponentExpression.ComponentExpressionSelectUpdate.as_view(),
            name='component_expressionselect_update'),
    
#         url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/(?P<code_list_id>\d+)/code/create/$',
#             ComponentExpression.ComponentExpressionSelectCodeCreate.as_view(),
#             name='component_expressionselect_code_create'),
    
        url(r'^(?i)components/C(?P<concept_id>\d+)/expressionselect/(?P<pk>\d+)/delete/$',
            ComponentExpression.ComponentExpressionSelectDelete.as_view(),
            name='component_expressionselect_delete'),

    ]
 
#======== change password ==============================================================================
# use Django form
urlpatterns += [
    url('^change-password/$', 
        auth_views.password_change, 
        {'post_change_redirect': 'concept_library_home'},
        name='password_change'),
    ]

#======== Check concurrent update =======================================================================
if not settings.CLL_READ_ONLY: 
    # for Ajax
    urlpatterns += [
        url(r'^(?i)concepts/C(?P<pk>\d+)/check_concurrent_concept_update/$',
            Concept.check_concurrent_concept_update,
            name='check_concurrent_concept_update'),
    
    ]

#======== Publish Concept =========================================================================
if settings.ENABLE_PUBLISH:
    urlpatterns += [
        url(r'^(?i)concepts/C(?P<pk>\d+)/(?P<concept_history_id>\d+)/publish/$',
            Concept.ConceptPublish.as_view(),
            name='concept_publish'),
        
        url(r'^(?i)phenotypes/PH(?P<pk>\d+)/(?P<phenotype_history_id>\d+)/publish/$',
            Phenotype.PhenotypePublish.as_view(),
            name='phenotype_publish'),
    ]
    

    
# handler400 = 'clinicalcode.views.bad_request'
# handler403 = 'clinicalcode.views.permission_denied'
# handler404 = 'clinicalcode.views.page_not_found'
# handler500 = 'clinicalcode.views.server_error'
