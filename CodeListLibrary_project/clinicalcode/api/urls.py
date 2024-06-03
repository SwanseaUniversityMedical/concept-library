from django.conf import settings
from django.urls import re_path as url
from django.urls import include
from rest_framework import routers
from rest_framework import permissions
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import (
  Concept, GenericEntity,
  Template, DataSource,
  Tag, Collection, Ontology
)

""" Router
    Use the default REST API router to access the API details explicitly. These paths will 
      appear as links on the API page.
"""
router = routers.DefaultRouter()
#router.register('concepts-live', Concept.ConceptViewSet)
#router.register('codes', Concept.CodeViewSet)
#router.register('tags-and-collections', View.TagViewSet, basename='tags')
#router.register('public/data-sources-list', View.DataSourceViewSet)
#router.register('public/coding-systems', View.CodingSystemViewSet)

""" Swagger """

class SchemaGenerator(OpenAPISchemaGenerator):
    """
    
    """
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
    ),
    public = True,
    permission_classes = (permissions.AllowAny,),
    generator_class = SchemaGenerator,
)

""" Swagger urls """
urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)/$', 
        schema_view.without_ui(cache_timeout=0), 
        name='schema-json'),
    url(r'^swagger/$', 
        schema_view.with_ui('swagger', cache_timeout=0), 
        name='schema-swagger-ui')
]

if settings.IS_DEVELOPMENT_PC:
    urlpatterns += [
        url(r'^redoc/$', 
            schema_view.with_ui('redoc', cache_timeout=0), 
            name='schema-redoc'),
    ]

""" API urls """
urlpatterns += [
    # Swagger
    url(r'^$', schema_view.with_ui('swagger', cache_timeout=0), name='root'),
    url(r'^', include(router.urls)),

    # Templates
    url(r'^templates/$', 
        Template.get_templates,
        name='get_templates'),
    url(r'^templates/(?P<template_id>\d+)/detail/$', 
        Template.get_template,
        name='get_template_detail'),
    url(r'^templates/(?P<template_id>\d+)/version/(?P<version_id>\d+)/detail/$', 
        Template.get_template,
        name='get_template_detail_from_version'),
    url(r'^templates/(?P<template_id>\d+)/get-versions/$', 
        Template.get_template_version_history,
        name='get_template_version_history'),

    # GenericEnities (Phenotypes)
    url(r'^phenotypes/$',
        GenericEntity.get_generic_entities,
        name='get_generic_entities'),
    url(r'^phenotypes/(?P<phenotype_id>\w+)/detail/$',
        GenericEntity.get_entity_detail,
        name='get_generic_entity_detail'),
    url(r'^phenotypes/(?P<phenotype_id>PH\d+)/version/(?P<version_id>\d+)/detail/$',
        GenericEntity.get_entity_detail,
        name='get_generic_entity_detail_by_version'),
    url(r'^phenotypes/(?P<phenotype_id>\w+)/export/(?P<field>\w+)/$',
        GenericEntity.get_entity_detail,
        name='get_generic_entity_field'),
    url(r'^phenotypes/(?P<phenotype_id>\w+)/version/(?P<version_id>\d+)/export/(?P<field>\w+)/$',
        GenericEntity.get_entity_detail,
        name='get_generic_entity_field_by_version'),
    url(r'^phenotypes/(?P<phenotype_id>\w+)/get-versions/$',
        GenericEntity.get_generic_entity_version_history,
        name='get_generic_entity_versions'),
    
    # Concepts
    url(r'^concepts/$', 
        Concept.get_concepts, 
        name='concepts'),
    url(r'^concepts/C(?P<concept_id>\d+)/detail/$',
        Concept.get_concept_detail,
        name='api_concept_detail'),
    url(r'^concepts/C(?P<concept_id>\d+)/version/(?P<version_id>\d+)/detail/$',
        Concept.get_concept_detail,
        name='api_concept_detail_version'),
    url(r'^concepts/C(?P<concept_id>\d+)/export/codes/$',
        Concept.get_concept_detail, 
        { 'export_codes': True },
        name='api_export_concept_codes'),
    url(r'^concepts/C(?P<concept_id>\d+)/version/(?P<version_id>\d+)/export/codes/$',
        Concept.get_concept_detail,
        { 'export_codes': True },
        name='api_export_concept_codes_byVersionID'),
    url(r'^concepts/C(?P<concept_id>\d+)/get-versions/$',
        Concept.get_concept_version_history,
        name='get_concept_versions'),

    # Datasources
    url(r'^data-sources/$', 
        DataSource.get_datasources, 
        name='data_sources'),
    url(r'^data-sources/(?P<datasource_id>[\w-]+)/detail/$',
        DataSource.get_datasource_detail,
        name='data_source_by_id'),

    # Tags
    url(r'^tags/$',
        Tag.get_tags,
        name='tag_list'),
    url(r'^tags/(?P<tag_id>\d+)/detail/$',
        Tag.get_tag_detail,
        name='tag_list_by_id'),

    # Collections
    url(r'^collections/$',
        Collection.get_collections,
        name='collection_list'),
    url(r'^collections/(?P<collection_id>\d+)/detail/$',
        Collection.get_collection_detail,
        name='collections_list_by_id'),

    # Ontology
    url(r'^ontology/$',
        Ontology.get_ontologies,
        name='ontology_list'),
    url(r'^ontology/type/(?P<ontology_id>\d+)/$',
        Ontology.get_ontology_detail,
        name='ontology_list_by_type'),
    url(r'^ontology/node/$',
        Ontology.get_ontology_nodes,
        name='ontology_nodes'),
    url(r'^ontology/node/(?P<node_id>\d+)/$',
        Ontology.get_ontology_node,
        name='ontology_node_by_id'),
]

""" Create/Update urls """
if not settings.CLL_READ_ONLY:
    urlpatterns += [
        # GenericEntities (Phenotypes)
        url(r'^phenotypes/create/$',
            GenericEntity.create_generic_entity,
            name='create_generic_entity'),
        url(r'^phenotypes/update/$',
            GenericEntity.update_generic_entity,
            name='update_generic_entity'),
    ]
