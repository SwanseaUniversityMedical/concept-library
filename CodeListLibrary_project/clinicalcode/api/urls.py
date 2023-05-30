'''
    --------------------------------------------------------------------------
    URLs
    URL routing for the API.
    --------------------------------------------------------------------------
'''
from clinicalcode.views import View as cc_view
#from . import views
#from cll import settings
from django.conf import settings
#from django.conf.urls import include, url
from django.urls import re_path as url
from django.urls import include
from rest_framework import routers

from .views import Concept, DataSource, Phenotype, View, WorkingSet, PhenotypeWorkingSet, GenericEntity, Template

from rest_framework import permissions
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
#import os
from django.utils.decorators import method_decorator


'''
Use the default REST API router to access the API details explicitly.
These paths will appear as links on the API page.
'''
router = routers.DefaultRouter()
router.register('concepts-live', Concept.ConceptViewSet)
router.register('codes', Concept.CodeViewSet)
router.register('tags-and-collections', View.TagViewSet, basename='tags')
router.register('public/data-sources-list', View.DataSourceViewSet)
router.register('public/coding-systems', View.CodingSystemViewSet)

urlpatterns = []

###########################################################################
# Swagger

class SchemaGenerator(OpenAPISchemaGenerator):
    #@method_decorator(View.robots())  
    def get_schema(self, request=None, public=False):
        schema = super(SchemaGenerator, self).get_schema(request, public)
        schema.basePath = request.path.replace('swagger/', '')
        if settings.IS_DEVELOPMENT_PC or settings.IS_INSIDE_GATEWAY:
            schema.schemes = ["http", "https"]
        else:
            schema.schemes = ["https"] 
        return schema

            
schema_view = get_schema_view(
                              openapi.Info(
                                            title = settings.SWAGGER_TITLE,
                                            default_version = "v1",
#                                           description = ""  #"description  ... goes here ...",
#                                           terms_of_service = "https://www.google.com/policies/terms/",
#                                           contact = openapi.Contact(email = "contact@snippets.local"),
#                                           license = openapi.License(name = "BSD License"),                          
                                            ),
                                public = True,
                                permission_classes = (permissions.AllowAny,),#(permissions.IsAuthenticated,),
                                # urlconf = "clinicalcode.api.urls",
                                # url =  "http://conceptlibrary.saildatabank.com/",
                                # validators = ['flex', 'ssv'],
                                # patterns  =  [],
                                generator_class = SchemaGenerator,
                            )


