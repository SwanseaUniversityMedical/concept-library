from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

import datetime

from ..entity_utils import constants

class MESH_CODES(models.Model):
    # Top-level
    id = models.BigAutoField(auto_created=True, primary_key=True)
    code = models.CharField(max_length=10, null=True, blank=True, unique=False, default='')
    description = models.CharField(max_length=256, null=True, blank=True, default='')
    parent_codes = ArrayField(models.TextField(), blank=True, null=True)
    record_type = models.IntegerField(null=True, blank=True, default=0)
    record_category = models.IntegerField(null=True, blank=True, default=0)
    record_modifier = models.IntegerField(null=True, blank=True, default=0)
    active = models.BooleanField(null=True, blank=True, default=True)
    effective_time = models.DateField(null=True, blank=True, default=datetime.date.today)

    class Meta:
        # Index reference
        indexes = [
            GinIndex(
                name='mesh_code_ln_gin_idx',
                fields=['code'],
                opclasses=['gin_trgm_ops']
            ),
            GinIndex(
                name='mesh_desc_ln_gin_idx',
                fields=['description'],
                opclasses=['gin_trgm_ops']
            ),
        ]
