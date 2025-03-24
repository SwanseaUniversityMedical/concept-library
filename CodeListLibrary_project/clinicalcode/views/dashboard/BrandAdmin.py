"""Brand Administration View(s) & Request Handling."""
from django.db import connection
from django.conf import settings
from django.shortcuts import render
from django.core.cache import cache
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.core.exceptions import BadRequest, PermissionDenied
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from rest_framework.decorators import schema
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage

import os
import logging
import psycopg2

from clinicalcode.models import Brand, Tag, Template
from clinicalcode.entity_utils import gen_utils, model_utils, permission_utils

from .targets import TemplateTarget


logger = logging.getLogger(__name__)


class BrandDashboardView(TemplateView):
	"""
	Dashboard View for Brand Administration.

	:template:`clinicalcode/dashboard/index.html`
	"""
	reverse_name = 'brand_dashboard'
	template_name = 'clinicalcode/dashboard/index.html'
	preferred_logos = ['logo-transparent.png', 'apple-touch-icon.png']

	def __get_admin_logo_target(self, brand=None):
		"""
		Resolves the best Brand-related logo to use for the Dashboard view

		Args:
			brand (:model:`Brand`|Dict[str, Any]): optionally specify the Brand from which to resolve the logo; defaults to `None`

		Returns:
			A (str) describing the static storage relative path to the image file
		"""
		if isinstance(brand, dict):
			path = brand.get('logo_path', None)
		elif isinstance(brand, Brand):
			path = getattr(brand, 'logo_path', None) if hasattr(brand, 'logo_path') else None
		else:
			path = None

		if not isinstance(path, str) or gen_utils.is_empty_string(path):
			path = settings.APP_LOGO_PATH

		for fname in self.preferred_logos:
			trg_path = os.path.join(path, fname)
			abs_path = staticfiles_storage.path(trg_path)
			if abs_path is not None and staticfiles_storage.exists(abs_path):
				return trg_path

			abs_path = finders.find(trg_path)
			if abs_path is not None and os.path.isfile(abs_path):
				return trg_path
		return None

	@method_decorator([permission_utils.redirect_readonly, permission_utils.brand_admin_required])
	def dispatch(self, request, *args, **kwargs):
		"""
		Request-Response Middleman.

		.. Note::
		Decporated such that it only dispatches when:
			- The app isn't in a read-only state;
			- The Brand context is administrable;
			- And either (a) the user is a superuser, or (b) the user is authenticated & is a brand administrator of the current Brand.
		"""
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, *args, **kwargs):
		"""
		Resolves the View context data.

		Args:
			*args: Variable length argument list.
			**kwargs: Arbitrary keyword arguments.

		Kwargs:
			brand (:model:`Brand`): the current HttpRequest's :model:`Brand` context

		Returns:
			The resulting Template context (`Dict[str, Any]` _OR_ :py:class:`Context`) 
			
		Raises:
			BadRequest (400 error)
		"""
		brand = kwargs.get('brand')
		context = super().get_context_data(*args, **kwargs)
		return context | {
			'brand': brand,
			'logo_path': self.__get_admin_logo_target(brand),
		}

	def get(self, request, *args, **kwargs):
		"""
		Display a :model:`clinicalcode.Brand` administration dashboard.

		.. Context::

		``logo_path``
			A (str) specifying the static path to the branded logo

		``brand``
			A (Brand|None) specifying the current Brand instance

		.. Template::

		:template:`clinicalcode/dashboard/index.html`

		.. Reverse::
		`brand_dashboard`
		"""
		brand = model_utils.try_get_brand(request)
		context = self.get_context_data(*args, **kwargs, brand=brand)
		return render(request, self.template_name, context)


@schema(None)
class BrandPeopleView(APIView):
	"""Brand People APIView for the Brand Dashboard"""
	reverse_name = 'brand_people_summary'
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	def get(self, request):
		"""GET request handler for BrandPeopleView"""
		return Response({ })


@schema(None)
class BrandInventoryView(APIView):
	"""Brand Inventory APIView for the Brand Dashboard"""
	reverse_name = 'brand_inventory_summary'
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	def get(self, request):
		"""GET request handler for BrandInventoryView"""
		return Response({ })


@schema(None)
class BrandConfigurationView(APIView):
	"""Brand Configuration APIView for the Brand Dashboard"""
	reverse_name = 'brand_config_summary'
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	def get(self, request):
		"""GET request handler for BrandConfigurationView"""
		return Response({ })


