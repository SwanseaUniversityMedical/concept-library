from clinicalcode.models.Brand import Brand
from clinicalcode.models.TimeStampedModel import TimeStampedModel
from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class Tag(TimeStampedModel):
    default = 1
    primary = 2
    success = 3
    info = 4
    warning = 5
    danger = 6

    DISPLAY_CHOICES = ((default, 'default'), (primary, 'primary'),
                       (success, 'success'), (info, 'info'),
                       (warning, 'warning'), (danger, 'danger'))

    tag = 1
    collection = 2

    TAG_TYPES = ((tag, 'tag'), (collection, 'collection'))
    description = models.CharField(max_length=50)
    display = models.IntegerField(choices=DISPLAY_CHOICES, default=1)
    created_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="tags_created")
    updated_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   null=True,
                                   related_name="tags_updated")

    tag_type = models.IntegerField(choices=TAG_TYPES, default=1)
    collection_brand = models.ForeignKey(Brand,
                                         on_delete=models.SET_NULL,
                                         null=True,
                                         related_name="tags_collection_brand")

    history = HistoricalRecords()

    class Meta:
        ordering = ('description', )

    def __str__(self):
        return self.description
