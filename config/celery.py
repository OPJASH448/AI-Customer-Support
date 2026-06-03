from celery import Celery
import os
import platform

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Windows is unstable with prefork/spawn pools for many workloads.
# Force a safer pool mode locally to avoid WinError handle issues.
if platform.system().lower().startswith('win'):
	app.conf.worker_pool = 'solo'
	app.conf.worker_concurrency = 1
