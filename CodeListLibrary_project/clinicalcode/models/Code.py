from django.db import models
from .CodeList import CodeList
from simple_history.models import HistoricalRecords


class CodeManager(models.Manager):

    def search(self, search_text=None):
        return (self.filter(code__contains=search_text).order_by('code'))


class Code(models.Model):
    code_list = models.ForeignKey(CodeList, related_name="codes")
    code = models.CharField(max_length=100)  # A Single Code
    description = models.CharField(max_length=510)

    history = HistoricalRecords()

    objects = CodeManager()

    def __str__(self):
        return self.code
    
    class Meta:
        # Specify the default ordering for the objects.
        ordering = ['code']

