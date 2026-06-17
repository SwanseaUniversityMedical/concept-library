from django.conf import settings
from django.contrib import messages
from django.shortcuts import render
from django.http.response import JsonResponse

import logging

class ExceptionMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		return self.get_response(request)

	def __resolve_ex_msg(self, exception, code=None):
		if isinstance(exception, Exception):
			msg = getattr(exception, 'message', None) if hasattr(exception, 'message') else str(exception)
		else:
			msg = str(exception)

		match code:
			case 400:
				title = 'Bad Request'
			case 401:
				title = 'Unauthorized'
			case 403:
				title = 'Forbidden'
			case 404:
				title = 'Not found'
			case 405:
				title = 'Method Not Allowed'
			case 406:
				title = 'Not Acceptable'
			case 500:
				title = 'Server Error'
			case 503:
				title = 'Service Unavailable'
			case _:
				title = 'Unknown Server Error'

		if not isinstance(msg, str) or len(msg.strip()) < 1 or msg.isspace():
			msg = title

		return title, msg

	def process_exception(self, request, exception):
		if settings.DEBUG:
			raise exception

		logging.exception(f'Exception on View<method: {request.method}, path: {request.path}> with err:\n{str(exception)}')

		code = None
		title = None
		message = None
		if isinstance(exception, Exception):
			match type(exception).__name__:
				case 'Http404' | 'ObjectDoesNotExist' | 'EmptyResultSet': # 404
					code = 404
					title, message = self.__resolve_ex_msg(exception, code)
				case 'MethodNotAllowed': # 405
					code = 405
					title, message = self.__resolve_ex_msg(exception, code)
				case 'PermissionDenied': # 403
					code = 403
					title, message = self.__resolve_ex_msg(exception, code)
				case 'BadRequest' | 'ValidationError':
					code = 400
					title, message = self.__resolve_ex_msg(exception, code)
				case 'APIException':
					try:
						details = exception.get_full_details()
						code = details.get('code', 500)
						title, message = self.__resolve_ex_info(details.get('message', None), code)
					except:
						pass
				case _:
					pass

		if not code or not message:
			code = 500
			title = 'Unknown Server Error'
			message = 'Unknown Server Error'

		if request.accepts('text/html'):
			if title != message:
				messages.add_message(request, messages.INFO, message)

			response = render(
					status=code,
					request=request,
					context={ 'errheader': { 'title': title, 'status_code': code } },
					content_type='text/html',
					template_name='fmt-error.html'
			)
		else:
			response = JsonResponse({ 'status': 'false', 'message': message }, status=code)

		return response
