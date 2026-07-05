from .base import *
import os

# ── Security ──────────────────────────────────────────────────────────────────
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

INTERNAL_IPS = ['127.0.0.1']

if not os.environ.get('SECRET_KEY'):
    raise ValueError('SECRET_KEY environment variable is required in production')

# AWS ALB handles HTTPS termination; Django is behind a proxy
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ── Database (RDS PostgreSQL) ─────────────────────────────────────────────────
DATABASES = {
    'default': env.db('DATABASE_URL', default='')
}
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

# ── File upload limits (10 MB — files go to Supabase/S3) ─────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ── Supabase Storage (or swap to S3 by changing serializers) ─────────────────
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'ai-customer-support-pdfs')

# ── Static files (served via WhiteNoise or S3/CDN) ───────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
static_dir = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [static_dir] if os.path.isdir(static_dir) else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Celery + ElastiCache Redis ────────────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', '')

CELERY_BROKER_URL          = REDIS_URL
CELERY_RESULT_BACKEND      = REDIS_URL
CELERY_ACCEPT_CONTENT      = ['json']
CELERY_TASK_SERIALIZER     = 'json'
CELERY_RESULT_SERIALIZER   = 'json'
CELERY_TIMEZONE            = 'UTC'

# Redis auth token (ElastiCache default uses 'default' user + auth token)
if REDIS_URL:
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'global_keyprefix': '',
        'visibility_timeout': 3600,
    }

# Task time limits — PDF processing should finish within 5 min
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_TASK_TIME_LIMIT      = 300

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES      = 10

CELERY_TASK_ACKS_LATE         = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ── Email (SES or SMTP) ──────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='email-smtp.us-east-1.amazonaws.com')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# ── Logging (stdout for CloudWatch agent to pick up) ─────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'support': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
