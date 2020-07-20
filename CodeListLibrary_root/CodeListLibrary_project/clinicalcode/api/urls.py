'''
    --------------------------------------------------------------------------
    URLs
    URL routing for the API.
    --------------------------------------------------------------------------
'''
from django.conf.urls import url, include
from rest_framework import routers
from . import views
#from cll import settings
from django.conf import settings

'''
Use the default REST API router to access the API details explicitly.
These paths will appear as links on the API page.
'''
router = routers.DefaultRouter()
router.register('concepts', views.ConceptViewSet)
router.register('codes', views.CodeViewSet)
router.register('tags', views.TagViewSet)


'''
Paths which are available as REST API URLs. The router URLs listed above can
be included via an include().
'''
urlpatterns = [
    url(r'^$', views.customRoot),    
    url(r'^', include(router.urls)),

      
    url(r'^export_concept_codes/(?P<pk>[0-9]+)/$'
        , views.export_concept_codes
        , name='api_export_concept_codes'),
    
    url(r'^export_concept_codes_byVersionID/(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/$'
        , views.export_concept_codes_byVersionID
        , name='api_export_concept_codes_byVersionID'),
    
    
    url(r'^export_workingset_codes/(?P<pk>[0-9]+)/$'
        , views.export_workingset_codes
        , name='api_export_workingset_codes'),

    url(r'^export_workingset_codes_byVersionID/(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/$'
        , views.export_workingset_codes_byVersionID
        , name='api_export_workingset_codes_byVersionID'),    
    
    
    
    url(r'^childconcepts/(?P<pk>[0-9]+)/$'
        , views.child_concepts
        , name='api_child_concepts'),
    
    
    url(r'^parentconcepts/(?P<pk>[0-9]+)/$'
        , views.parent_concepts
        , name='api_parent_concepts'),
    
]


#======== Concept/Working set create/update ===================
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^api_concept_create/$'
            , views.api_concept_create
            , name='api_concept_create'),           

        url(r'^api_concept_update/$'
            , views.api_concept_update
            , name='api_concept_update'),   
                
        
        url(r'^api_workingset_create/$'
            , views.api_workingset_create
            , name='api_workingset_create'),
        
        url(r'^api_workingset_update/$'
            , views.api_workingset_update
            , name='api_workingset_update'),
        
 
    ]
    
    
#======== Publish Concept =====================================
if settings.ENABLE_PUBLISH:
    urlpatterns += [
        url(r'^publishedconcepts/$'
            , views.get_all_published_concepts 
            , name='api_get_all_published_concepts'),
    
        url(r'^publishedconceptcodes/(?P<version_id>[0-9]+)/$'
            , views.published_concept_codes
            , name='api_published_concept_codes'),
        
        url(r'^publishedconcept/(?P<version_id>[0-9]+)/$'
            , views.published_concept
            , name='api_published_concept'),
    
    ]
        