urlpatterns += [
    url(r'^swagger(?P<format>\.json|\.yaml)/$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

if settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
        url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]    
###########################################################################


'''
Paths which are available as REST API URLs. The router URLs listed above can
be included via an include().
'''
urlpatterns += [
    url(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='root'),
    url(r'^', include(router.urls)),

    
    #----------------------------------------------------------
    # ---  concepts  ------------------------------------------
    #----------------------------------------------------------
    url(r'^concepts/C(?P<pk>\d+)/export/codes/$',
        Concept.export_concept_codes,
        name='api_export_concept_codes'),
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/export/codes/$',
        Concept.export_concept_codes_byVersionID,
        name='api_export_concept_codes_byVersionID'),
    url(r'^public/concepts/C(?P<pk>\d+)/export/codes/$',
        Concept.export_published_concept_codes,
        name='api_export_published_concept_codes_latestVersion'),
    url(r'^public/concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/export/codes/$',
        Concept.export_published_concept_codes,
        name='api_export_published_concept_codes'),    

    #===============================================
    # only superuser - under testing
    url(r'^concepts/C(?P<pk>\d+)/childconcepts/$',
        Concept.child_concepts,
        name='api_child_concepts'),

    # only superuser - under testing
    url(r'^parentconcepts/C(?P<pk>\d+)/$',
        Concept.parent_concepts,
        name='api_parent_concepts'),

    # concepts_live_and_published  used for internal search for concepts (not useful for external api user)
    url(r'^concept-search/$',
        Concept.concepts_live_and_published,
        name='concepts_live_and_published'),

    #==== search concepts/published concepts =======
    # search user concepts
    url(r'^concepts/$', Concept.user_concepts, name='concepts'),
    url(r'^concepts/C(?P<pk>\d+)/$',
        Concept.user_concepts,
        name='concept_by_id'),

    # search published concepts
    url(r'^public/concepts/$',
        Concept.published_concepts,
        name='api_published_concepts'),
    url(r'^public/concepts/C(?P<pk>\d+)/$',
        Concept.published_concepts,
        name='api_published_concept_by_id'),
    #================================================

    # get concept detail
    # if only concept_id is provided, get the latest version
    url(r'^concepts/C(?P<pk>\d+)/detail/$',
        Concept.concept_detail,
        name='api_concept_detail'),
    url(r'^public/concepts/C(?P<pk>\d+)/detail/$',
        Concept.concept_detail_PUBLIC,
        name='api_concept_detail_public'),

    # get specific version
    url(r'^concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/detail/$',
        Concept.concept_detail,
        name='api_concept_detail_version'),
    url(r'^public/concepts/C(?P<pk>\d+)/version/(?P<concept_history_id>\d+)/detail/$',
        Concept.concept_detail_PUBLIC,
        name='api_concept_detail_version_public'),

    # show versions
    url(r'^concepts/C(?P<pk>\d+)/get-versions/$',
        Concept.concept_detail, {'get_versions_only': '1'},
        name='get_concept_versions'),
    url(r'^public/concepts/C(?P<pk>\d+)/get-versions/$',
        Concept.concept_detail_PUBLIC, {'get_versions_only': '1'},
        name='get_concept_versions_public'),

    #----------------------------------------------------------
    # ---  working sets  --------------------------------------
    #----------------------------------------------------------
    url(r'^workingsets/WS(?P<pk>\d+)/export/codes/$',
        WorkingSet.export_workingset_codes,
        name='api_export_workingset_codes'),
    url(r'^workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
        WorkingSet.export_workingset_codes_byVersionID,
        name='api_export_workingset_codes_byVersionID'),

    # search my working sets
    url(r'^workingsets/$', WorkingSet.workingsets, name='workingsets'),
    url(r'^workingsets/WS(?P<pk>\d+)/$',
        WorkingSet.workingsets,
        name='workingset_by_id'),

    # my working set detail
    # if only workingset_id is provided, get the latest version
    url(r'^workingsets/WS(?P<pk>\d+)/detail/$',
        WorkingSet.workingset_detail,
        name='api_workingset_detail'),
    # get specific version
    url(r'^workingsets/WS(?P<pk>\d+)/version/(?P<workingset_history_id>\d+)/detail/$',
        WorkingSet.workingset_detail,
        name='api_workingset_detail_version'),

    # show versions
    url(r'^workingsets/WS(?P<pk>\d+)/get-versions/$',
        WorkingSet.workingset_detail, {'get_versions_only': '1'},
        name='get_workingset_versions'),

    #----------------------------------------------------------
    # --- phenotypes   ----------------------------------------
    #----------------------------------------------------------
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/export/codes/$',
    #     GenericEntity.get_entity_detail, { 'field': 'codes' },
    #     name='api_export_phenotype_codes_latestVersion'),
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/version/(?P<historical_id>\d+)/export/codes/$',
    #     GenericEntity.get_entity_detail, { 'field': 'codes' },
    #     name='api_export_phenotype_codes_byVersionID'),
        
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/export/codes/$',
    #     GenericEntity.get_entity_detail, { 'field': 'codes' },
    #     name='api_export_published_phenotype_codes_latestVersion'),
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/version/(?P<historical_id>\d+)/export/codes/$',
    #     GenericEntity.get_entity_detail, { 'field': 'codes' },
    #     name='api_export_published_phenotype_codes'),

    # #==== search concepts/published phenotypes =====
    # url(r'^phenotypes/$', 
    #     GenericEntity.get_generic_entities, { 'should_paginate': False },
    #     name='phenotypes'),
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/$', 
    #     GenericEntity.get_entity_detail, 
    #     name='phenotype_by_id'),

    # # search published phenotypes
    # url(r'^public/phenotypes/$',
    #     GenericEntity.get_generic_entities, { 'should_paginate': False },
    #     name='api_published_phenotypes'),
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/$',
    #     GenericEntity.get_entity_detail, 
    #     name='api_published_phenotype_by_id'),
    # #===============================================

    # # my phenotype detail
    # # if only phenotype_id is provided, get the latest version
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/detail/$',
    #     GenericEntity.get_entity_detail, 
    #     name='api_phenotype_detail'),
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/detail/$',
    #     GenericEntity.get_entity_detail, 
    #     name='api_phenotype_detail_public'),

    # # get specific version
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/version/(?P<historical_id>\d+)/detail/$',
    #     GenericEntity.get_entity_detail, 
    #     name='api_phenotype_detail_version'),
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/version/(?P<historical_id>\d+)/detail/$',
    #     GenericEntity.get_entity_detail, 
    #     name='api_phenotype_detail_version_public'),

    # # show versions
    # url(r'^phenotypes/(?P<primary_key>PH\d+)/get-versions/$',
    #     GenericEntity.get_generic_entity_version_history,
    #     name='get_phenotype_versions'),
    # url(r'^public/phenotypes/(?P<primary_key>PH\d+)/get-versions/$',
    #     GenericEntity.get_generic_entity_version_history,
    #     name='get_phenotype_versions_public'),

    # ---------------------------------------------------------
    # ---  data sources  --------------------------------------
    #----------------------------------------------------------

    #==== search data sources =====
    url(r'^data-sources/$', DataSource.data_sources, name='data_sources'),
    url(r'^data-sources/(?P<pk>\d+)/$',
        DataSource.data_sources,
        name='data_source_by_id'),

    # public
    url(r'^public/data-sources/$',
        DataSource.published_data_sources, {'show_published_data_only': True},
        name='data_sources_public'),
    url(r'^public/data-sources/(?P<pk>\d+)/$',
        DataSource.published_data_sources, {'show_published_data_only': True},
        name='data_source_by_id_public'),

    # only get live phenotypes
    url(r'^data-sources/live/$',
        DataSource.data_sources, {'get_live_phenotypes': True},
        name='data_sources_live'),
    url(r'^data-sources/live/(?P<pk>\d+)/$',
        DataSource.data_sources, {'get_live_phenotypes': True},
        name='data_source_live_by_id'),

    # only get live published phenotypes
    url(r'^public/data-sources/live/$',
        DataSource.published_data_sources, {
            'get_live_phenotypes': True,
            'show_published_data_only': True
        },
        name='data_sources_live_public'),
    url(r'^public/data-sources/live/(?P<pk>\d+)/$',
        DataSource.published_data_sources, {
            'get_live_phenotypes': True,
            'show_published_data_only': True
        },
        name='data_source_live_by_id_public'),
    
    
    # ---------------------------------------------------------
    # ---  tags / collections  --------------------------------
    #----------------------------------------------------------
    # public tags
    url(r'^public/tags/$',
        View.getTagsOrCollections, {'tag_type': 1},
        name='tag_list_public'),
    url(r'^public/tags/(?P<pk>\d+)/$',
        View.getTagsOrCollections, {'tag_type': 1},
        name='tag_list_by_id_public'),
    
    # public collections
    url(r'^public/collections/$',
        View.getTagsOrCollections, {'tag_type': 2},
        name='collection_list_public'),
    url(r'^public/collections/(?P<pk>\d+)/$',
        View.getTagsOrCollections, {'tag_type': 2},
        name='collections_list_by_id_public'),
    
]       
        
    #----------------------------------------------------------
    # --- phenotype-working set   -----------------------------
    #----------------------------------------------------------
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
    # search
    url(r'^phenotypeworkingsets/$', PhenotypeWorkingSet.phenotypeworkingsets, name='phenotypeworkingsets'),
    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/$',
        PhenotypeWorkingSet.phenotypeworkingsets,
        name='api_phenotypeworkingset_by_id'),
    
    # public search
    url(r'^public/phenotypeworkingsets/$',
        PhenotypeWorkingSet.published_phenotypeworkingsets,
        name='api_published_phenotypeworkingset'),
    url(r'^public/phenotypeworkingsets/(?P<pk>WS\d+)/$',
        PhenotypeWorkingSet.published_phenotypeworkingsets,
        name='api_published_phenotypeworkingset_by_id'),
    
    # details
    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/detail/$',
        PhenotypeWorkingSet.phenotypeworkingset_detail,
        name='api_phenotypeworkingset_detail'),
    url(r'^public/phenotypeworkingsets/(?P<pk>WS\d+)/detail/$',
        PhenotypeWorkingSet.phenotypeworkingset_detail_PUBLIC,
        name='api_phenotypeworkingset_detail_public'),

    # get specific version
    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/detail/$',
        PhenotypeWorkingSet.phenotypeworkingset_detail,
        name='api_phenotypeworkingset_detail_version'),

    # show versions
    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/get-versions/$',
        PhenotypeWorkingSet.phenotypeworkingset_detail, {'get_versions_only': '1'},
        name='get_phenotypeworkingset_versions'),

    # coding
    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/export/codes/$',
        PhenotypeWorkingSet.export_phenotypeworkingset_codes_byVersionID,
        name='api_export_phenotypeworkingset_codes_latestVersion'),

    url(r'^phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
        PhenotypeWorkingSet.export_phenotypeworkingset_codes_byVersionID,
        name='api_export_phenotypeworkingset_codes_byVersionID'),
        
    url(r'^public/phenotypeworkingsets/(?P<pk>WS\d+)/export/codes/$',
        PhenotypeWorkingSet.export_published_phenotypeworkingset_codes,
        name='api_export_published_phenotypeworkingset_codes_latestVersion'),

    url(r'^public/phenotypeworkingsets/(?P<pk>WS\d+)/version/(?P<workingset_history_id>\d+)/export/codes/$',
        PhenotypeWorkingSet.export_published_phenotypeworkingset_codes,
        name='api_export_published_phenotypeworkingset_codes'),
]

