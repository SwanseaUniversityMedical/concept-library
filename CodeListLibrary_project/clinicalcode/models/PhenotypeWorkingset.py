'''
    Working Set Model

    A working set is a list of columns from a number of Concepts and Phenotypes
'''
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from simple_history.models import HistoricalRecords
from clinicalcode.constants import Type_status

from ..permissions import Permissions
from .TimeStampedModel import TimeStampedModel





class PhenotypeWorkingset(TimeStampedModel):
    id = models.CharField(primary_key=True, editable=False, max_length=50)
    name = models.CharField(max_length=250)
    type = models.IntegerField(choices=Type_status,null=True,blank=True,default = 0)  # restricted type of the working_set(constants)
    tags = ArrayField(models.IntegerField(), blank=True, null=True)  # tags of brands
    collections = ArrayField(models.IntegerField(), blank=True, null=True)  # collection of branded workingsets
    publications = ArrayField(models.CharField(max_length=500), blank=True, null=True)
    author = models.CharField(max_length=250)
    citation_requirements = models.CharField(max_length=250)  # Any request for citation requirements to be honoured
    description = models.TextField(null=True, blank=True)
    data_sources = ArrayField(models.IntegerField(), blank=True, null=True)  # Easy access to data sources

    # Contains all data related to Phenotypes/Concepts
    phenotypes_concepts_data = JSONField()

    # Permissions section for updating/creating phenotype_workingset
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="phenotype_workingset_created")
    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="phenotype_workingset_updated")
    is_deleted = models.NullBooleanField(default=False)
    deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,related_name="phenotype_workingset_deleted")
    owner = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="phenotype_workingset_owned")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
    owner_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.EDIT)
    group_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)
    world_access = models.IntegerField(choices=Permissions.PERMISSION_CHOICES, default=Permissions.NONE)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        count = PhenotypeWorkingset.objects.count()
        if count:
            count += 1
        else:
            count = 1
        if not self.id:
            self.id = "WS" + str(count)

        super(PhenotypeWorkingset, self).save(*args, **kwargs)

    def save_without_historical_record(self, *args, **kwargs):
        self.skip_history_when_saving = True
        try:
            ret = self.save(*args, **kwargs)
        finally:
            del self.skip_history_when_saving
        return ret

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name
