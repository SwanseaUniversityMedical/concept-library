from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

class NoSourceMappedManifestStaticFilesStorage(ManifestStaticFilesStorage):
    '''
        [!] Temporary fix

        Reverts .map behaviour support added in Django 4.1.10

        Ref @ https://code.djangoproject.com/ticket/33353#comment:13
    '''
    patterns = (
        (
            "*.css",
            (
                "(?P<matched>url\\(['\"]{0,1}\\s*(?P<url>.*?)[\"']{0,1}\\))",
                (
                    "(?P<matched>@import\\s*[\"']\\s*(?P<url>.*?)[\"'])",
                    '@import url("%(url)s")',
                ),
            ),
        ),
    )