#======== Concept/Working set/Phenotye create/update ===================
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        url(r'^api_concept_create/$',
            Concept.api_concept_create,
            name='api_concept_create'),
        url(r'^api_concept_update/$',
            Concept.api_concept_update,
            name='api_concept_update'),
        url(r'^api_workingset_create/$',
            WorkingSet.api_workingset_create,
            name='api_workingset_create'),
        url(r'^api_workingset_update/$',
            WorkingSet.api_workingset_update,
            name='api_workingset_update'),
        url(r'^api_phenotype_create/$',
            Phenotype.api_phenotype_create,
            name='api_phenotype_create'),
        url(r'^api_phenotype_update/$',
            Phenotype.api_phenotype_update,
            name='api_phenotype_update'),
        url(r'^api_datasource_create/$',
            DataSource.api_datasource_create,
            name='api_datasource_create'),
        ]
    
    if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
        urlpatterns += [
            url(r'^api_phenotypeworkingset_create/$',
                PhenotypeWorkingSet.api_phenotypeworkingset_create,
                name='api_phenotypeworkingset_create'),
            url(r'^api_phenotypeworkingset_update/$',
                PhenotypeWorkingSet.api_phenotypeworkingset_update,
                name='api_phenotypeworkingset_update'),
        ]

############################################################################
############################################################################
# ****************   Generic Entity API   **********************************
############################################################################
############################################################################
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
        # List all entities
        url(r'^phenotypes/$',
            GenericEntity.get_generic_entities,
            name='api_generic_entity'),

        # Generic entity detail
        url(r'^phenotypes/(?P<primary_key>\w+)/detail/$',
            GenericEntity.get_entity_detail,
            name='api_generic_entity_detail'),

        # Get specific entity version
        url(r'^phenotypes/(?P<primary_key>PH\d+)/version/(?P<historical_id>\d+)/detail/$',
            GenericEntity.get_entity_detail,
            name='api_generic_entity_detail_by_version'),

        # Export specific entity field
        url(r'^phenotypes/(?P<primary_key>\w+)/export/(?P<field>\w+)/$',
            GenericEntity.get_entity_detail,
            name='get_generic_entity_field'),

        # Export specific entity field from specific entity version
        url(r'^phenotypes/(?P<primary_key>\w+)/version/(?P<historical_id>\d+)/export/(?P<field>\w+)/$',
            GenericEntity.get_entity_detail,
            name='get_generic_entity_field_by_version'),

        # Show entity versions
        url(r'^phenotypes/(?P<primary_key>\w+)/get-versions/$',
            GenericEntity.get_generic_entity_version_history,
            name='get_generic_entity_versions'),

        # Create entity
        url(r'^phenotypes/create/$',
            GenericEntity.create_generic_entity,
            name='create_generic_entity'),

        # Update entity
        url(r'^phenotypes/update/$',
            GenericEntity.update_generic_entity,
            name='update_generic_entity'),

        # Get templates
        url(r'^templates/$', 
            Template.get_templates,
            name='get_templates'),

        # Get template versions
        url(r'^templates/(?P<primary_key>\d+)/get-versions/$', 
            Template.get_template_version_history,
            name='get_template_version_history'),

        # Get template detail
        url(r'^templates/(?P<primary_key>\d+)/detail/$', 
            Template.get_template,
            name='get_template_detail'),

        # Get template detail with history
        url(r'^templates/(?P<primary_key>\d+)/version/(?P<history_id>\d+)/detail/$', 
            Template.get_template,
            name='get_template_detail_from_version'),
    ]

