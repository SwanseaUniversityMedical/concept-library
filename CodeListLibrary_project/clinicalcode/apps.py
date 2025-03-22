""""""
from django.apps import AppConfig
from django.core.signals import request_started

class ClinicalCodeConfig(AppConfig):
	name = 'clinicalcode'

	def ready(self):
		# Enable EasyAudit signal override
		from clinicalcode.audit.request_signals import request_started_watchdog

		request_started.connect(
			receiver=request_started_watchdog,
			dispatch_uid='easy_audit_signals_request_started'
		)
