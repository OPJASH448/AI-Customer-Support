from .base import *

# SECURITY
DEBUG = True
ALLOWED_HOSTS = ['*']

# Database - PostgreSQL with Docker (same as production, but local)
if env('DATABASE_URL', default=''):
    DATABASES = {
        'default': env.db('DATABASE_URL')
    }
    DATABASES['default']['CONN_MAX_AGE'] = 60
    DATABASES['default']['OPTIONS'] = {'sslmode': 'require'}
else:
    DATABASES = {
        'default': {
            'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
            'NAME': env('DB_NAME', default='ai_support'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default='password'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5433'),
            'CONN_MAX_AGE': 60,   # keep DB connections alive for 60 s
        }
    }

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

# Celery in local development
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6380/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6380/0')

if CELERY_BROKER_URL.startswith('rediss://'):
    import ssl
    CELERY_BROKER_USE_SSL = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }
    CELERY_REDIS_BACKEND_USE_SSL = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }

# When Redis is not running locally, run tasks synchronously in the same
# process.  This means upload will block until processing finishes, but
# the document will ALWAYS end up 'ready' (never stuck at 'processing').
# Set to False and start a Celery worker when you want true async.
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True   # surface exceptions in eager mode

# Prevent a single task from hanging the worker indefinitely
CELERY_TASK_SOFT_TIME_LIMIT = 300   # 5 min — raises SoftTimeLimitExceeded
CELERY_TASK_TIME_LIMIT = 360        # 6 min — hard kill

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
