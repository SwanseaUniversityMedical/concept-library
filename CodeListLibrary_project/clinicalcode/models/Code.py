from django.db import models
from simple_history.models import HistoricalRecords

from .CodeList import CodeList

class CodeManager(models.Manager):
    def search(self, search_text=None):
        return (self.filter(code__contains=search_text).order_by('code'))

class Code(models.Model):
    code_list = models.ForeignKey(CodeList,
                                  on_delete=models.CASCADE,
                                  related_name="codes")
    code = models.CharField(max_length=100)
    description = models.CharField(max_length=510)

    history = HistoricalRecords()

    objects = CodeManager()

    def __str__(self):
        return self.code

    class Meta:
        ordering = ['code']
