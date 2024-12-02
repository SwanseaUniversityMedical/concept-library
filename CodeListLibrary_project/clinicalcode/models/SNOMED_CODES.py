from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

import datetime

from ..entity_utils import constants

class SNOMED_CODES(models.Model):
    # Top-level
    id = models.BigAutoField(auto_created=True, primary_key=True)
    code = models.CharField(max_length=18, null=True, blank=True, unique=True, default='')
    description = models.CharField(max_length=256, null=True, blank=True, default='')
    case_sig = models.IntegerField(
        choices=[(e.name, e.value) for e in constants.CASE_SIGNIFICANCE],
        null=False, default=constants.CASE_SIGNIFICANCE.CI.value
    )
    active = models.BooleanField(null=False, default=True)
    effective_time = models.DateField(null=False, default=datetime.date.today)

    # Mapping
    mesh_codes = ArrayField(models.TextField(), blank=True, null=True)
    opcs4_codes = ArrayField(models.TextField(), blank=True, null=True)
    icd9_codes = ArrayField(models.TextField(), blank=True, null=True)
    icd10_codes = ArrayField(models.TextField(), blank=True, null=True)
    readcv2_codes = ArrayField(models.TextField(), blank=True, null=True)
    readcv3_codes = ArrayField(models.TextField(), blank=True, null=True)

    # FTS
    search_vector = SearchVectorField(null=True)   # Weighted name / description / synonyms / relations
    synonyms_vector = SearchVectorField(null=True) # Related descriptor terms, e.g. snomed synonyms
    relation_vector = SearchVectorField(null=True) # Related object descriptors, e.g. mapped codes

    class Meta:
        # Index reference
        indexes = [
            GinIndex(name='sct_cd_trgm_idx', fields=['code'], opclasses=['gin_trgm_ops']),
            GinIndex(name='sct_desc_trgm_idx', fields=['description'], opclasses=['gin_trgm_ops']),
            GinIndex(name='sct_mesh_txt_idx', fields=['mesh_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_opcs_txt_idx', fields=['opcs4_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_icd9_txt_idx', fields=['icd9_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_icd10_txt_idx', fields=['icd10_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_cv2_txt_idx', fields=['readcv2_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_cv3_txt_idx', fields=['readcv3_codes'], opclasses=['array_ops']),
            GinIndex(name='sct_sv_gin_idx', fields=['search_vector']),
            GinIndex(name='sct_syn_gin_idx', fields=['synonyms_vector']),
            GinIndex(name='sct_rel_gin_idx', fields=['relation_vector']),
        ]
