"""Brand Administration View(s) & Request Handling."""
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

import logging

from clinicalcode.entity_utils import model_utils, permission_utils


logger = logging.getLogger(__name__)


class BrandDashboard(TemplateView):
	"""
	Brand Dashboard View

	:template:`clinicalcode/dashboard/index.html`
	"""
	reverse_name = 'brand_dashboard'
	template_name = 'clinicalcode/dashboard/index.html'

	@method_decorator([permission_utils.redirect_readonly, permission_utils.brand_admin_required])
	def dispatch(self, request, *args, **kwargs):
		"""
		View dispatch management

		.. Note::
		Dispatches if:
			- The app isn't in a read-only state;
			- The Brand context is administrable;
			- And either (a) the user is a superuser, or (b) the user is authenticated & is a brand administrator of the current Brand.
		"""
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, *args, **kwargs):
		"""
		Resolves the View context data

		Args:
			*args: Variable length argument list.
			**kwargs: Arbitrary keyword arguments.

		Kwargs:
			brand (:py:class:`Brand`): the current HttpRequest's :py:class:`Brand` context

		Returns:
			The resulting Template context (`Dict[str, Any]` _OR_ :py:class:`Context`) 
			
		Raises:
			HttpResponseBadRequest (400 error)
		"""
		brand = kwargs.get('brand')
		if brand is None:
			raise HttpResponseBadRequest('Invalid Brand')

		context = super().get_context_data(*args, **kwargs)
		return context | {
			'administrators': brand.admins.all(),
		}

	def get(self, request, *args, **kwargs):
		"""
		Display a :model:`clinicalcode.Brand` administration dashboard.

		.. Context::

		``administrators``
			A :py:class:`QuerySet` of :model:`auth.User`s who can administrate this instance.

		.. Template::

		:template:`clinicalcode/dashboard/index.html`

		.. Reverse::
		`brand_dashboard`
		"""
		brand = model_utils.try_get_brand(request)
		context = self.get_context_data(*args, **kwargs, brand=brand)
		return render(request, self.template_name, context)