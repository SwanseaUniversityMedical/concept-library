'''
    CodeForms
    
    The code forms used in the application.
'''
from django import forms
from django.forms.models import inlineformset_factory, ModelChoiceField

from ..models.Code import Code
from ..models.CodeList import CodeList
from ..models.CodeRegex import CodeRegex
from ..models.Component import Component
from django.forms.widgets import HiddenInput


class CodeForm(forms.ModelForm):
    code = forms.CharField(
        label='Code:',
        help_text='20 max characters',
        required=True,
        max_length=20,
        error_messages={'required': 'Please enter a code'},
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'please enter a code'})
    )
    description = forms.CharField(
        label='Descriptions:',
        help_text='510 max characters',
        required=True,
        max_length=510,
        error_messages={'required': 'Please enter a description'},
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'please enter a description'})
    )
    code_list = ModelChoiceField(queryset=CodeList.objects.all(),
                                 required=False,
                                 widget=HiddenInput())

    class Meta:
        model = Code
        fields = '__all__'


class CodeListForm(forms.ModelForm):
    component = forms.CharField(widget=forms.HiddenInput())
    description = forms.CharField(
        label='Code list descriptions:',
        help_text='250 max characters',
        required=True,
        max_length=250,
        error_messages={'required': 'Please enter a description'},
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'please enter a description'})
    )
    sql_rules = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = CodeList
        fields = '__all__'


class CodeRegexForm(forms.ModelForm):
    regex_type = forms.ChoiceField(
        label='Regex type:',
        widget=forms.RadioSelect(),
        choices=CodeRegex.REGEX_TYPE_CHOICES,
        initial=CodeRegex.REGEX_TYPE_CHOICES[0][0]
    )

    column_search = forms.ChoiceField(
        label='Column to search:',
        widget=forms.RadioSelect(),
        choices=CodeRegex.SEARCH_COLUMN_CHOICES,
        initial=CodeRegex.SEARCH_COLUMN_CHOICES[0][0]
    )
    
    case_sensitive_search = forms.BooleanField(
        label='case sensitive search:',
        widget=forms.CheckboxInput(attrs={'id': 'case_sensitive_search', 'name': 'case_sensitive_search'}),
        required=False
    )
    
    regex_code = forms.CharField(
        label='Pattern:',
        help_text='1000 max characters',
        max_length=1000,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    sql_rules = forms.CharField(required=False, widget=forms.HiddenInput())
    component = forms.CharField(widget=forms.HiddenInput())
    code_list = ModelChoiceField(queryset=CodeList.objects.all(),
                                 required=False,
                                 widget=HiddenInput())

    class Meta:
        model = CodeRegex
        exclude = ['created_by', 'modified_by']


CodeRegexFormSet = inlineformset_factory(Component, CodeRegex, form=CodeRegexForm)
CodeListFormSet = inlineformset_factory(Component, CodeList, form=CodeListForm, min_num=1, validate_min=True)
  