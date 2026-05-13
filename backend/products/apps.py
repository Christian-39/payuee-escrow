from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Products & Catalog' 

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        from products.scheduler import start_scheduler
        start_scheduler()
