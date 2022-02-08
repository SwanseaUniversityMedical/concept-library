from django import forms


class ContactForm(forms.Form):
    issuetypes = [('General Enquiries', 'General Enquiries')]
    from_email = forms.EmailField(required=True)
    name = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea)
    categories = forms.CharField(widget=forms.Select(choices=issuetypes))

    def __str__(self):
        return self.name
