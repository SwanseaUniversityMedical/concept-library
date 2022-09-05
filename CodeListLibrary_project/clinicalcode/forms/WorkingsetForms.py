from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from clinicalcode.models import PhenotypeWorkingset
from clinicalcode.permissions import allowed_to_permit, Permissions
from clinicalcode.constants import Type_status



class WorkingsetForms(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # To get request.user, do not use kwargs.pop('user', None) due to
        # potential security hole.
        self.user = kwargs.pop('user')
        self.groups = kwargs.pop('groups')
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        # Populate the list of possible owners from the current user list
        # maintained by Django.
        # Set the initial value on a blank form as the current user.
        self.user_list = []  # Clear list or it will just accumulate.
        users = User.objects.all()
        for user in users:
            # Use user.id (stored in the database) to refer to a User object;
            # Django will use the username for display in the pull-down menu.
            self.user_list.append((user.id, user))
        self.fields['owner'].choices = self.user_list

        # Populate the list of possible groups from the group list
        # maintained by Django.
        self.group_list = []  # Clear list or it will just accumulate.
        self.phenotypes_concepts_data = [] # intial list of data to put
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
            if not allowed_to_permit(self.user, PhenotypeWorkingset, instance.id):
                self.fields['owner'].disabled = True
                self.fields['owner_access'].disabled = True
                self.fields['group'].disabled = True
                self.fields['group_access'].disabled = True
                self.fields['world_access'].disabled = True
        else:
            # Note that we are setting self.initial NOT self.fields[].initial.
            self.initial['owner'] = self.user.id


        ## If the user does not belong to a certain group, remove the field
        # if not self.user.groups.filter(name__iexact='mygroup').exists():
        #    del self.fields['confidential']

    name = forms.CharField(label='Name:', help_text='250 max characters', required=True,
                           error_messages={'required': 'Please enter a valid name'},
                           max_length=250, widget=forms.TextInput(attrs={
            'class': 'input-material col-sm-12 form-control ',
            'data-required': 'Please enter a valid name',
            'placeholder': " ",
            'autofocus': 'autofocus'
        }))

    author = forms.CharField(
        label='Author:',
        required=True,
        error_messages={'required': 'Please enter an author'},
        max_length=250,

        widget=forms.TextInput(attrs={'class': 'input-material col-sm-12 form-control','placeholder':" "})
    )

    type = forms.ChoiceField(

        label='Type',
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=Type_status,
        required=True
    )

    description = forms.CharField(
        label='Description',
        required=True,
        error_messages={'required': 'Please enter a description'},
        widget=forms.Textarea(attrs={
            'class': 'input-material col-sm-12 form-control',
            'rows': 5,'placeholder':" "
        }),
        max_length=3000)

    publication = forms.CharField(
        label='Publication',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'input-material col-sm-12 form-control',
            'rows': 5,
             'placeholder':" "
        }),
        max_length=3000)

    citation_requirements = forms.CharField(
        label='Citation requirements',
        help_text='250 max characters',
        max_length=250,
        required=False,
        widget=forms.TextInput(attrs={'class': 'input-material col-sm-12 form-control','placeholder':" "}))

    owner_access = forms.ChoiceField(
        label='Owner access',
        widget=forms.RadioSelect(attrs={
            'class': 'radio-inline',
            'disabled': 'disabled'
        }),
        choices=Permissions.PERMISSION_CHOICES,
        initial=Permissions.EDIT,
        required=False)
    group_access = forms.ChoiceField(
        label='Group access',
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
        choices=Permissions.PERMISSION_CHOICES,
        initial=Permissions.NONE)
    world_access = forms.ChoiceField(
        label='Everyone else access',
        widget=forms.RadioSelect(attrs={'class': 'radio-inline'}),
        choices=Permissions.PERMISSION_CHOICES_WORLD_ACCESS,
        initial=Permissions.NONE)
    owner = forms.ChoiceField(
        label='Owned by',
        required=True,
        widget=forms.Select(attrs={'class': 'input-material col-sm-12 form-control','placeholder':" "})
        # No choices or initial value as these are assigned dynamically.
    )
    group = forms.ChoiceField(
        label='Permitted group',
        # Not required unless one of the GROUP options is selected. Handle
        # this case separately in the cleaning code.
        required=False,
        widget=forms.Select(attrs={'class': 'input-material col-sm-12 form-control'})
        # No choices or initial value as these are assigned dynamically.
    )

    def clean_owner(self):
        owner_id = self.cleaned_data['owner']
        users = User.objects.all()
        for user in users:
            if (user.id == int(owner_id)):
                return user
        raise ValidationError(
            _("Didn't find selected user in selected users list???"))

    def clean_group(self):
        # Only need to clean the group data if group access is better than 'none'.

        instance = getattr(self, 'instance', None)

        group_access_value = -1
        if instance.id is None:  # create
            group_access_value = int(self.data['group_access'])
        else:  # update
            if allowed_to_permit(self.user, PhenotypeWorkingset, instance.id):
                group_access_value = int(self.data['group_access'])
            else:
                prev_stored_group_access = PhenotypeWorkingset.objects.filter(
                    id=instance.id).get().group_access
                group_access_value = prev_stored_group_access

        if group_access_value in (Permissions.VIEW, Permissions.EDIT):
            group_id = self.cleaned_data['group']
            groups = self.groups.all()
            for group in groups:
                if (group.id == int(group_id)):
                    return group
            # No group found, so get Django to put up the required error.
            self._errors['group'] = self.error_class(['required'])

    class Meta:
        '''
            Class metadata (anything that's not a field).
        '''
        model = PhenotypeWorkingset


        exclude = [
            'created_by', 'modified_by', 'deleted', 'is_deleted', 'deleted_by','phenotypes_concepts_data'
        ] #Exciding jsonfileobject because will be separate validation from client
