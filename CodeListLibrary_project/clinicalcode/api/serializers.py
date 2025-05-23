'''
    ---------------------------------------------------------------------------
    Serializers
    Specifications of data content for serialisation of the data for API calls.
    The base class serializer allows serialisation to JSON, API or XML output.
    ---------------------------------------------------------------------------
'''
from rest_framework import serializers

from ..models import (Code, Concept, DataSource, Tag, CodingSystem)

class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = '__all__'


class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id', 'description', 'display', 'get_display_display', 'tag_type',
            'get_tag_type_display', 'collection_brand'
        )


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = (
            'id', 'name', 'uid', 'url', 'description', 'datasource_id'
        )


class CodingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingSystem
        fields = (
            'id', 'name', 'description', 'codingsystem_id'
        )
