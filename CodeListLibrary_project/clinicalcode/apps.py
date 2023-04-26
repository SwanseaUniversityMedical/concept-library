from django.apps import AppConfig

class ClinicalCodeAppConfig(AppConfig):
    name = 'clinicalcode'

    def ready(self):
        from . import signals
