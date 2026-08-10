import os
from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Products & Catalog'

    def ready(self):
        # products/scheduler.py:start_scheduler() runs the Payuee product
        # sync every 5 hours, but nothing in the project ever called it -
        # so the scheduled sync has never actually run. Start it here,
        # but only for the actual server process (not for one-off
        # management commands like migrate/makemigrations/sync_payuee/test,
        # and not for the `runserver` autoreloader's parent watcher process).
        import sys

        argv = sys.argv
        is_management_command = len(argv) > 1 and argv[1] not in ('runserver',)
        if is_management_command:
            return

        is_runserver = len(argv) > 1 and argv[1] == 'runserver'
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            # Parent watcher process under the autoreloader - the child
            # (RUN_MAIN=true) will start the scheduler instead.
            return

        from products.scheduler import start_scheduler
        start_scheduler()
