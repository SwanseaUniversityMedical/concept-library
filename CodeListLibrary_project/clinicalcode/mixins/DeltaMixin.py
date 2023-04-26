from django.db import models
from decimal import Decimal
from itertools import chain
from datetime import datetime

import inspect

def model_to_dict(instance, fields=None, exclude=None, date_to_strf=None):
    from django.db.models.fields.related import ManyToManyField
    from django.db.models.fields import DateTimeField
    from django.db.models.fields.files import ImageField, FileField
    opts = instance._meta
    data = {}

    __fields = list(map(lambda a: a.split('__')[0], fields or []))

    for f in chain(opts.concrete_fields, opts.many_to_many):
        is_editable = getattr(f, 'editable', False)

        if fields and f.name not in __fields:
            continue

        if exclude and f.name in exclude:
            continue

        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                qs = f.value_from_object(instance)
                if isinstance(qs, list):
                    data[f.name] = qs
                elif qs._result_cache is not None:
                    data[f.name] = [item.pk for item in qs]
                else:
                    try:
                        m2m_field  = list(filter(lambda a: f.name in a and a.find('__') != -1, fields))[0]
                        key = m2m_field[len(f.name) + 2:]
                        data[f.name] = list(qs.values_list(key, flat=True))
                    except IndexError:
                        data[f.name] = list(qs.values_list('pk', flat=True))

        elif isinstance(f, DateTimeField):
            date = f.value_from_object(instance)
            data[f.name] = date_to_strf(date) if date_to_strf else datetime.timestamp(date)

        elif isinstance(f, ImageField):
            image = f.value_from_object(instance)
            data[f.name] = image.url if image else None

        elif isinstance(f, FileField):
            file = f.value_from_object(instance)
            data[f.name] = file.url if file  else None

        elif is_editable:
            data[f.name] = f.value_from_object(instance)

    if not instance.pk:
        return data
    
    funcs = set(__fields) - set(list(data.keys()))
    for func in funcs:
        obj = getattr(instance, func)
        if inspect.ismethod(obj):
            data[func] = obj()
        else:
            data[func] = obj
    return data

class DeltaModelMixin(object):
    '''
        Delta diff between models
    '''
    FLOAT_EPSILON = 0.00001
    IGNORED_FIELDS = ['id', 'entity_id', 'version_id', 'created_date', 'version_date', 'change_reason', 'change_type']

    def __init__(self, *args, **kwargs):
        super(DeltaModelMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    def get_delta(self, d2):
        d1 = self.__initial

        if isinstance(d2, models.Model) and getattr(d2, '_dict'):
            d2 = d2._dict

        if not d1:
            return dict()

        diffs = {}
        for k, v1 in d1.items():
            v2 = d2[k]
            if isinstance(v1, Decimal):
                v1 = float(v1)
            if isinstance(v2, Decimal):
                v2 = float(v2)
            
            if isinstance(v2, float) or isinstance(v1, float):
                changed = self.is_float_diff(v1, v2)
            else:
                changed = v1 != v2

            if changed: 
                diffs[k] = [v1, v2]
        
        return dict(diffs)

    @property
    def diff(self):
        return self.get_delta(self._dict)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def is_float_diff(self, a, b):
        return abs(round(a, b, 5)) > self.FLOAT_EPSILON
    
    def get_field_diff(self, field_name):
        return self.diff.get(field_name, None)

    @property
    def _dict(self):
        data = model_to_dict(self, fields=[field.name for field in self._meta.get_fields() if field.name not in self.IGNORED_FIELDS])
        return data
