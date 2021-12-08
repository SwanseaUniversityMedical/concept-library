from django.db import models
from simple_history.models import HistoricalRecords
from .Component import Component
from clinicalcode.models.CodeList import CodeList


class CodeRegex(models.Model):

    SIMPLE = 1
    POSIX = 2

    CODE = 1
    DESCRIPTION = 2

    REGEX_TYPE_CHOICES = (
        (SIMPLE, 'simple (% only)'),
        (POSIX, 'POSIX regex')
        )
    SEARCH_COLUMN_CHOICES = (
        (CODE, 'code'),
        (DESCRIPTION, 'description')
    )

    component = models.OneToOneField(Component,
                                     on_delete=models.CASCADE,
                                     blank=True, null=True)
    regex_type = models.IntegerField(choices=REGEX_TYPE_CHOICES)
    regex_code = models.CharField(max_length=1000, blank=True, null=True)
    column_search = models.IntegerField(choices=SEARCH_COLUMN_CHOICES, blank=True, null=True)
    sql_rules = models.CharField(max_length=1000, blank=True, null=True)
    code_list = models.ForeignKey(CodeList, on_delete=models.CASCADE, blank=True, null=True)
    
    case_sensitive_search = models.NullBooleanField(default=False)
    
    history = HistoricalRecords()

    