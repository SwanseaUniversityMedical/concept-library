from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.edit import CreateView
from collections import OrderedDict as ordr

from clinicalcode import db_utils
from clinicalcode.forms.WorkingsetForms import WorkingsetForms
from clinicalcode.models import PhenotypeWorkingset, Tag
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
            overall = [int(i) for i in data.split(",")]

        return overall

    def get_brand_collections(self, array_collections):
        queryset = Tag.objects

        rows_to_return = []
        titles = ['id', 'name','brand']

        queryset = queryset.filter(id__in=array_collections)
        for t in queryset:
            ret = [t.id, t.description,t.collection_brand.name]
            rows_to_return.append(ordr(list(zip(titles, ret))))

        return rows_to_return

    def get_form_kwargs(self):
        print('test kwarks ')
        kwargs = super(CreateView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'groups': getGroups(self.request.user)})
        return kwargs

    def form_invalid(self, form):
        print('test form invalid ')
        tag_ids = self.commaSeparate('tagids')
        collections = self.commaSeparate('collections')
        datasources = self.commaSeparate('datasources')
        context = self.get_context_data()

        if tag_ids:
            context['tags'] = Tag.objects.filter(pk__in=tag_ids)
            print(context['tags'])

        if collections:
            context['collections'] = self.get_brand_collections(collections)
            print(context['collections'])

        context['datasources'] = datasources #itarate datasources
        print(context)

        return self.render_to_response(context)

    def form_valid(self, form):
        print('test form valid ')
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.author = self.commaSeparate('author')
            form.instance.tags = self.commaSeparate('tagids')
            form.instance.collections = self.commaSeparate('collections')
            form.instance.data_sources = self.commaSeparate('datasources')
            form.instance.phenotypes_concepts_data = [{"phenotype_id": "PH3","phenotype_version_id": 6,"concept_id": "C717","concept_version_id":2573,"Attributes":[{"name": "Attributename","type":"int","value": 234}]}]


            self.object = form.save()
            db_utils.modify_Entity_ChangeReason(PhenotypeWorkingset,self.object.pk,"Created")
            print(self.object.pk)
            messages.success(self.request,"Workingset has been successfully created.")

        return HttpResponseRedirect(reverse('workingset_create'))
        # return HttpResponseRedirect(reverse('workingset_update'),args=(self.object.pk)) when update is done







