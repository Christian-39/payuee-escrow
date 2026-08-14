import os
from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Products & Catalog'

    def ready(self):
        # The Payuee product sync previously ran via a bespoke `threading`
        # loop started here (products/scheduler.py), which would duplicate
        # itself if this process were ever scaled to more than one worker.
        # It now runs on Celery beat's schedule instead (see
        # CELERY_BEAT_SCHEDULE in settings.py and the
        # `products.sync_payuee_products` task in products/tasks.py),
        # dispatched by a separate `celery beat` process rather than from
        # inside the web process - so nothing needs to start here anymore.
        pass
