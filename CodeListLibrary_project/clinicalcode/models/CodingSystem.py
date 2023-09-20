from django.db import models
from simple_history.models import HistoricalRecords

class CodingSystemQuerySet(models.QuerySet):
    def lookups(self):
        return self.only("id", "name").order_by("id")

class CodingSystemManager(models.Manager):
    def get_queryset(self):
        return CodingSystemQuerySet(self.model, using=self._db)

    def lookups(self):
        return self.get_queryset().lookups()

class CodingSystem(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField()
    link = models.CharField(max_length=2083)
    database_connection_name = models.CharField(max_length=250)
    table_name = models.CharField(max_length=250)
    code_column_name = models.CharField(max_length=250)
    desc_column_name = models.CharField(max_length=250)
    filter = models.CharField(max_length=1000, blank=True, null=True)

    codingsystem_id = models.IntegerField(unique=True, null=True)

    history = HistoricalRecords()

    objects = CodingSystemManager()

    def __str__(self):
        return self.name
