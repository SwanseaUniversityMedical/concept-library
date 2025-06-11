from django.conf import settings
from django.http import HttpResponseServerError
from django.http.response import JsonResponse
from django.template.loader import get_template

import logging

class ExceptionMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		return self.get_response(request)

	def process_exception(self, request, exception):
		if settings.DEBUG:
			raise exception

		logging.exception(f'Exception on View<method: {request.method}, path: {request.path}> with err:\n{str(exception)}')

		if request.accepts('text/html'):
			response = HttpResponseServerError(get_template('500.html').render(request=request))
		else:
			response = JsonResponse({ 'status': 'false', 'message': 'Server Error' }, status=500)

		return response
