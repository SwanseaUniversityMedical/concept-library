
from django.contrib.auth.mixins import LoginRequiredMixin  # , UserPassesTestMixin
# from django.contrib.messages import constants
# from django.db.models import Q
from django.db import transaction  # , models, IntegrityError
# from django.forms.models import model_to_dict
from django.http.response import JsonResponse
from django.template.loader import render_to_string
# from django.core.urlresolvers import reverse_lazy, reverse
from django.views.generic.base import TemplateResponseMixin, View

from view_utils import utils_ge_validator
from ..permissions import *
from .View import *
from clinicalcode.constants import *

