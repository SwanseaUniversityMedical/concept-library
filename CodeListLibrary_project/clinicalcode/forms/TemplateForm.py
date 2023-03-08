import json
from django import forms
from django.contrib import admin

from ..models.Template import Template
from ..entity_utils import template_utils

class PrettyPrintOrderedDefinition(json.JSONEncoder):
    '''
        PrettyPrintOrderedDefinition
            @desc Indents and prettyprints the definition field so that it's readable
                  Preserves order that was given by template_utils.get_ordered_definition
    '''
    def __init__(self, *args, indent, sort_keys, **kwargs):
        super().__init__(*args, indent=2, sort_keys=False, **kwargs)

class TemplateAdminForm(forms.ModelForm):
    '''
        TemplateAdminForm
            @desc overrides the Django form to reorder the 'layout_field' and 'order' fields
                  within the template definition
    '''
    template_version = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly':'readonly'}))
    definition = forms.JSONField(encoder=PrettyPrintOrderedDefinition)

    def __init__(self, *args, **kwargs):
        super(TemplateAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.initial['definition'] = template_utils.get_ordered_definition(instance.definition, clean_fields=True)

    class Meta:
        model = Template
        fields = '__all__'
