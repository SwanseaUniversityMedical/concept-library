from django import forms

MESSAGE_CATEGORIES = [
    ('General Enquiries', 'General Enquiries'),
    ('Website Support', 'Website Support'),
    ('Request Account', 'Request Account')
]

FORM_FIELD_CLASSES = {
    'EmailInput': 'text-input',
    'TextInput': 'text-input',
    'Textarea': 'text-area-input simple',
    'Select': 'selection-input'
}

class ContactForm(forms.Form):
    '''
        Generates the contact us form widgets
    '''
    from_email = forms.EmailField(required=True)
    name = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea)
    categories = forms.CharField(widget=forms.Select(choices=MESSAGE_CATEGORIES))

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)

        for form_input in self.visible_fields():
            input_type = type(form_input.field.widget).__name__
            if input_type in FORM_FIELD_CLASSES:
                form_input.field.widget.attrs['class'] = FORM_FIELD_CLASSES[input_type]

    def __str__(self):
        return self.name