@schema(None)
class BrandStatsSummaryView(APIView):
	"""Statistical Summary APIView, used to retrieve the interaction data for the Brand Dashboard"""
	# View behaviour
	reverse_name = 'brand_stats_summary'
	permission_classes = [permission_utils.IsReadOnlyRequest & permission_utils.IsBrandAdmin]

	# Statistics summary cache duration (in seconds)
	CACHE_TIMEOUT = 3600

	def get(self, request):
		"""GET request handler for BrandStatsSummaryView"""
		brand = model_utils.try_get_brand(request)
		summary = self.__get_or_compute_summary(brand)

		# TODO: TEMP
		print(list(Template.get_brand_records_by_request(request).object_list))

		return Response(summary)

	def __get_or_compute_summary(self, brand=None):
		"""
		Attempts to resolve the statistics summary for the specified Brand, either by retrieving it from the cache store or, if not found, by computing it.

		Args:
			brand (:model:`Brand`|None): the Request-specified Brand context

		Returns:
			A (dict) describing the statistics/analytics summary
		"""
		cache_key = brand.name if isinstance(brand, Brand) else 'all'
		cache_key = f'dashboard-stat-summary__{cache_key}__cache'

		summary = cache.get(cache_key)
		if summary is not None:
			return summary.get('value')

		summary = self.__compute_summary(brand)
		cache.set(cache_key, { 'value': summary }, self.CACHE_TIMEOUT)
		return summary

	def __resolve_assets(self, brand):
		'''
		'''
		pass

	def __compute_summary(self, brand):
		"""
		Attempts to compute the statistics summary for the specified Brand

		.. Note::
			Computes the following:
				- No. of Phenotypes created in the last 7 days
				- No. of Phenotypes edited in the last 7 days
				- No. of Phenotypes published in the last 7 days
				- No. of unique Daily Active Users today
				- No. of unique Monthly Active Users for this month
				- No. of page hits over the last 7 days

			These can be modified by overrides defined for each brand, _e.g._ ...
				- HDRN: `{"stats_context": "^/HDRN.*$"}`
				- HDRUK: `{"stats_context": "^(?!/HDRN)", "content_visibility": {"allow_null": true, "allowed_brands": [1, 2, 3]}}`

		Args:
			brand (:model:`Brand`|None): the Request-specified Brand context

		Returns:
			A (dict) describing the statistics/analytics summary
		"""
		query_params = {}
		stats_context = None
		content_visibility = None

		if brand:
			content_visibility = brand.get_vis_rules()

			overrides = getattr(brand, 'overrides', None)
			stats_context = overrides.get('stats_context') if isinstance(overrides, dict) else None
			if not isinstance(stats_context, str) or gen_utils.is_empty_string(stats_context):
				stats_context = '^\/%s.*$' % brand.name
			query_params.update({ 'stats_ctx': stats_context })

		with connection.cursor() as cursor:
			if isinstance(content_visibility, dict):
				allowed_brands = content_visibility.get('ids')
				allowed_brands = allowed_brands if isinstance(allowed_brands, list) and len(allowed_brands) > 0 else None
				allowed_null_brand = content_visibility.get('allow_null')
				query_params.update({ 'brand_ids': allowed_brands if allowed_brands is not None else [brand.id] })

				if allowed_brands and allowed_null_brand:
					content_visibility = psycopg2.sql.SQL('''and (ge.brands is null or ge.brands && %(brand_ids)s::int[])''')
				else:
					content_visibility = psycopg2.sql.SQL('''and (ge.brands is not null and ge.brands && %(brand_ids)s::int[])''')
			elif brand:
					query_params.update({ 'brand_ids': [brand.id] })
					content_visibility = psycopg2.sql.SQL('''and (ge.brands is not null and ge.brands && %(brand_ids)s::int[])''')
			else:
				content_visibility = psycopg2.sql.SQL('')

			if stats_context is not None:
				stats_context = psycopg2.sql.SQL('''and (req.url ~ %(stats_ctx)s)''')
			else:
				stats_context = psycopg2.sql.SQL('')

			sql = psycopg2.sql.Composed([
				# Visible phenotypes
				psycopg2.sql.SQL('''
				with
					pheno_vis as (
					  select ge.*
						  from public.clinicalcode_genericentity as ge
					   where (ge.is_deleted is null or ge.is_deleted = false)
							 '''),
				content_visibility,
				psycopg2.sql.SQL('''
					),
				'''),
				# Visible requests
				psycopg2.sql.SQL('''
					request_vis as (
					  select req.*,
									 (case
										 when req.user_id is not null then req.user_id::text
										 else null
									 end) as uid
						  from public.easyaudit_requestevent as req
					   where req.method in ('GET', 'POST', 'PUT')
							 '''),
				stats_context,
				psycopg2.sql.SQL('''
					),
				'''),
				# Count created
				psycopg2.sql.SQL('''
					pheno_created as (
					  select count(ge.*) as cnt
							from pheno_vis as ge
					   where ge.created >= date_trunc('day', now()) - interval '7 day'
					),
				'''),
				# Count edits
				psycopg2.sql.SQL('''
					pheno_edited as (
					  select count(hge.*) as cnt
							from pheno_vis as ge
						  join public.clinicalcode_historicalgenericentity as hge
								using (id)
					   where hge.history_date >= date_trunc('day', now()) - interval '7 day'
					),
				'''),
				# Count publications
				psycopg2.sql.SQL('''
					pheno_pubs as (
					  select count(pge.*) as cnt
							from pheno_vis as ge
							join public.clinicalcode_publishedgenericentity as pge
								on ge.id = pge.entity_id
						 where pge.approval_status = 2
							 and pge.modified >= date_trunc('day', now()) - interval '7 day'
					),
				'''),
				# Count DAU
				psycopg2.sql.SQL('''
					unq_dau as (
					  select count(distinct coalesce(req.remote_ip, req.uid, '')) as cnt
							from request_vis as req
						 where req.datetime >= date_trunc('day', now())
					),
				'''),
				# Count MAU
				psycopg2.sql.SQL('''
					unq_mau as (
					  select count(distinct coalesce(req.remote_ip, req.uid, '')) as cnt
							from request_vis as req
						 where req.datetime >= date_trunc('month', now())
					),
				'''),
				# Count page hits last 7 day
				psycopg2.sql.SQL('''
					page_hits as (
					  select count(*) as cnt
							from request_vis as req
						 where req.datetime >= date_trunc('day', now()) - interval '7 day'
					)
				'''),
				# Collect summary
				psycopg2.sql.SQL('''
				select
						(select cnt from pheno_created) as created,
						(select cnt from pheno_edited) as edited,
						(select cnt from pheno_pubs) as published,
						(select cnt from unq_dau) as dau,
						(select cnt from unq_mau) as mau,
						(select cnt from page_hits) as hits
				''')
			])

			cursor.execute(sql, params=query_params)
			columns = [col[0] for col in cursor.description]

			return { 'data': dict(zip(columns, row)) for row in cursor.fetchall() }
