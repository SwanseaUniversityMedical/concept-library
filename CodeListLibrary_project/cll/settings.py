"""
Django settings for cll project.

For the full list of settings and their values, see
https://docs.djangoproject.com/
"""

import distutils
import os
import socket
import sys
from distutils import util

import ldap
from decouple import Config, Csv, RepositoryEnv
from django.conf.global_settings import AUTHENTICATION_BACKENDS, EMAIL_BACKEND
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
#from django.core.urlresolvers import reverse_lazy
from django.urls import reverse_lazy
from django_auth_ldap.config import (GroupOfNamesType, LDAPSearch,
                                     LDAPSearchUnion,
                                     NestedActiveDirectoryGroupType)


def GET_SERVER_IP(TARGET_IP='10.255.255.255', PORT=1):
    """
        returns the server IP
    """
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


SRV_IP = GET_SERVER_IP()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_env_value(env_variable, cast=None):
    try:
        if cast == None:
            return os.environ[env_variable]
        elif cast == 'int':
            return int(os.environ[env_variable])
        elif cast == 'bool':
            return bool(distutils.util.strtobool(os.environ[env_variable]))
        else:
            return os.environ[env_variable]
    except KeyError:
        error_msg = 'Set the {} environment variable'.format(env_variable)
        raise ImproperlyConfigured(error_msg)


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

#==========================================================================
# separate settings for different environments
# general variables
IS_DEMO = get_env_value('IS_DEMO', cast='bool')

CLL_READ_ONLY = get_env_value('CLL_READ_ONLY', cast='bool')

# This variable was used for dev/admin and no longer maintained
#ENABLE_PUBLISH = True   # get_env_value('ENABLE_PUBLISH', cast='bool')

SHOWADMIN = get_env_value('SHOWADMIN', cast='bool')
BROWSABLEAPI = get_env_value('BROWSABLEAPI', cast='bool')

IS_INSIDE_GATEWAY = get_env_value('IS_INSIDE_GATEWAY', cast='bool')
IS_DEVELOPMENT_PC = get_env_value('IS_DEVELOPMENT_PC', cast='bool')
if IS_DEVELOPMENT_PC:
    print("SRV_IP=" + SRV_IP)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_value('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_value('DEBUG', cast='bool')

ADMIN = [('Muhammad', 'Muhammad.Elmessary@Swansea.ac.uk'),
         ('Dan', 'd.s.thayer@swansea.ac.uk')]

ALLOWED_HOSTS = [i.strip() for i in get_env_value('ALLOWED_HOSTS').split(",")]

ROOT_URLCONF = 'cll.urls'
DATA_UPLOAD_MAX_MEMORY_SIZE = None

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

CLINICALCODE_SESSION_ID = 'concept'

#===========================================================================

os.environ["DJANGO_SETTINGS_MODULE"] = "cll.settings"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'cll/static'),
]

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticroot')

WSGI_APPLICATION = 'cll.wsgi.application'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # SCSS compilation
    'sass_processor.finders.CssFinder',
    # Compressor
    'compressor.finders.CompressorFinder',
)

# Compressor options
COMPRESS_ENABLED = not DEBUG

# SCSS options
SASS_PROCESSOR_ENABLED = True
SASS_PROCESSOR_AUTO_INCLUDE = True
SASS_PROCESSOR_INCLUDE_FILE_PATTERN = r'^.+\.scss$'
SASS_OUTPUT_STYLE = 'expanded' if DEBUG else 'compressed'

# Binding and connection options
# LDAP authentication  =======================================================
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
#==============================================================================

# Application definition
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
    # SCSS
    'sass_processor',
    # Compressor - asset management
    'compressor'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # manages sessions across requests
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # associates users with requests using sessions
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'cll.middleware.brandMiddleware'
]

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
    'DEFAULT_PERMISSION_CLASSES':
    ('rest_framework.permissions.IsAuthenticated', ),
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
                'cll.context_processors.general_var',
            ],
            'libraries': {
                'breadcrumbs': 'clinicalcode.templatetags.breadcrumbs',
                'entity_renderer': 'clinicalcode.templatetags.entity_renderer',
                'detail_pg_renderer': 'clinicalcode.templatetags.detail_pg_renderer',
            }
        },
    },
]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

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

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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

GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = reverse_lazy('concept_list')
LOGIN_URL = reverse_lazy('login')
LOGOUT_URL = reverse_lazy('logout')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

MESSAGE_TAGS = {messages.ERROR: 'danger'}

CURRENT_BRAND = ""
CURRENT_BRAND_WITH_SLASH = ""
BRAND_OBJECT = {}

if not DEBUG:
    SESSION_COOKIE_AGE = 3600  # 1 hour

DEV_PRODUCTION = ""
if IS_DEMO:  # Demo server
    DEV_PRODUCTION = "<i class='glyphicon glyphicon-cog'  aria-hidden='true'> </i> DEMO SITE <i class='glyphicon glyphicon-cog'  aria-hidden='true'> </i>"

##EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Email, contact us page
DEFAULT_FROM_EMAIL = get_env_value('DEFAULT_FROM_EMAIL')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = get_env_value('EMAIL_USE_TLS', cast='bool')
EMAIL_HOST = get_env_value('EMAIL_HOST')
EMAIL_PORT = get_env_value('EMAIL_PORT')
GOOGLE_RECAPTCHA_SECRET_KEY = get_env_value('GOOGLE_RECAPTCHA_SECRET_KEY')
EMAIL_HOST_PASSWORD = get_env_value('EMAIL_HOST_PASSWORD')
EMAIL_HOST_USER = get_env_value('EMAIL_HOST_USER')
HELPDESK_EMAIL = get_env_value('HELPDESK_EMAIL')

IS_HDRUK_EXT = "0"
SHOW_COOKIE_ALERT = True

# MARKDOWNIFY
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

# CELERY SETTINGS

CELERY_BROKER_URL = 'redis://localhost:6379/0' if IS_DEVELOPMENT_PC else 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'

CELERY_RESULT_BACKEND = 'django-db'

#CELERY BEAT
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Swagger
# SWAGGER_SETTINGS = {
#                     'JSON_EDITOR': True,
# }

# Setup support for proxy headers
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SWAGGER_TITLE = "Concept Library API"


# Default primary key field type
# Django >= 3.2
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CSRF_TRUSTED_ORIGINS = [
    'https://*.saildatabank.com',
    'https://phenotypes.healthdatagateway.org',
    'http://conceptlibrary.serp.ac.uk',
    'http://conceptlibrary.sail.ukserp.ac.uk'
]



