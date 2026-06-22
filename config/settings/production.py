from .base import *
import os

# ── Security ──────────────────────────────────────────────────────────────────
DEBUG = False

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '.onrender.com').split(',')

# Required for Django forms / DRF to accept HTTPS requests from Render domain
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
]

if not os.environ.get('SECRET_KEY'):
    raise ValueError('SECRET_KEY environment variable is required in production')

# Render handles HTTPS termination at the load balancer; Django is behind a proxy
# so we must trust the X-Forwarded-Proto header instead of redirecting ourselves.
SECURE_SSL_REDIRECT = False                 # Render proxy handles this
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ── Database (PostgreSQL via DATABASE_URL) ────────────────────────────────────
DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}

# ── File upload limits (10 MB — files go to Supabase, not local disk) ────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ── Supabase Storage ──────────────────────────────────────────────────────────
import os as _os
SUPABASE_URL = _os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = _os.environ.get('SUPABASE_KEY', '')
SUPABASE_BUCKET = _os.environ.get('SUPABASE_BUCKET', 'ai-customer-support-pdfs')

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
static_dir = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [static_dir] if os.path.isdir(static_dir) else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get('REDIS_URL', '')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', '')
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 360

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

# ── Logging ───────────────────────────────────────────────────────────────────
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
    },
}
