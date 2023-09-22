"""
Django settings for cll project.

For the full list of settings and their values, see
https://docs.djangoproject.com/
"""

from datetime import timedelta
from django.urls import reverse_lazy
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.config import (LDAPSearch,
                                     LDAPSearchUnion,
                                     NestedActiveDirectoryGroupType)

import os
import socket
import sys
import ldap
import numbers

''' Utilities '''

def strtobool(val):
    '''
        Converts str() to bool()
        [!] Required as distutil.util.strtobool no longer
            supported in Python v3.10+ and removed in v3.12+
    '''
    if isinstance(val, bool):
        return val

    if isinstance(val, numbers.Number):
        val = str(int(val))

    if not isinstance(val, str):
        raise ValueError('Invalid paramater %r, expected <str()> but got %r' % (val,type(val)))

    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    raise ValueError('Invalid truth value %r, expected one of (\'y/n\', \'yes/no\', \'t/f\', \'true/false\', \'on/off\', \'1/0\')' % (val,))

def GET_SERVER_IP(TARGET_IP='10.255.255.255', PORT=1):
    '''
        Returns the server IP
    '''
    S = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        S.connect((TARGET_IP, PORT))
        IP = S.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        S.close()
    return IP

def get_env_value(env_variable, cast=None):
    '''
        Attempts to get env variable from OS
    '''
    try:
        if cast == None:
            return os.environ[env_variable]
        elif cast == 'int':
            return int(os.environ[env_variable])
        elif cast == 'bool':
            return bool(strtobool(os.environ[env_variable]))
        else:
            return os.environ[env_variable]
    except KeyError:
        error_msg = 'Set the {} environment variable'.format(env_variable)
        raise ImproperlyConfigured(error_msg)

#==============================================================================#

''' Application base '''

APP_TITLE = 'Concept Library'
APP_DESC = 'The {app_title} is a system for storing, managing, sharing, and documenting clinical code lists in health research.'
APP_LOGO_PATH = 'img/'
APP_EMBED_ICON = '{logo_path}embed_img.png'
INDEX_PATH = 'clinicalcode/index.html'

ADMIN = [
    ('Muhammad', 'Muhammad.Elmessary@Swansea.ac.uk'),
    ('Dan', 'd.s.thayer@swansea.ac.uk')
]

#==============================================================================#

''' Application settings '''

SRV_IP = GET_SERVER_IP()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# check OS
IS_LINUX = False
if os.name.lower() == "nt":
    path_prj = BASE_DIR  # windows os
    IS_LINUX = False
else:
    path_prj = BASE_DIR  # Linux
    IS_LINUX = True

if path_prj not in sys.path:
    sys.path.append(path_prj)

#==============================================================================#

''' Application variables '''

# separate settings for different environments
IS_DEMO = get_env_value('IS_DEMO', cast='bool')

CLINICALCODE_SESSION_ID = 'concept'

CLL_READ_ONLY = get_env_value('CLL_READ_ONLY', cast='bool')

IS_INSIDE_GATEWAY = get_env_value('IS_INSIDE_GATEWAY', cast='bool')
IS_DEVELOPMENT_PC = get_env_value('IS_DEVELOPMENT_PC', cast='bool')
if IS_DEVELOPMENT_PC:
    print("SRV_IP=" + SRV_IP)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_value('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_value('DEBUG', cast='bool')

# Allowed application hots
ALLOWED_HOSTS = [i.strip() for i in get_env_value('ALLOWED_HOSTS').split(",")]

ROOT_URLCONF = 'cll.urls'
DATA_UPLOAD_MAX_MEMORY_SIZE = None

# Setup support for proxy headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'https://*.saildatabank.com',
    'https://phenotypes.healthdatagateway.org',
    'http://conceptlibrary.serp.ac.uk',
    'http://conceptlibrary.sail.ukserp.ac.uk'
]

# This variable was used for dev/admin and no longer maintained
#ENABLE_PUBLISH = True   # get_env_value('ENABLE_PUBLISH', cast='bool')
SHOWADMIN = get_env_value('SHOWADMIN', cast='bool')
BROWSABLEAPI = get_env_value('BROWSABLEAPI', cast='bool')

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

os.environ["DJANGO_SETTINGS_MODULE"] = "cll.settings"

#==============================================================================#

''' Site related variables '''

## Brand related settings
IS_HDRUK_EXT = "0"
CURRENT_BRAND = ""
CURRENT_BRAND_WITH_SLASH = ""
BRAND_OBJECT = {}

## Graph settings
GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

## Message template settings
MESSAGE_TAGS = {messages.ERROR: 'danger'}

