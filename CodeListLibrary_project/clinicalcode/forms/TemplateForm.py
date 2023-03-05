from django import forms
from ..models.Template import Template

class TemplateAdminForm(forms.ModelForm):
  '''
    TemplateAdminForm
      @desc adds a checkbox item to the admin form to forcefully update the JSONB field order
            otherwise, ignores order update(s)

  '''
    update_order = forms.BooleanField(required=False)

    class Meta:
      model = Template
      fields = '__all__'
