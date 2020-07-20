from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from clinicalcode.models.TimeStampedModel import TimeStampedModel


class Tag(TimeStampedModel):
    default = 1
    primary = 2
    success = 3
    info = 4
    warning = 5
    danger = 6

    DISPLAY_CHOICES = (
        (default, 'default'),
        (primary, 'primary'),
        (success, 'success'),
        (info, 'info'),
        (warning, 'warning'),
        (danger, 'danger')
    )
    description = models.CharField(max_length=50)
    display = models.IntegerField(choices=DISPLAY_CHOICES, default=1)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="tags_created")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="tags_updated")

    history = HistoricalRecords()
    
    
    class Meta:
        ordering = ('description',)
        
        
    def __str__(self):
        return self.description
