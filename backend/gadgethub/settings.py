"""
Django settings for GadgetHub project.
Production-ready configuration with Payuee integration.
"""

import os
from pathlib import Path
from decouple import config
from dotenv import load_dotenv
import pymysql

pymysql.install_as_MySQLdb()
# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'storages',
    
    # Local apps
    'accounts',
    'products',
    'orders',
    'payments',
    'admin_dashboard',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gadgethub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'gadgethub.wsgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='3306'), 
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}


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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Media files (Images)

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Payuee's own security guidance explicitly recommends rate-limiting
    # the order-creation endpoint; previously nothing here was throttled
    # at all (login, checkout, order/create all wide open).
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'user': '120/min',
    },
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_COOKIE_ACCESS': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
}
# BLACKLIST_AFTER_ROTATION above was already set to True, but
# 'rest_framework_simplejwt.token_blacklist' was never added to
# INSTALLED_APPS (added above) - without it, simplejwt has no
# OutstandingToken/BlacklistedToken models to blacklist against, and
# every refresh-token rotation raises instead of quietly rotating. This
# is very likely the actual cause of "user logs out whenever the page
# refreshes / gets logged back in inconsistently": the very first token
# refresh after login would fail server-side, the frontend would treat
# that as a fully-expired session and clear auth state, and then
# sometimes silently log back in only because a still-valid access token
# happened to still be sitting in localStorage. Run
# `python manage.py migrate` after this change to create the blacklist
# tables.
#
# Auth tokens are now delivered as httpOnly cookies (see
# accounts/authentication.py, accounts/views.py) instead of being returned
# in the JSON body and stored in localStorage - a JS-readable/writable
# localStorage token is trivially exfiltrated by any XSS on the page;
# httpOnly cookies aren't readable from JS at all.
#
# IMPORTANT - do not derive these from DEBUG: DEBUG defaults to False in
# this project (see above), which is an easy, silent trap for this
# specific pair of settings. A `Secure` cookie is refused by every browser
# over plain http - if AUTH_COOKIE_SECURE ends up True while the app is
# actually being served over http (e.g. local `runserver`/Vite dev with
# DEBUG left at its False default, or a staging box without TLS yet), the
# browser drops the Set-Cookie for access/refresh/csrf entirely and
# *every* request looks unauthenticated - which is exactly the symptom of
# "profile/refresh 401-loop, can't add to cart, can't upload, login page
# keeps reloading": there was never a valid session cookie for the browser
# to send, on any request, from the moment login. Both flags below must be
# set explicitly and intentionally, matching how the app is actually being
# served right now (not "will eventually be served in prod"):
#   - Local http dev (runserver / Vite dev server, no TLS): leave both at
#     their defaults below (Secure=False, SameSite=Lax).
#   - Real HTTPS deployment with frontend and API on different origins:
#     set AUTH_COOKIE_SECURE=True and AUTH_COOKIE_SAMESITE=None in that
#     environment's env vars - SameSite=None additionally requires
#     Secure=True or browsers reject the cookie outright, so these two
#     must always be changed together.
AUTH_COOKIE_SECURE = config('AUTH_COOKIE_SECURE', default=False, cast=bool)
AUTH_COOKIE_SAMESITE = config('AUTH_COOKIE_SAMESITE', default='Lax')
AUTH_COOKIE_DOMAIN = config('AUTH_COOKIE_DOMAIN', default=None)

# CORS Configuration
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# django-cors-headers' default CORS_ALLOW_HEADERS does NOT include custom
# headers - it only allows a fixed standard set (accept, authorization,
# content-type, etc.). The X-CSRF-Token header (see
# accounts/authentication.py / frontend lib/api.ts) is a custom header,
# so without explicitly whitelisting it here, the browser's CORS
# preflight (OPTIONS) rejects it and blocks every cross-origin POST/PUT/
# PATCH/DELETE outright before it ever reaches Django - this is what was
# actually breaking add-to-cart, wishlist, and profile image upload (all
# non-GET requests), independent of the login-redirect-loop bug fixed in
# lib/api.ts. Must list the full set explicitly since setting this at all
# replaces django-cors-headers' default list rather than extending it.
from corsheaders.defaults import default_headers as _cors_default_headers
CORS_ALLOW_HEADERS = list(_cors_default_headers) + ['x-csrf-token']

