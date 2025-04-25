from django.db import models
from django.http import HttpRequest
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.request import Request
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex

from clinicalcode.entity_utils import gen_utils, model_utils, constants
from clinicalcode.models.HDRNSite import HDRNSite
from clinicalcode.models.HDRNJurisdiction import HDRNJurisdiction
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNDataAsset(TimeStampedModel):
	"""
	HDRN Inventory Data Assets
	"""
	# Top-level
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=False, null=False, blank=False)
	description = models.TextField(null=True, blank=True)

	# Reference
	hdrn_id = models.IntegerField(null=True, blank=True)
	hdrn_uuid = models.UUIDField(primary_key=False, null=True, blank=True)

	# Metadata
	link = models.URLField(max_length=500, blank=True, null=True)
	site = models.ForeignKey(HDRNSite, on_delete=models.SET_NULL, null=True, related_name='data_assets')
	years = models.CharField(max_length=256, unique=False, null=True, blank=True)
	scope = models.TextField(null=True, blank=True)
	regions = models.ManyToManyField(HDRNJurisdiction, related_name='data_assets', blank=True)
	purpose = models.TextField(null=True, blank=True)

	collection_period = models.TextField(null=True, blank=True)

	data_level = models.CharField(max_length=256, unique=False, null=True, blank=True)
	data_categories = ArrayField(models.IntegerField(), blank=True, null=True) # Note: ref to `Tag`

	@staticmethod
	def get_verbose_names(*args, **kwargs):
		return { 'verbose_name': HDRNDataAsset._meta.verbose_name, 'verbose_name_plural': HDRNDataAsset._meta.verbose_name_plural }

	@staticmethod
	def get_brand_records_by_request(request, params=None):
		brand = model_utils.try_get_brand(request)
		if brand is None or brand.name == 'HDRN':
			records = HDRNDataAsset.objects.all()

		if records is None:
			return HDRNDataAsset.objects.none()

		if not isinstance(params, dict):
			params = { }

		if isinstance(request, Request) and hasattr(request, 'query_params'):
			params = { key: value for key, value in request.query_params.items() } | params
		elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
			params = { key: value for key, value in request.GET.dict().items() } | params

		search = params.pop('search', None)
		query = gen_utils.parse_model_field_query(HDRNDataAsset, params, ignored_fields=['description'])
		if query is not None:
			records = records.filter(**query)

		if not gen_utils.is_empty_string(search) and len(search) >= 3:
			records = records.filter(Q(name__icontains=search) | Q(description__icontains=search))

		records = records.order_by('id')
		return records

	@staticmethod
	def get_brand_paginated_records_by_request(request, params=None):
		if not isinstance(params, dict):
				params = { }

		if isinstance(request, Request) and hasattr(request, 'query_params'):
				params = { key: value for key, value in request.query_params.items() } | params
		elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
				params = { key: value for key, value in request.GET.dict().items() } | params

		records = HDRNDataAsset.get_brand_records_by_request(request, params)

		page = gen_utils.try_value_as_type(params.get('page'), 'int', default=1)
		page = max(page, 1)

		page_size = params.get('page_size', '1')
		if page_size not in constants.PAGE_RESULTS_SIZE:
			page_size = constants.PAGE_RESULTS_SIZE.get('1')
		else:
			page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

		if records is None:
			return Page(HDRNDataAsset.objects.none(), 0, Paginator([], page_size, allow_empty_first_page=True))

		pagination = Paginator(records, page_size, allow_empty_first_page=True)
		try:
			page_obj = pagination.page(page)
		except EmptyPage:
			page_obj = pagination.page(pagination.num_pages)
		return page_obj

	class Meta:
		ordering = ('name', )
		indexes = [
			GinIndex(name='hdrn_danm_trgm_idx', fields=['name'], opclasses=['gin_trgm_ops']),
			GinIndex(name='hdrn_dadc_arr_idx', fields=['data_categories'], opclasses=['array_ops']),
		]
		verbose_name = _('HDRN Data Asset')
		verbose_name_plural = _('HDRN Data Assets')

	def __str__(self):
		return self.name
