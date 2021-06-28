'''
    ---------------------------------------------------------------------------
    Serializers
    Specifications of data content for serialisation of the data for API calls.
    The base class serializer allows serialisation to JSON, API or XML output.
    ---------------------------------------------------------------------------
'''
from rest_framework import serializers
from ..models import Concept, Component, CodeRegex, CodeList, Code, ConceptTagMap, Tag, WorkingSet, WorkingSetTagMap, DataSource


class ConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concept
        fields = '__all__'
    
     
class CodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Code
        #fields = ('id', 'code', 'description', 'code_list')
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'description', 'display', 'get_display_display'
                # ,  'created_by' , 'updated_by' 
                  )
                
class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ('id', 'name', 'uid', 'url', 'description'
                # ,  'created_by' , 'updated_by' 
                  )
                

        

# api/concepts/