### Icon settings for demo sites, incl. cookie alert(s)
DEV_PRODUCTION = ""
if IS_DEMO:  # Demo server
    DEV_PRODUCTION = "<i class='glyphicon glyphicon-cog'  aria-hidden='true'>&#9881; </i> DEMO SITE <i class='glyphicon glyphicon-cog'  aria-hidden='true'>&#9881; </i>"

SHOW_COOKIE_ALERT = True

#==============================================================================#

''' LDAP authentication '''

# Binding and connection options
ENABLE_LDAP_AUTH = get_env_value('ENABLE_LDAP_AUTH', cast='bool')

AUTH_LDAP_SERVER_URI = get_env_value('AUTH_LDAP_SERVER_URI')
AUTH_LDAP_BIND_DN = get_env_value('AUTH_LDAP_BIND_DN')

AUTH_LDAP_BIND_PASSWORD = get_env_value('AUTH_LDAP_BIND_PASSWORD')

AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(LDAPSearch(get_env_value('AUTH_LDAP_USER_SEARCH'), ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"), )

# Set up the basic group parameters.
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(get_env_value('AUTH_LDAP_GROUP_SEARCH'), ldap.SCOPE_SUBTREE, "(objectClass=group)")

AUTH_LDAP_GROUP_TYPE = NestedActiveDirectoryGroupType()

# Simple group restrictions
AUTH_LDAP_REQUIRE_GROUP = get_env_value('AUTH_LDAP_REQUIRE_GROUP')

# Populate the django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail"
}

# This is the default, but I like to be explicit.
AUTH_LDAP_ALWAYS_UPDATE_USER = True

# Use LDAP group membership to calculate group permissions.
AUTH_LDAP_FIND_GROUP_PERMS = True

# Cache group memberships for an hour to minimize LDAP traffic
AUTH_LDAP_CACHE_GROUPS = True
AUTH_LDAP_GROUP_CACHE_TIMEOUT = 3600

#==============================================================================#

''' Installed applications '''

INSTALLED_APPS = []
if SHOWADMIN:
    INSTALLED_APPS = INSTALLED_APPS + [
        'django.contrib.admin',
    ]

INSTALLED_APPS = INSTALLED_APPS + [
    'django.contrib.postgres',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mathfilters',
    'clinicalcode',
    'cll',
    'simple_history',
    'rest_framework',
    #'mod_wsgi.server',
    'django_extensions',
    'markdownify',
    'cookielaw',
    'django_celery_results',
    'django_celery_beat',
    #'rest_framework_swagger',
    'drf_yasg',
    'django.contrib.sitemaps',
    'svg',
    # SCSS
    'sass_processor',
    # Compressor
    'compressor',
    # HTML Minifier
    'django_minify_html',
]

#==============================================================================#


''' Middleware '''

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # GZip
    'django.middleware.gzip.GZipMiddleware',
    # Manage sessions across requests
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Associates users with requests using sessions
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    # Minify HTML
    'clinicalcode.middleware.compression.HTMLCompressionMiddleware',
    # Handle brands
    'clinicalcode.middleware.brands.BrandMiddleware',
    # Handle user session expiry
    'clinicalcode.middleware.sessions.SessionExpiryMiddleware',
]

#==============================================================================#

''' Authentication backends '''

# Keep ModelBackend around for per-user permissions and a local superuser.
# Don't check AD on development PCs due to network connection
if IS_DEVELOPMENT_PC or (not ENABLE_LDAP_AUTH):
    AUTHENTICATION_BACKENDS = [
        #'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]
else:
    AUTHENTICATION_BACKENDS = [
        'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]

# Password validation, ref @ https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

#==============================================================================#

''' REST framework settings '''

REST_FRAMEWORK = {
    #     'DEFAULT_RENDERER_CLASSES': (
    #         'rest_framework.renderers.JSONRenderer',
    #         'rest_framework_xml.renderers.XMLRenderer',
    #         'rest_framework.renderers.BrowsableAPIRenderer',
    #     ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # 'DEFAULT_PARSER_CLASSES': (
    #     'rest_framework.parsers.FileUploadParser',
    #     'rest_framework.parsers.JSONParser',
    #     'rest_framework.parsers.FormParser',
    #     'rest_framework.parsers.MultiPartParser',
    # ),
}

if not BROWSABLEAPI:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
    )

#==============================================================================#

''' Templating settings '''

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cookielaw.context_processors.cookielaw',
                'clinicalcode.context_processors.general.general_var',
            ],
            'libraries': {
                'breadcrumbs': 'clinicalcode.templatetags.breadcrumbs',
                'entity_renderer': 'clinicalcode.templatetags.entity_renderer',
                'detail_pg_renderer': 'clinicalcode.templatetags.detail_pg_renderer',
            }
        },
    },
]

#==============================================================================#

''' Database settings '''

