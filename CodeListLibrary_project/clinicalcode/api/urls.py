'''
    --------------------------------------------------------------------------
    URLs
    URL routing for the API.
    --------------------------------------------------------------------------
'''
from django.conf.urls import url, include
from rest_framework import routers
#from . import views
#from cll import settings
from django.conf import settings
from views import (View, Concept, WorkingSet, Phenotype, DataSource)
 
'''
Use the default REST API router to access the API details explicitly.
These paths will appear as links on the API page.
'''
router = routers.DefaultRouter()
router.register('concepts-live', Concept.ConceptViewSet)
router.register('codes', Concept.CodeViewSet)
router.register('tags', View.TagViewSet)


'''
Paths which are available as REST API URLs. The router URLs listed above can
be included via an include().
'''
urlpatterns = [
    url(r'^$', View.customRoot),    
    url(r'^', include(router.urls)),

    # ---  concepts  ------------------------------------------      
    url(r'^export_concept_codes/(?P<pk>[0-9]+)/$'
        , Concept.export_concept_codes
        , name='api_export_concept_codes'),
    
    url(r'^export_concept_codes_byVersionID/(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/$'
        , Concept.export_concept_codes_byVersionID
        , name='api_export_concept_codes_byVersionID'),
      
    # only superuser - under testing
    url(r'^childconcepts/(?P<pk>[0-9]+)/$'
        , Concept.child_concepts
        , name='api_child_concepts'),
    
    # only superuser - under testing
    url(r'^parentconcepts/(?P<pk>[0-9]+)/$'
        , Concept.parent_concepts
        , name='api_parent_concepts'),
    
    
    # search my concepts
    url(r'^myconcepts/$'
        , Concept.myConcepts
        , name='myConcepts'),

       
    # concepts_live_and_published
    url(r'^concepts/$'
        , Concept.concepts_live_and_published
        , name='concepts_live_and_published'),
    
    # my concept detail
    # if only concept_id is provided, get the latest version
    url(r'^myconcept-detail/(?P<pk>[0-9]+)/$'
        , Concept.myConcept_detail
        , name='myConceptdetail'),
    # get specific version
    url(r'^myconcept-detail/(?P<pk>[0-9]+)/version/(?P<concept_history_id>\d+)/$'
        , Concept.myConcept_detail
        , name='myConceptdetail_version'),
    
    
    # ---  working sets  ------------------------------------------      
    
    url(r'^export_workingset_codes/(?P<pk>[0-9]+)/$'
        , WorkingSet.export_workingset_codes
        , name='api_export_workingset_codes'),

    url(r'^export_workingset_codes_byVersionID/(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/$'
        , WorkingSet.export_workingset_codes_byVersionID
        , name='api_export_workingset_codes_byVersionID'),    
        
    
    
    # search my working sets
    url(r'^myworkingsets/$'
        , WorkingSet.myWorkingSets
        , name='myWorkingSets'),
    
    # my working set detail
    # if only workingset_id is provided, get the latest version
    url(r'^myworkingset-detail/(?P<pk>[0-9]+)/$'
        , WorkingSet.myWorkingset_detail
        , name='myWorkingsetdetail'),
    # get specific version
    url(r'^myworkingset-detail/(?P<pk>[0-9]+)/version/(?P<workingset_history_id>\d+)/$'
        , WorkingSet.myWorkingset_detail
        , name='myWorkingsetdetail_version'),    
    
    
    # --- phenotypes   ----------------------------------------------
    
    url(r'^export_phenotype_codes_byVersionID/(?P<pk>\d+)/version/(?P<phenotype_history_id>\d+)/$'
        , Phenotype.export_phenotype_codes_byVersionID
        , name='api_export_phenotype_codes_byVersionID'),
]


#======== Concept/Working set create/update ===================
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^api_concept_create/$'
            , Concept.api_concept_create
            , name='api_concept_create'),           

        url(r'^api_concept_update/$'
            , Concept.api_concept_update
            , name='api_concept_update'),   
                
        
        url(r'^api_workingset_create/$'
            , WorkingSet.api_workingset_create
            , name='api_workingset_create'),
        
        url(r'^api_workingset_update/$'
            , WorkingSet.api_workingset_update
            , name='api_workingset_update'),
        
        url(r'^api_phenotype_create/$',
            Phenotype.api_phenotype_create,
            name='api_phenotype_create'),
        
        url(r'^api_phenotype_update/$',
            Phenotype.api_phenotype_update,
            name='api_phenotype_update'),

        url(r'^api_datasource_create/$',
            DataSource.api_datasource_create,
            name='api_datasource_create')
    ]
    
    
#======== Publish Concept =====================================
if settings.ENABLE_PUBLISH:
    urlpatterns += [
        url(r'^export_published_concept_codes/(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/$'
        , Concept.export_published_concept_codes
        , name='api_export_published_concept_codes'),
      
      
        url(r'^publishedconcepts/$'
            , Concept.get_all_published_concepts 
            , name='api_get_all_published_concepts'),
    
#         url(r'^publishedconceptcodes/(?P<version_id>[0-9]+)/$'
#             , Concept.published_concept_codes
#             , name='api_published_concept_codes'),
        
        url(r'^publishedconcept/(?P<version_id>[0-9]+)/$'
            , Concept.published_concept
            , name='api_published_concept'),
    
        url(r'^export_published_phenotype_codes/(?P<pk>\d+)/version/(?P<phenotype_history_id>\d+)/$'
            , Phenotype.export_published_phenotype_codes
            , name='api_export_published_phenotype_codes'),
    ]
        






