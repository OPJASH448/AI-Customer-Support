#!/usr/bin/env python
"""
Verify Django project setup and dependencies.
Run with: python verify_setup.py
"""
import os
import sys
import importlib

def check_environment():
    """Verify environment variables and Python version."""
    print("✓ Checking environment...")
    
    if sys.version_info < (3, 9):
        print("  ✗ Python 3.9+ required")
        return False
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    return True


def check_dependencies():
    """Verify all required packages are installed."""
    print("\n✓ Checking dependencies...")
    
    required_packages = [
        'django',
        'rest_framework',
        'corsheaders',
        'environ',
        'psycopg2',
        'pgvector',
        'celery',
        'redis',
        'openai',
        'rest_framework_simplejwt',
        'gunicorn',
        'whitenoise',
    ]
    
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n  Run: pip install {' '.join(missing)}")
        return False
    
    return True


def check_settings():
    """Verify Django settings module."""
    print("\n✓ Checking Django settings...")
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()
        
        from django.conf import settings
        print("  ✓ Settings module loaded")
        print(f"  ✓ DEBUG = {settings.DEBUG}")
        print(f"  ✓ Installed apps: {len(settings.INSTALLED_APPS)} apps")
        
        return True
    except Exception as e:
        print(f"  ✗ Settings error: {str(e)}")
        return False


def check_database():
    """Check database configuration."""
    print("\n✓ Checking database configuration...")
    
    try:
        from django.conf import settings
        db_config = settings.DATABASES['default']
        engine = db_config.get('ENGINE', 'Unknown')
        print(f"  ✓ Database engine: {engine}")
        
        # Try connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
        print("  ✓ Database connection successful")
        
        return True
    except Exception as e:
        print(f"  ✗ Database error: {str(e)}")
        print("  → Ensure DATABASE_URL is set in .env or local database is running")
        return False


def check_models():
    """Verify Django models."""
    print("\n✓ Checking models...")
    
    try:
        from support.models import Document, DocumentChunk, Conversation, Message, EscalationTicket
        from accounts.models import UserProfile
        
        print("  ✓ Document model")
        print("  ✓ DocumentChunk model")
        print("  ✓ Conversation model")
        print("  ✓ Message model")
        print("  ✓ EscalationTicket model")
        print("  ✓ UserProfile model")
        
        return True
    except Exception as e:
        print(f"  ✗ Model error: {str(e)}")
        return False


def check_celery():
    """Verify Celery configuration."""
    print("\n✓ Checking Celery...")
    
    try:
        from config.celery import app
        print("  ✓ Celery app initialized")
        
        from django.conf import settings
        broker = settings.CELERY_BROKER_URL
        backend = settings.CELERY_RESULT_BACKEND
        
        print(f"  ✓ Broker: {broker[:30]}...")
        print(f"  ✓ Backend: {backend[:30]}...")
        
        return True
    except Exception as e:
        print(f"  ✗ Celery error: {str(e)}")
        return False


def main():
    """Run all checks."""
    print("=" * 50)
    print("Django Project Verification")
    print("=" * 50)
    
    checks = [
        check_environment,
        check_dependencies,
        check_settings,
        check_database,
        check_models,
        check_celery,
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"\n✗ Unexpected error in {check.__name__}: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 50)
    if all(results):
        print("✓ All checks passed! Project is ready.")
        return 0
    else:
        print("✗ Some checks failed. See above for details.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
