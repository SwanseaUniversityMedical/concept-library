from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from ..models.GenericEntity import GenericEntity
from ..entity_utils import gen_utils, permission_utils, model_utils

class ArchiveForm(forms.Form):
    """
        Generates the archive form widget to allow users
        to archive their content
    """

    entity_id = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'hidden': True,
                'class': 'hide',
            }
        )
    )

    passphrase = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'text-input',
                'aria-label': 'Enter the entity ID to confirm',
                'autocomplete': 'off',
                'autocorrect': 'off',
            }
        ),
    )

    comments = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                'class': 'text-area-input',
                'style': 'resize: none;',
                'aria-label': 'Enter the reason you\'re archiving this entity',
                'rows': '4',
                'autocomplete': 'off',
                'autocorrect': 'on',
                'spellcheck': 'default',
                'wrap': 'soft',
            }
        ),
        min_length=10,
        max_length=255,
    )

    def __init__(self, *args, **kwargs):
        super(ArchiveForm, self).__init__(*args)

        request = kwargs.pop('parent_request')
        self.view_request = request
        self.username = self.view_request.user.username

    def clean(self):
        cleaned_data = super().clean()

        entity_id = cleaned_data.get('entity_id')
        self.__validate_entity(entity_id)

        passphrase = cleaned_data.get('passphrase')
        if not self.__check_required_value(passphrase):
            raise ValidationError('The \'Passphrase\' field is required')

        comments = cleaned_data.get('comments')
        if not self.__check_required_value(comments):
            raise ValidationError('The \'Comments\' field is required')

        if passphrase != entity_id:
            raise ValidationError('You entered the incorrect passphrase')
        
        return cleaned_data

    def __check_required_value(self, value):
        if not value or gen_utils.is_empty_string(value):
            return False
        return True

    def __validate_entity(self, entity_id):
        if not self.__check_required_value(entity_id):
            raise ValidationError('Form is invalid - please try again.')

        instance = model_utils.try_get_instance(GenericEntity, id=entity_id)
        if instance is None:
            raise ValidationError('Form is invalid - please try again.')
        
        if not permission_utils.can_user_edit_entity(self.view_request, entity_id):
            raise ValidationError('You do not have permission to delete this entity.')

        return True
