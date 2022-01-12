from django.db import models
from django.contrib.auth.models import User, Group
from django import forms
from simple_history.models import HistoricalRecords
from .TimeStampedModel import TimeStampedModel
from django.contrib.postgres.fields import JSONField


class ContactForm(forms.Form):
    issuetypes = [
        ('General Enquiries', 'General Enquiries')
    ]
    from_email = forms.EmailField(required=True)
    name = forms.CharField(required=True)
    message = forms.CharField(widget=forms.Textarea)
    categories = forms.CharField(widget=forms.Select(choices=issuetypes))

    def __str__(self):
        return self.name
    
   













