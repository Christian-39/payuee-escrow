"""
Celery application entrypoint.

CELERY_BROKER_URL / CELERY_RESULT_BACKEND / CELERY_BEAT_SCHEDULE were
already configured in settings.py, but no Celery `app` instance actually
existed anywhere in the project - so a Redis broker and result backend
sat fully configured but nothing ever imported/used them. The Payuee
product sync instead ran as a bespoke `threading` loop (see
products/scheduler.py, now unused) started from products/apps.py.

This wires up the standard Django+Celery pattern:
- `app` here is the Celery application, using Django settings for config.
- `app.autodiscover_tasks()` picks up `@shared_task`-decorated functions
  from each app's `tasks.py` (see products/tasks.py).
- CELERY_BEAT_SCHEDULE (in settings.py) replaces the old 5-hour
  `time.sleep` loop with a real, restart-safe, single-worker-guaranteed
  periodic schedule via `celery beat`.

Run in production alongside the web process (see Procfile):
    celery -A gadgethub worker -l info
    celery -A gadgethub beat -l info
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gadgethub.settings')

app = Celery('gadgethub')

# Read CELERY_* settings from Django settings.py (CELERY_BROKER_URL,
# CELERY_RESULT_BACKEND, CELERY_BEAT_SCHEDULE, etc.).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in each INSTALLED_APPS app (e.g. products/tasks.py).
app.autodiscover_tasks()
