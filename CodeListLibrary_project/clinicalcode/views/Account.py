"""Views relating to Django User account management."""

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import login as auth_login
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ImproperlyConfigured, ValidationError
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm
from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView
from django.contrib.auth.views import PasswordContextMixin
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters


# State
UserModel = get_user_model()


# Const
INTERNAL_RESET_SESSION_TOKEN = '_password_reset_token'


# Views
class AccountManagementResultView(TemplateView):
	"""
		Simple account management result page.

		Note:
			- Intention is to display success/failure message relating to `Django Account Management <https://github.com/django/django/tree/ef6a83789b310a441237a190a493c9586a4cb260/django/contrib/admin/templates/registration>`__ registration pages;
			- The content of this page can be modified using the `as_view()` method of the `TemplateView` class.
	"""
	requires_auth = False
	template_name = 'registration/management_result.html'

	template_title = _('Account Management')
	template_header = None
	template_target = None
	template_message = '<p>%(msg)s</p>' % { 'msg': _('Account property changed') }
	template_prompt_signin = True
	template_incl_redirect = True

	def dispatch(self, request, *args, **kwargs):
		if self.requires_auth and (not request.user or not request.user.is_authenticated):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		return context | {
			'template_title': self.template_title,
			'template_header': self.template_header,
			'template_target': self.template_target,
			'template_message': self.template_message,
			'template_prompt_signin': self.template_prompt_signin and not self.requires_auth,
			'template_incl_redirect': self.template_incl_redirect,
		}


class AccountResetConfirmView(PasswordContextMixin, FormView):
	"""Password reset form & view."""

	title = _('Enter new password')
	form_class = SetPasswordForm
	success_url = reverse_lazy('password_reset_complete')
	template_name = 'registration/reset_form.html'

	post_reset_login = True
	post_reset_login_backend = None

	reset_url_token = 'set-password'
	token_generator = default_token_generator

	@method_decorator(sensitive_post_parameters())
	@method_decorator(never_cache)
	def dispatch(self, *args, **kwargs):
		if 'uidb64' not in kwargs or 'token' not in kwargs:
			raise ImproperlyConfigured(
				'The URL path must contain \'uidb64\' and \'token\' parameters.'
			)

		self.validlink = False
		self.user = self.get_user(kwargs['uidb64'])

		if self.user is not None:
			token = kwargs['token']
			if token == self.reset_url_token:
				session_token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
				if self.token_generator.check_token(self.user, session_token):
					self.validlink = True
					return super().dispatch(*args, **kwargs)
			else:
				if self.token_generator.check_token(self.user, token):
					self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
					redirect_url = self.request.path.replace(
						token, self.reset_url_token
					)
					return HttpResponseRedirect(redirect_url)

		return self.render_to_response(self.get_context_data())

	def get_user(self, uidb64):
		try:
			uid = urlsafe_base64_decode(uidb64).decode()
			pk = UserModel._meta.pk.to_python(uid)
			user = UserModel._default_manager.get(pk=pk)
		except (
			TypeError,
			ValueError,
			OverflowError,
			UserModel.DoesNotExist,
			ValidationError,
		):
			user = None
		return user

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.user
		return kwargs

	def form_invalid(self, form):
		response = super().form_invalid(form)
		if self.request.accepts('text/html'):
			return response
		return JsonResponse(form.errors, status=400)

	def form_valid(self, form):
		user = form.save()
		del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
		if self.post_reset_login:
			auth_login(self.request, user, self.post_reset_login_backend)
		return super().form_valid(form)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		if self.validlink:
			context['validlink'] = True
		else:
			context.update({
				'form': None,
				'title': _('Password reset unsuccessful'),
				'validlink': False,
			})

		return context
