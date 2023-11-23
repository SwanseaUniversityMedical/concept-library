from django import forms

import json

from ..models.Template import Template
from ..entity_utils import template_utils

class PrettyPrintOrderedDefinition(json.JSONEncoder):
    """
        Indents and prettyprints the definition field so that it's readable
        Preserves order that was given by template_utils.get_ordered_definition
    """
    def __init__(self, *args, indent, sort_keys, **kwargs):
        super().__init__(*args, indent=2, sort_keys=False, **kwargs)

class TemplateAdminForm(forms.ModelForm):
    """
        Template form to override behaviour to meet requirements of:
            1. Render the JSON definition of a template as described by its 'layout_field' and 'order' fields
            
            2. On submission, update the [name] and [description] fields to reflect the template's JSON definition
    """
    name = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)
    description = forms.CharField(widget=forms.Textarea(attrs={'readonly': 'readonly'}), required=False)
    template_version = forms.IntegerField(widget=forms.NumberInput(attrs={'readonly':'readonly'}))
    definition = forms.JSONField(encoder=PrettyPrintOrderedDefinition)

    def __init__(self, *args, **kwargs):
        super(TemplateAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # apply name/desc from template definition if available
            if isinstance(instance.definition, dict):
                details = instance.definition.get('template_details')
                if details is not None:
                    self.initial['name'] = details.get('name', '')
                    self.initial['description'] = details.get('description', '')
            
            # reorder the template
            self.initial['definition'] = template_utils.get_ordered_definition(instance.definition, clean_fields=True)

    def clean(self):
        data = self.cleaned_data
        
        # apply name/desc from definition if available
        definition = data.get('definition')
        if isinstance(definition, dict):
            details = definition.get('template_details')
            if details is not None:
                data['name'] = details.get('name', '')
                data['description'] = details.get('description', '')
        
        return data


    class Meta:
        model = Template
        fields = '__all__'