from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Products & Catalog'

    def ready(self):
        # PAYUEE SYNC DISABLED — Only local products are shown
        # The scheduler has been disabled to prevent Payuee products
        # from being synced and stored on your device.
        pass
