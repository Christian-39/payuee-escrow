# Ensures the Celery app (gadgethub/celery.py) is loaded whenever Django
# starts, so `@shared_task`-decorated functions are registered correctly
# with the shared Celery app instance.
from .celery import app as celery_app

__all__ = ('celery_app',)
