"""
Base settings for Gambia Judiciary E-Filing System.
All environment-specific settings live in development.py / production.py.
"""
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# ── Application definition ─────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'storages',
]

LOCAL_APPS = [
    'apps.users',
    'apps.firms',
    'apps.cases',
    'apps.documents',
    'apps.payments',
    'apps.audit',
    'apps.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Database ───────────────────────────────────────────────────────────────
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://judiciary:judiciary@localhost:5432/judiciary_db',
        conn_max_age=600,
    )
}

# ── Custom User ────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'

# ── Password validation ────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ───────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Banjul'
USE_I18N = True
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ─────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.judiciary_exception_handler',
}

# ── JWT ────────────────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ── CORS ───────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:5173',
    'http://localhost:3000',
])
CORS_ALLOW_CREDENTIALS = True

# ── Celery ─────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ── Cache ──────────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

# ── API Schema ─────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Gambia Judiciary E-Filing API',
    'DESCRIPTION': 'National Judiciary E-Filing & Case Management System',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ── File Storage ───────────────────────────────────────────────────────────
USE_S3 = env.bool('USE_S3', default=False)

if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    STORAGES = {
        'default': {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }

# ── Notifications ──────────────────────────────────────────────────────────
SENDGRID_API_KEY = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@judiciary.gm')

TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')

# ── MUSU Payment Gateway ───────────────────────────────────────────────────
MUSU_API_BASE_URL = env('MUSU_API_BASE_URL', default='https://api.musu.gm/v1')
MUSU_MERCHANT_ID = env('MUSU_MERCHANT_ID', default='')
MUSU_API_KEY = env('MUSU_API_KEY', default='')
MUSU_WEBHOOK_SECRET = env('MUSU_WEBHOOK_SECRET', default='')

# ── Judiciary-specific settings ────────────────────────────────────────────
# Court fee configuration (in GMD)
COURT_TIERS = ['cadi', 'magistrate', 'high', 'appeal', 'supreme']

# Appeal window in days (statutory)
APPEAL_WINDOW_DAYS = 30

# Case reference number prefix
CASE_REF_PREFIX = 'GJ'
