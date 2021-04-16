'''
    ConceptForms
    
    Forms used in managing the Concepts.
'''
from django import forms
import datetime
# Access the user data from the request and provide an exception in the event
# that a user mysteriously disappears possibly through deletion while the form
# is being accessed.
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
# Access the models & permissions.
from ..models.CodingSystem import CodingSystem
from ..models.Component import Component
from ..models.Concept import Concept
from ..models.Tag import Tag
from ..models.ConceptCodeAttribute import ConceptCodeAttribute  

from ..permissions import (
    Permissions, allowed_to_permit
)
from django.contrib.postgres.forms import SimpleArrayField

'''
    ConceptForm
    This form is used to create or edit the data for a concept.
    Django will run all the clean_* methods when data is submitted.
'''
class ConceptForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # To get request.user, do not use kwargs.pop('user', None) due to
        # potential security hole.
        self.user = kwargs.pop('user')
        self.groups = kwargs.pop('groups')
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        # Populate the list of possible owners from the current user list
        # maintained by Django.
        # Set the initial value on a blank form as the current user.
        self.user_list = []             # Clear list or it will just accumulate.
        users = User.objects.all()
        for user in users:
            # Use user.id (stored in the database) to refer to a User object;
            # Django will use the username for display in the pull-down menu.
            self.user_list.append((user.id, user))
        self.fields['owner'].choices = self.user_list

        # Populate the list of possible groups from the group list
        # maintained by Django.
        self.group_list = []             # Clear list or it will just accumulate.
        self.group_list.append((0, '----------'))
        for group in self.groups.all():
            # Use user.id (stored in the database) to refer to a User object;
            # Django will use the username for display in the pull-down menu.
            self.group_list.append((group.id, group))
        self.fields['group'].choices = self.group_list

        # Check that the user generating the request matches the user which
        # owns the concept for permission to edit permissions.
        instance = getattr(self, 'instance', None)
            # if self.user.id != instance.owner.id:
        if instance.owner is not None:
            if not allowed_to_permit(self.user, Concept, instance.id):
                self.fields['owner'].disabled = True
                self.fields['owner_access'].disabled = True
                self.fields['group'].disabled = True
                self.fields['group_access'].disabled = True
                self.fields['world_access'].disabled = True
        else:
            # Note that we are setting self.initial NOT self.fields[].initial.
            self.initial['owner'] = self.user.id
            
        ## If the user does not belong to a certain group, remove the field
        #if not self.user.groups.filter(name__iexact='mygroup').exists():
        #    del self.fields['confidential']
    
    name = forms.CharField(
        label='Name:',
        help_text='250 max characters',
        required=True,
        error_messages={'required': 'Please enter a name'},
        max_length=250,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'Please enter a name', 'autofocus': 'autofocus'})
    )
    author = forms.CharField(
        label='Author:',
        required=True,
        error_messages={'required': 'Please enter an author'},
        max_length=250,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    entry_date = forms.DateField(
        initial=datetime.date.today,
        input_formats=('%d/%m/%Y',),
        label='Entry date:',
        required=True,
        error_messages={'required': 'Please enter an entry date'},
        widget=forms.DateInput(format='%d/%m/%Y', attrs={'class': 'form-control datepicker', 'placeholder': 'dd/mm/yyyy'})
    )
    description = forms.CharField(
        label='Description:',
        required=True,
        error_messages={'required': 'Please enter a description'},
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        max_length=3000
    )
    coding_system = forms.ModelChoiceField(
        label='Coding system:',
        required=True,
        queryset=CodingSystem.objects.lookups(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    validation_performed = forms.BooleanField(
        label='Validation performed:',
        required=False
    )
    validation_description = forms.CharField(
        label='Validation description:',
        error_messages={'required': 'Please enter a validation description'},
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        max_length=3000,
        required=False
    )
    publication_doi = forms.CharField(
        label='Primary publication DOI:',
        help_text='100 max characters',
        required=False,
        error_messages={'required': 'Please enter the publication doi'},
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    publication_link = forms.CharField(
        label='Primary publication link:',
        help_text='1000 max characters',
        required=False,
        error_messages={'required': 'Please enter the publication link'},
        max_length=1000,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    secondary_publication_links = forms.CharField(
        label='Secondary publication links:',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        max_length=3000
    )
    paper_published = forms.BooleanField(
        label='Paper published:',
        required=False
    )
    source_reference = forms.CharField(
        label='Source reference:',
        help_text='250 max characters',
        max_length=250,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    citation_requirements = forms.CharField(
        label='Citation requirements:',
        help_text='250 max characters',
        max_length=250,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    owner_access = forms.ChoiceField(
        label='Owner access:',
        widget=forms.RadioSelect(attrs={'class': 'radio-inline', 'disabled': 'disabled'}),
        choices=Permissions.PERMISSION_CHOICES,
        initial=Permissions.EDIT,
        required=False
    )
    group_access = forms.ChoiceField(
        label='Group access:',
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
        choices=Permissions.PERMISSION_CHOICES,
        initial=Permissions.NONE
    )
    world_access = forms.ChoiceField(
        label='Everyone else access:',
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
        choices=Permissions.PERMISSION_CHOICES_WORLD_ACCESS,
        initial=Permissions.NONE
    )
    owner = forms.ChoiceField(
        label='Owned by:',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
        # No choices or initial value as these are assigned dynamically.
    )
    group = forms.ChoiceField(
        label='Permitted group:',
        # Not required unless one of the GROUP options is selected. Handle
        # this case separately in the cleaning code.
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
        # No choices or initial value as these are assigned dynamically.
    )

    

    class Meta:
        model = Concept
        exclude = ['created_by', 'modified_by', 'deleted', 'is_deleted', 'deleted_by']

    def clean_owner(self):
        owner_id = self.cleaned_data['owner']
        users = User.objects.all()
        for user in users:
            if (user.id == int(owner_id)):
                return user      
        raise ValidationError(_("Didn't find selected user in selected users list???"))

    def clean_group(self):
        # Only need to clean the group data if group access is better than 'none'.
        
        instance = getattr(self, 'instance', None)
        
        group_access_value = -1
        if instance.id is None:  # create
            group_access_value = int(self.data['group_access']) 
        else:   # update
            if allowed_to_permit(self.user, Concept, instance.id):
                group_access_value = int(self.data['group_access'])
            else:
                prev_stored_group_access = Concept.objects.filter(id=instance.id).get().group_access
                group_access_value = prev_stored_group_access
                    
        if group_access_value in (Permissions.VIEW , Permissions.EDIT) : 
            group_id = self.cleaned_data['group']
            groups = self.groups.all()
            for group in groups:
                if (group.id == int(group_id)):
                    return group
            # No group found, so get Django to put up the required error.
            self._errors['group'] = self.error_class(['required'])
                

class ConceptUploadForm(forms.Form):
    CHOICES = (
        ('1', '1'),
        ('2', '2'),)
    COLUMN_CHOICES = (
        ('', 'Please select'),
        ('code', 'Code'),
        ('desc', 'Code description'),
        ('cat', 'Category'),
        ('cat_desc', 'Category description'),
        ('sub_cat', 'Sub category'),
        ('sub_cat_desc', 'Sub category description'),)

    upload_name = forms.CharField(
        label='Name:',
        help_text='100 max characters',
        required=True,
        max_length=100,
        error_messages={'required': 'Please enter an upload name'},
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'please enter an upload name'}))
    logical_type = forms.ChoiceField(
        label='Type:',
        widget=forms.RadioSelect(),
        choices=Component.LOGICAL_TYPES,
        initial=Component.LOGICAL_TYPES[0][0])
    concept_level_depth = forms.ChoiceField(
        label='Concept level depth:',
        required=True,
        choices=CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}))
    category_column = forms.ChoiceField(
        label='Category column:',
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=COLUMN_CHOICES,
        required=False)
    sub_category_column = forms.ChoiceField(
        label='Sub category column:',
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=COLUMN_CHOICES,
        required=False)
    first_row_has_column_headings = forms.BooleanField(
        label='Has column names in the first row',
        required=False)
    col_1 = forms.ChoiceField(
        label='Column 1:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),)
    col_2 = forms.ChoiceField(
        label='Column 2:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),)
    col_3 = forms.ChoiceField(
        label='Column 3:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False)
    col_4 = forms.ChoiceField(
        label='Column 4:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False)
    col_5 = forms.ChoiceField(
        label='Column 5:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False)
    col_6 = forms.ChoiceField(
        label='Column 6:',
        choices=COLUMN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False)
    upload_concept_file = forms.FileField(
        label='Upload csv:',
        required=True,)



class Tag(forms.ModelForm):
    description = forms.CharField(
        label='Description:',
        help_text='50 max characters',
        required=True,
        error_messages={'required': 'Please enter a description'},
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-required': 'Please enter a description'})
    )

    class Meta:
        model = Tag
        exclude = ['created_by', 'modified_by']
        
        