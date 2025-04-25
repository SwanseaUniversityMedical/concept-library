from django import forms
from django.contrib.auth import get_user_model

from ..models.EntityClass import EntityClass

User = get_user_model()

class EntityAdminForm(forms.ModelForm):
    """
        excludes the created_by field so that the request.user who creates/updates this form is set as the
        created_by User()
    """

    class Meta:
        model = EntityClass
        fields = '__all__'
        exclude = ['created_by', 'created', 'modified_by', 'modified']
    
    def clean_created_by(self):
        if not self.cleaned_data['created_by']:
            return User()
        return self.cleaned_data['created_by']
    
    def clean_modified_by(self):
        if not self.cleaned_data['modified_by']:
            return User()
        return self.cleaned_data['modified_by']
