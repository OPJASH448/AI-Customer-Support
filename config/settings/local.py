from .base import *

# SECURITY
DEBUG = True
ALLOWED_HOSTS = ['*']

# Database - PostgreSQL with Docker (same as production, but local)
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME', default='ai_support'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default='password'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5433'),
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

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
