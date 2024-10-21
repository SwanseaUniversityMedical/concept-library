from django.db import connection
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import schema

import enum
import redis


class HealthcheckMode(int, enum.Enum):
	"""
		Describes the application state
	"""
	DEBUG = 0
	PROD  = 1


@schema(None)
class HealthcheckReport(APIView):
	"""
		HealthcheckReport view
			- Reports the health of the app's postgres & redis connection
	"""
	redis = None
	permission_classes = [permissions.IsAuthenticatedOrReadOnly]

	def get(self, request):
		"""
			HealthcheckReport GET request handler

			Args:
				request {RequestContext}: the request context of the request

			Returns:
				A {RESTResponse} specifying a status code and a JSON response body
				describing the health status of the application
		"""
		pg_connected = self.__ping_db()

		is_readonly = not settings.IS_DEVELOPMENT_PC and (settings.IS_DEMO or settings.CLL_READ_ONLY or settings.IS_INSIDE_GATEWAY)
		if settings.DEBUG or (not settings.DEBUG and is_readonly):
			return Response(
				data={
					'healthcheck_mode': HealthcheckMode.DEBUG.value,
					'postgres_healthy': pg_connected
				},
				content_type='application/json',
				status=(status.HTTP_200_OK if pg_connected else status.HTTP_503_SERVICE_UNAVAILABLE)
			)

		redis_connected = self.__ping_redis()
		response_status = status.HTTP_200_OK if redis_connected and pg_connected else status.HTTP_503_SERVICE_UNAVAILABLE
		return Response(
			data={
				'healthcheck_mode': HealthcheckMode.PROD.value,
				'redis_healthy': redis_connected,
				'postgres_healthy': pg_connected,
			},
			content_type='application/json',
			status=response_status
		)

	def __ping_db(self):
		"""
			Wrapper around the `connection.ensure_connection()` method
			to guarantee that a connection to the database is established
		"""
		try:
			connection.ensure_connection()
		except:
			return False
		else:
			return True

	def __ping_redis(self):
		"""
			Assert that the Redis client has initialised and a valid
			connection can be made
		"""
		try:
			if self.redis is None:
				self.redis = redis.Redis.from_url(settings.REDIS_BROKER_URL)

			self.redis.ping()
		except:
			return False
		else:
			return True
