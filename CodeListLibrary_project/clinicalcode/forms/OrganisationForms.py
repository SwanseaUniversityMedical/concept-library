from django import forms
from django.forms.models import modelformset_factory
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib import admin
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from ..models.Organisation import Organisation, OrganisationMembership, OrganisationAuthority
from ..entity_utils import gen_utils, permission_utils, model_utils

from django.utils import timezone

User = get_user_model()

""" Admin """

class OrganisationMembershipInline(admin.TabularInline):
  model = OrganisationMembership
  extra = 1

class OrganisationAuthorityInline(admin.TabularInline):
  model = OrganisationAuthority
  extra = 1

class OrganisationAdminForm(forms.ModelForm):
  """
    Override organisation admin form management
  """
  name = forms.CharField(
    required=True,
    widget=forms.TextInput(
      attrs={ }
    ),
    min_length=3,
    max_length=250
  )
  slug = forms.CharField(
    required=False,
    widget=forms.TextInput(
      attrs={ }
    )
  )
  description = forms.CharField(
    required=False,
    widget=forms.Textarea(
      attrs={ }
    ),
    max_length=1000
  )
  email = forms.EmailField(required=False)
  website = forms.URLField(required=False)
  owner = forms.ModelChoiceField(queryset=User.objects.all())
  created = forms.DateTimeField(
    required=False,
    widget=forms.DateTimeInput(attrs={'readonly': 'readonly'})
  )

  def __init__(self, *args, **kwargs):
    super(OrganisationAdminForm, self).__init__(*args, **kwargs)

  class Meta:
    model = Organisation
    fields = '__all__'

  def clean_created(self):
    """
      Responsible for cleaning the `created` field
      
      Returns:
        (timezone) - the cleaned `created` value
    """
    # Example clean individual fields
    if self.cleaned_data.get('created', None) is None:
      return timezone.now()

    return self.cleaned_data['created']

  def clean(self):
    """
      Responsible for cleaning the model fields form data
      
      Returns:
        (dict) - the cleaned model form data
    """
    # Example clean multiple fields
    data = self.cleaned_data

    create_datetime = data.get('created', None)
    if create_datetime is None:
      data.update({ 'created': timezone.now() })
    
    return data

""" Create / Update """

class OrganisationCreateForm(forms.ModelForm):
  NameValidator = RegexValidator(
    r'^(?=.*[a-zA-Z].*)([a-zA-Z0-9\-_\(\) ]+)*$',
    'Name can only contain a-z, 0-9, -, _, ( and )'
  )

  name = forms.CharField(
    required=True,
    widget=forms.TextInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'off',
        'autocorrect': 'off',
      }
    ),
    min_length=3,
    max_length=250,
    validators=[NameValidator]
  )
  description = forms.CharField(
    required=False,
    widget=forms.Textarea(
      attrs={
        'class': 'text-area-input',
        'style': 'resize: none;',
        'aria-label': 'Describe your organisation',
        'rows': '4',
        'autocomplete': 'off',
        'autocorrect': 'on',
        'spellcheck': 'default',
        'wrap': 'soft',
      }
    ),
    max_length=1000
  )
  email = forms.EmailField(
    required=False,
    widget=forms.EmailInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'on',
        'autocorrect': 'off',
      }
    )
  )
  website = forms.URLField(
    required=False,
    widget=forms.URLInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'off',
        'autocorrect': 'off',
      }
    )
  )

  def __init__(self, *args, **kwargs):
    initial = kwargs.get('initial')
    super(OrganisationCreateForm, self).__init__(*args, **kwargs)

    owner = initial.get('owner')
    self.fields['owner'] = forms.ModelChoiceField(
      queryset=User.objects.filter(pk=owner.id),
      initial=owner,
      widget=forms.HiddenInput(),
      required=False
    )

  class Meta:
    model = Organisation
    fields = '__all__'
    exclude = ['slug', 'created', 'members', 'brands']

  def clean(self):
    """
      Responsible for cleaning the model fields form data
      
      Returns:
        (dict) - the cleaned model form data
    """
    data = super(OrganisationCreateForm, self).clean()

    name = data.get('name', None)
    if gen_utils.is_empty_string(name):
      self.add_error(
        'name', 
        ValidationError('Name cannot be empty')
      )
    else:
      data.update({ 'slug': slugify(name) })

    create_datetime = data.get('created', None)
    if create_datetime is None:
      data.update({ 'created': timezone.now() })
    
    return data

class OrganisationManageForm(forms.ModelForm):
  NameValidator = RegexValidator(
    r'^(?=.*[a-zA-Z].*)([a-zA-Z0-9\-_\(\) ]+)*$',
    'Name can only contain a-z, 0-9, -, _, ( and )'
  )

  name = forms.CharField(
    required=True,
    widget=forms.TextInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'off',
        'autocorrect': 'off',
      }
    ),
    min_length=3,
    max_length=250,
    validators=[NameValidator]
  )
  description = forms.CharField(
    required=False,
    widget=forms.Textarea(
      attrs={
        'class': 'text-area-input',
        'style': 'resize: none;',
        'aria-label': 'Describe your organisation',
        'rows': '4',
        'autocomplete': 'off',
        'autocorrect': 'on',
        'spellcheck': 'default',
        'wrap': 'soft',
      }
    ),
    max_length=1000
  )
  email = forms.EmailField(
    required=False,
    widget=forms.EmailInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'on',
        'autocorrect': 'off',
      }
    )
  )
  website = forms.URLField(
    required=False,
    widget=forms.URLInput(
      attrs={
        'class': 'text-input',
        'aria-label': 'Enter the organisation\'s name',
        'autocomplete': 'off',
        'autocorrect': 'off',
      }
    )
  )

  def __init__(self, *args, **kwargs):
    super(OrganisationManageForm, self).__init__(*args, **kwargs)

    print(args, kwargs)

  class Meta:
    model = Organisation
    fields = '__all__'
    exclude = ['slug', 'created', 'owner', 'brands']

  def clean(self):
    """
      Responsible for cleaning the model fields form data
      
      Returns:
        (dict) - the cleaned model form data
    """
    data = super(OrganisationManageForm, self).clean()

    name = data.get('name', None)
    if gen_utils.is_empty_string(name):
      self.add_error(
        'name', 
        ValidationError('Name cannot be empty')
      )
    else:
      data.update({ 'slug': slugify(name) })

    create_datetime = data.get('created', None)
    if create_datetime is None:
      data.update({ 'created': timezone.now() })
    
    return data
