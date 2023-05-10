from rest_framework import serializers

from ..models import ClinicalConcept

class ClinicalConceptSerializer(serializers.ModelSerializer):
    '''
        Will be used for serialisation of Concepts for API, Forms and Detail
    '''
    class Meta:
        model = ClinicalConcept
        fields = '__all__'
    
    def to_representation(self, instance):
        data = super(ClinicalConceptSerializer, self).to_representation(instance)
        return data
