'''
    ---------------------------------------------------------------------------
    COMPONENT FORMS

    Form definition for the Components.
    ---------------------------------------------------------------------------
'''

from django import forms
# !!! from simple_history.models import HistoricalRecords

from ..models.Component import Component
from ..models.Concept import Concept


class ComponentForm(forms.ModelForm):
    '''
        Components are parts of a concept. Each component may contain codes
        which are to be added to or removed from a code-list.
    '''
    comment = forms.CharField(
        label='Comment:',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        required=False
    )
    component_type = forms.CharField(widget=forms.HiddenInput())
    concept = forms.ModelChoiceField(queryset=Concept.objects.all(),
        widget=forms.HiddenInput())
    concept_ref = forms.ModelChoiceField(queryset=Concept.objects.all(),
        required=False,
        widget=forms.HiddenInput())
    # ------
    # !!! Changing the form field for the concept_ref_history_id so that it
    #     uses just the integer ID value not a choice field of all the objects.
    #     Modified choice field that works follows (commented out) as well as
    #     the original code.
    concept_ref_history = forms.ModelChoiceField(queryset=Concept.history.all(),#.values_list('id' , flat=True),
        required=False,
        widget=forms.HiddenInput())
        
#     concept_ref_history_id = forms.IntegerField(required=False,
#         widget=forms.HiddenInput())
    #concept_ref_history = forms.ModelChoiceField(queryset=Concept.history.all(),
    #    required=False, widget=forms.HiddenInput())
    ## concept_ref_history = forms.ChoiceField(queryset=Concept.objects.all(),
    ##    required=False, widget=forms.HiddenInput())
    # ------
    logical_type = forms.ChoiceField(
        label='Type:',
        widget=forms.RadioSelect(),
        choices=Component.LOGICAL_TYPES,
        initial=Component.LOGICAL_TYPES[0][0]
    )
    name = forms.CharField(
        label='Name:',
        help_text='250 max characters',
        required=True,
        error_messages={'required': 'Please enter a name'},
        max_length=250,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'data-required': 'Please enter a name',
            'autofocus': 'autofocus'})
    )

    class Meta:
        '''
            Class metadata (anything that's not a field).
        '''
        model = Component
        exclude = ['created_by', 'modified_by']
