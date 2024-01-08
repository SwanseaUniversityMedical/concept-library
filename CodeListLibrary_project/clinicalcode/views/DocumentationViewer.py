from django.http.response import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.generic import TemplateView


class DocumentationViewer(TemplateView):
    """
        Simple contextual documentation view
        for the creation wizards

        Documentation for each template can be
        set by filling out the 'documentation' field
        for the wizard's section
    """

    PAGE_BASE = 'clinicalcode/documentation/index.html'
    PAGE_TITLES = {
        'clinical-coded-phenotype-docs': 'Clinical Coded Phenotype Documentation',
    }

    def get(self, request, *args, **kwargs):
        """
            Matches the given documentation kwarg
            with the appropriate page
        """
        documentation = kwargs.get('documentation')
        if not documentation:
            raise Http404

        title = self.PAGE_TITLES.get(documentation)
        if not title:
            raise PermissionDenied

        docs = {
            'title': title,
            'page': f'clinicalcode/documentation/views/{documentation}.html',
        }

        return render(request, self.PAGE_BASE, {'docs': docs})
