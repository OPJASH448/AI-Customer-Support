from .base import *

# SECURITY
DEBUG = True
ALLOWED_HOSTS = ['*']

# Database - SQLite for local development (instant, zero setup)
# Switch to PostgreSQL later when deploying to Render
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
