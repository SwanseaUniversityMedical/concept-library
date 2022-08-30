from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.edit import CreateView

from clinicalcode import db_utils
from clinicalcode.forms.WorkingsetForms import WorkingsetForms
from clinicalcode.models import PhenotypeWorkingset
from ..permissions import *
from clinicalcode.views.Concept import MessageMixin


class PhenotypeWorkingsetCreate(LoginRequiredMixin,HasAccessToCreateCheckMixin,CreateView):
    model = PhenotypeWorkingset
    form_class = WorkingsetForms
    template_name = 'clinicalcode/phenotypeworkingset/form.html'

    def commaSeparate(self, id):
        data = self.request.POST.get(id)
        overall = None
        if data:
            if (type(data) == str):
                overall = [str(i) for i in data.split(",")]
            else:
                overall = [int(i) for i in data.split(",")]

        return overall

    def get_form_kwargs(self):
        print('test kwarks ')
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def form_invalid(self, form):
        print('test form invalid ')
        context = self.get_context_data()
        return self.render_to_response(context)

    def form_valid(self, form):
        print('test form valid ')
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.author = self.commaSeparate('author')
            form.instance.tags = self.commaSeparate('tagids')
            form.instance.collections = self.commaSeparate('collections')
            form.instance.data_sources = self.commaSeparate('datasources')


            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset,self.object.pk,"Created")
            workingset = PhenotypeWorkingset.objects.get(pk=self.object.pk)
            workingset.history.latest().delete()

            messages.success(self.request,"Workingset has been successfully created.")

        return HttpResponseRedirect(reverse('workingset_update'),args=(self.object.pk))







