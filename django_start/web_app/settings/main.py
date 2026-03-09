"""
Base django settings
"""
import os
from pathlib import Path

from envparse import env
from split_settings.tools import include
from dotenv import load_dotenv

from django_start.web_app.settings.utils import parse_str_to_list

load_dotenv()

BASE_DIR = Path(__file__).parents[2]

include(
    '_database.py',
    '_log_config.py',
    '_cache.py',
    '_redis.py',
    '_cors.py',
    '_rest.py',
    '_celery.py',
)

PROJECT_ROOT = BASE_DIR

SECRET_KEY = env.str('SECRET_KEY', default='')

DEBUG = env.bool('DEBUG', default=False)
ENV_TYPE = env.str('ENV', default='DEV')

FILE_UPLOAD_MAX_MEMORY_SIZE = env.int('FILE_UPLOAD_MAX_MEMORY_SIZE', default=2621440)  # 2.5 MB

INTERNAL_IPS = parse_str_to_list('INTERNAL_IPS', default=[])

SESSION_COOKIE_AGE = env.int('SESSION_COOKIE_AGE', default=1200)  # 20 мин
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
SESSION_COOKIE_SAMESITE = env.str('SESSION_COOKIE_SAMESITE', default='Lax')
if SESSION_COOKIE_SAMESITE == 'None':
    SESSION_COOKIE_SAMESITE = None

CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)
CSRF_COOKIE_SAMESITE = env.str('CSRF_COOKIE_SAMESITE', default='Lax')
if CSRF_COOKIE_SAMESITE == 'None':
    CSRF_COOKIE_SAMESITE = None

CSRF_TRUSTED_ORIGINS = parse_str_to_list('CSRF_TRUSTED_ORIGINS', default=[])

# Application definition
REQUIRED_APPS = [
    "django.contrib.admin",
    "django.contrib.sites",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.admindocs",
    "rest_framework",
    "django_celery_beat",
    "drf_yasg",
]

PROJECT_APPS = [
    'web_app',
    'celery_misc.celery_monitoring',
    'django_json_widget'
]

INSTALLED_APPS = ['corsheaders'] + REQUIRED_APPS + PROJECT_APPS

SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'web_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [
            os.path.join(BASE_DIR, "templates").replace('\\', '/')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors':
                (
                    'django.contrib.auth.context_processors.auth',
                    'django.template.context_processors.debug',
                    'django.template.context_processors.i18n',
                    'django.template.context_processors.media',
                    'django.template.context_processors.static',
                    'django.template.context_processors.tz',
                    'django.template.context_processors.csrf',
                    'django.template.context_processors.request',
                    'django.contrib.messages.context_processors.messages',
                )
        }
    },
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

WSGI_APPLICATION = 'web_app.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru'
LANGUAGES = [
    ('ru', 'Russian'),
]
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

CMS_TEMPLATES = (
    ('fullwidth.html', 'Fullwidth'),
    ('sidebar_left.html', 'Sidebar Left'),
    ('sidebar_right.html', 'Sidebar Right')
)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_DIRS = (
    # os.path.join(BASE_DIR, 'static'),
)

STATIC_ROOT = os.path.join(BASE_DIR, "public")
STATIC_URL = "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
FILE_UPLOAD_PERMISSIONS = 0o644

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_SAVE_EVERY_REQUEST = True
AUTH_PROFILE_MODULE = 'app'

ALLOWED_HOSTS = parse_str_to_list('ALLOWED_HOSTS', default=["*"])
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
