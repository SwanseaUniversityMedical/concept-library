from django.db import models
from django.http import HttpRequest
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator, Page
from rest_framework.request import Request
from django.utils.translation import gettext_lazy as _

from clinicalcode.entity_utils import gen_utils, model_utils, constants
from clinicalcode.models.TimeStampedModel import TimeStampedModel

class HDRNJurisdiction(TimeStampedModel):
	"""HDRN Jurisdictions: Provinces & Territories of Canada"""
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=512, unique=True, null=False, blank=False)
	abbreviation = models.CharField(max_length=256, null=True, blank=True)
	description = models.TextField(null=True, blank=True)
	metadata = models.JSONField(blank=True, null=True)

	@staticmethod
	def get_verbose_names(*args, **kwargs):
		return { 'verbose_name': HDRNJurisdiction._meta.verbose_name, 'verbose_name_plural': HDRNJurisdiction._meta.verbose_name_plural }

	@staticmethod
	def get_brand_records_by_request(request, params=None):
		brand = model_utils.try_get_brand(request)
		if brand is None or brand.name == 'HDRN':
			records = HDRNJurisdiction.objects.all()

		if records is None:
			return HDRNJurisdiction.objects.none()

		if not isinstance(params, dict):
				params = { }

		if isinstance(request, Request) and hasattr(request, 'query_params'):
				params = { key: value for key, value in request.query_params.items() } | params
		elif isinstance(request, HttpRequest) and hasattr(request, 'GET'):
				params = { key: value for key, value in request.GET.dict().items() } | params

		search = params.pop('search', None)
		query = gen_utils.parse_model_field_query(HDRNJurisdiction, params, ignored_fields=['description'])
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

		records = HDRNJurisdiction.get_brand_records_by_request(request, params)

		page = gen_utils.try_value_as_type(params.get('page'), 'int', default=1)
		page = max(page, 1)

		page_size = params.get('page_size', '1')
		if page_size not in constants.PAGE_RESULTS_SIZE:
			page_size = constants.PAGE_RESULTS_SIZE.get('1')
		else:
			page_size = constants.PAGE_RESULTS_SIZE.get(page_size)

		if records is None:
			return Page(HDRNJurisdiction.objects.none(), 0, Paginator([], page_size, allow_empty_first_page=True))

		pagination = Paginator(records, page_size, allow_empty_first_page=True)
		try:
			page_obj = pagination.page(page)
		except EmptyPage:
			page_obj = pagination.page(pagination.num_pages)
		return page_obj

	class Meta:
		verbose_name = _('HDRN Jurisdiction')
		verbose_name_plural = _('HDRN Jurisdictions')

	def __str__(self):
		if isinstance(self.abbreviation, str) and not gen_utils.is_empty_string(self.abbreviation):
			return f'{self.name} ({self.abbreviation})'
		return self.name
