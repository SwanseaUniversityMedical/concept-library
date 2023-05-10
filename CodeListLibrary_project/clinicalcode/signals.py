from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_save
from django.db.models.fields.related import ManyToManyField

from .mixins.HistoricalMixin import HistoricalModelMixin
from .models.ClinicalConcept import ClinicalConcept

@receiver(post_save)
def historical_m2m_clone_handler(sender, **kwargs):
    if not issubclass(sender, HistoricalModelMixin):
       return
    
    instance = kwargs.get('instance')
    if not instance:
        return
    
    initial = None
    try:
        initial = getattr(instance, '__initial')
    except:
        pass

    if initial is None:
        instance.__initial = instance._dict
        return
    
    for key, value in initial.items():
        field = instance._meta.get_field(key)
        if isinstance(field, ManyToManyField):
            getattr(instance, key).add(*value)
    
    instance.__initial = instance._dict

@receiver(m2m_changed, sender=ClinicalConcept.rulesets.through)
def ruleset_changed(sender, **kwargs):
    action = kwargs.get('action')
    timeline = action.split('_')[0]
    concept = kwargs.get('instance')
    if timeline == 'pre':
        return
    concept.__initial = concept._dict
