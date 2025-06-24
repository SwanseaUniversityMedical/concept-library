"""App registry"""
from django.apps import AppConfig
from django.template import base as template_base
from django.core.signals import request_started

import re

# Enable multi-line tag support
template_base.tag_re = re.compile(template_base.tag_re.pattern, re.DOTALL)

# App registration
class ClinicalCodeConfig(AppConfig):
	"""CLL Base App Config"""
	name = 'clinicalcode'

	def ready(self):
		"""Initialises signals on app start"""

		# Enable EasyAudit signal override
		from clinicalcode.audit.request_signals import request_started_watchdog

		request_started.connect(
			receiver=request_started_watchdog,
			dispatch_uid='easy_audit_signals_request_started'
		)