# Databases, ref @ https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_env_value('DB_NAME'),
        'USER': get_env_value('DB_USER'),
        'PASSWORD': get_env_value('DB_PASSWORD'),
        'HOST': get_env_value('DB_HOST'),
        'PORT': '',
    }
}

# sslmode is required for production DB
if not IS_DEMO and (not IS_DEVELOPMENT_PC):
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

#==============================================================================#

''' Caching '''

if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://redis:6379/0',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            },
            'KEY_PREFIX': 'cll',
        }
    }

#==============================================================================#

''' Static file handling & serving '''

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticroot')

WSGI_APPLICATION = 'cll.wsgi.application'

STATICFILES_STORAGE = 'clinicalcode.storage.files_manifest.NoSourceMappedManifestStaticFilesStorage'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # SCSS compilation
    'sass_processor.finders.CssFinder',
    # Compressor
    'compressor.finders.CompressorFinder',
)

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'cll/static'),
]

#==============================================================================#

''' Media file handling '''

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

#==============================================================================#

''' Application logging settings '''

if IS_LINUX or IS_DEVELOPMENT_PC:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            },
        },
    }
else:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format':
                '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
        },
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': os.path.join(BASE_DIR, 'debug.log'),
            },
            'stream_to_console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler'
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'django_auth_ldap': {
                'handlers': ['stream_to_console'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

#==============================================================================#

''' Installed application settings '''

# General settings

## Django auth settings -> Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = reverse_lazy('search_phenotypes')
LOGIN_URL = reverse_lazy('login')
LOGOUT_URL = reverse_lazy('logout')

## User session expiry for middleware.SessionExpiryMiddleware
SESSION_EXPIRY = {
    # i.e. logout after 1 week (optional)
    'SESSION_LIMIT': timedelta(weeks=1),
    # i.e. logout after 1 day if no requests were made during this time (optional)
    'IDLE_LIMIT': timedelta(days=1),
}

## Django cookie session settings
if not DEBUG:
    SESSION_COOKIE_AGE = 3600  # 1 hour

## Default primary key field type - Django >= 3.2
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

## HTML Minifier
HTML_MINIFIER_ENABLED = True

## Compressor options
COMPRESS_ENABLED = not DEBUG
COMPRESS_OFFLINE = True
COMPRESS_URL = STATIC_URL
COMPRESS_ROOT = STATIC_ROOT

if not DEBUG:
    COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'
    COMPRESS_PRECOMPILERS = (
        ('module', 'esbuild {infile} --bundle --outfile={outfile}'),
    )

## SASS options
SASS_PROCESSOR_ENABLED = True
SASS_PROCESSOR_AUTO_INCLUDE = True
SASS_PROCESSOR_INCLUDE_FILE_PATTERN = r'^.+\.scss$'
SASS_OUTPUT_STYLE = 'expanded' if DEBUG else 'compressed'

## CAPTCHA
### To ignore captcha during debug builds
try:
    IGNORE_CAPTCHA = get_env_value('IGNORE_CAPTCHA')
except:
    IGNORE_CAPTCHA = False

## Email settings
###     EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = get_env_value('DEFAULT_FROM_EMAIL')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = get_env_value('EMAIL_USE_TLS', cast='bool')
EMAIL_HOST = get_env_value('EMAIL_HOST')
EMAIL_PORT = get_env_value('EMAIL_PORT')
GOOGLE_RECAPTCHA_SECRET_KEY = get_env_value('GOOGLE_RECAPTCHA_SECRET_KEY')
EMAIL_HOST_PASSWORD = get_env_value('EMAIL_HOST_PASSWORD')
EMAIL_HOST_USER = get_env_value('EMAIL_HOST_USER')
HELPDESK_EMAIL = get_env_value('HELPDESK_EMAIL')

## Celery settings
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'django-db'

## Celery beat settings
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

## Swagger settings
##     SWAGGER_SETTINGS = { 'JSON_EDITOR': True, }
SWAGGER_TITLE = "Concept Library API"

## Markdownify settings
MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            'a', 'abbr', 'acronym', 'b', 'blockquote', 'em', 'i', 'li', 'ol',
            'p', 'strong', 'ul', 'img',
            'h1', 'h2', 'h3','h4', 'h5', 'h6', 'h7'
            #, 'span', 'div',  'code'
        ],
        "WHITELIST_ATTRS": [
            'href',
            'src',
            'alt',
            'style',
            'class',
        ],
        "WHITELIST_STYLES": [
            'color',
            'font-weight',
            'background-color',
        ],

        "MARKDOWN_EXTENSIONS": [
            'markdown.extensions.fenced_code',
            'markdown.extensions.extra',
        ],
        "WHITELIST_PROTOCOLS": [
            'http',
            'https',
        ]
    }
}

#==============================================================================#
