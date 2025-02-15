from django.http import HttpResponse
from django.conf import settings
from django_minify_html.middleware import MinifyHtmlMiddleware

import minify_html

class HTMLCompressionMiddleware(MinifyHtmlMiddleware):
    """
        HTML minifier middleware to determine how and whether to compress a HTML response
    """
    minify_args = {
        'keep_comments': False,
        'minify_css': False,
        'minify_js': False,
    }

    def should_minify(self, request, response):
        if not settings.HTML_MINIFIER_ENABLED:
            return False

        if request.path.startswith('/admin/'):
            return False

        is_minifiable = super().should_minify(request, response)
        return is_minifiable
