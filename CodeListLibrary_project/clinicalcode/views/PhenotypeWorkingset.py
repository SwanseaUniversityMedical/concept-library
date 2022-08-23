from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic import CreateView

from clinicalcode import db_utils
from clinicalcode.forms import WorkingsetForms
from clinicalcode.models import PhenotypeWorkingset
from clinicalcode.permissions import HasAccessToEditConceptCheckMixin, getGroups
from clinicalcode.views.Concept import MessageMixin


class PhenotypeWorkingsetCreate(LoginRequiredMixin, HasAccessToEditConceptCheckMixin,MessageMixin,CreateView):
    model = PhenotypeWorkingset
    form = WorkingsetForms
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
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def form_invalid(self, form):
        context = self.get_context_data()
        return self.render_to_response(context)
    
    def form_valid(self, form):
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