# Payuee API Configuration
PAYUEE_API_KEY = config('PAYUEE_API_KEY')
PAYUEE_API_SECRET = config('PAYUEE_API_SECRET')
PAYUEE_BASE_URL = config('PAYUEE_BASE_URL')
# Used to verify inbound Payuee webhook signatures (separate from the API secret above).
WEBHOOK_SECRET = config('WEBHOOK_SECRET', default='')
PAYUEE_WEBHOOK_URL = config('PAYUEE_WEBHOOK_URL', default='')

# Backblaze B2 Configuration
#
# AWS_DEFAULT_ACL = 'public-read' review/confirmation: the only thing this
# app actually stores in B2 is user-uploaded profile images
# (accounts/views.py::upload_profile_image, path `profiles/<user_id>/
# <uuid>.<ext>`) - product images (`featured_image`) are plain URLField
# links to Payuee's own CDN and never touch B2 at all. Public-read is the
# correct, intended setting here: profile pictures are displayed via plain
# <img src> tags (no signed-URL infrastructure exists, and
# AWS_QUERYSTRING_AUTH=False below confirms that's deliberate), so making
# the bucket private would just break avatar display without adding any
# real protection - filenames are namespaced by a random UUID (not
# sequential/enumerable), so this is equivalent in practice to how most
# public-avatar-hosting apps work. If per-user private images are ever
# needed for a different upload type in the future, that should get its
# own non-public path/bucket rather than changing this default globally.
AWS_ACCESS_KEY_ID = config('B2_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('B2_APPLICATION_KEY', default='')
AWS_STORAGE_BUCKET_NAME = config('B2_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = config('B2_ENDPOINT', default='https://s3.us-east-005.backblazeb2.com')
AWS_S3_REGION_NAME = config('B2_REGION', default='us-east-005')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_S3_SIGNATURE_VERSION = "s3v4"

# Use S3 for media files in production
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # AWS_S3_ADDRESSING_STYLE = "virtual" means django-storages builds URLs as
    # https://{bucket}.{endpoint-host}/{key}. MEDIA_URL must match that shape
    # (path-style {endpoint}/{bucket}/ would be wrong for a virtual-hosted
    # bucket and produce broken <img> src values even though storage.url()
    # itself is computed independently and would still work).
    _b2_host = AWS_S3_ENDPOINT_URL.split('://', 1)[-1]
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.{_b2_host}/'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Periodic tasks (requires a separate `celery beat` process running - see
# Procfile). Replaces the old products/scheduler.py `threading` loop:
# beat guarantees a single dispatch on schedule regardless of how many web
# or worker processes are running, instead of every process running its
# own independent in-memory timer.
CELERY_BEAT_SCHEDULE = {
    'sync-payuee-products-every-5-hours': {
        'task': 'products.sync_payuee_products',
        'schedule': 5 * 60 * 60,  # seconds
        'kwargs': {'max_pages': 5, 'category': 'all'},
    },
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'payuee': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Security Settings
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Lax')
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Lax')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Required when SECURE_SSL_REDIRECT is on behind a reverse proxy/load
# balancer (e.g. Render) that terminates TLS itself and forwards plain
# HTTP internally - without this, Django can't tell the original request
# was HTTPS and will redirect-loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cross-origin POSTs (admin actions, checkout, etc.) from the deployed
# frontend need their origin explicitly trusted for Django's CSRF checks
# to pass in production - previously unset, so this defaulted to allowing
# none, which silently breaks any cookie/CSRF-based flow (JWT-only API
# calls in this app already sidestep it, but Django admin does not).
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173'
).split(',')