####### M Elmessary ################
if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
    # generic entity detail
    # if only id is provided, get the latest version
    url(r'^ge0/(?P<pk>\w+)/detail/$',
        GenericEntity.generic_entity_detail,
        name='api_generic_entity_detail'),
    url(r'^public/ge0/(?P<pk>\w+)/detail/$',
        GenericEntity.generic_entity_detail_PUBLIC,
        name='api_generic_entity_detail_public'),

    # get specific version
    url(r'^ge0/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$',
        GenericEntity.generic_entity_detail,
        name='api_generic_entity_detail_version'),
    url(r'^public/ge0/(?P<pk>\w+)/version/(?P<history_id>\d+)/detail/$',
        GenericEntity.generic_entity_detail_PUBLIC,
        name='api_generic_entity_detail_version_public'),

    # show versions
    url(r'^ge0/(?P<pk>\w+)/get-versions/$',
        GenericEntity.generic_entity_detail, {'get_versions_only': '1'},
        name='get_generic_entity_versions'),
    url(r'^public/ge0/(?P<pk>\w+)/get-versions/$',
        GenericEntity.generic_entity_detail_PUBLIC, {'get_versions_only': '1'},
        name='get_generic_entity_versions_public'),
    
        #----------------------------------------------------------
    url(r'^ge0/(?P<pk>\w+)/export/codes/$',
        GenericEntity.export_phenotype_codes_byVersionID,
        name='ge_api_export_phenotype_codes_latestVersion'),
    url(r'^ge0/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$',
        GenericEntity.export_phenotype_codes_byVersionID,
        name='ge_api_export_phenotype_codes_byVersionID'),
        
    url(r'^public/ge0/(?P<pk>\w+)/export/codes/$',
        GenericEntity.export_published_phenotype_codes,
        name='ge_api_export_published_phenotype_codes_latestVersion'),
    url(r'^public/ge0/(?P<pk>\w+)/version/(?P<history_id>\d+)/export/codes/$',
        GenericEntity.export_published_phenotype_codes,
        name='ge_api_export_published_phenotype_codes'),
    
    ]

#======== Generic Entity create/update ===================
if not settings.CLL_READ_ONLY:    
    if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC:
        urlpatterns += [
            url(r'^api_genericentity_create/$',
                GenericEntity.create_generic_entity,
                name='api_genericentity_create'),
            url(r'^api_genericentity_update/$',
                GenericEntity.update_generic_entity,
                name='api_genericentity_update'),
        ]    
    