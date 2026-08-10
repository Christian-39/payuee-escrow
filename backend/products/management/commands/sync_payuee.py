from django.core.management.base import BaseCommand
from payments.payuee_client import get_payuee_client
from products.views import sync_payuee_products_to_db
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync products from Payuee API to local database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=5,
            help='Number of pages to fetch (default: 5)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default='all',
            help='Category to sync (default: all)'
        )

    def handle(self, *args, **options):
        client = get_payuee_client()
        max_pages = options['pages']
        category = options['category']

        self.stdout.write(f"Fetching up to {max_pages} pages from Payuee (category: {category})...")

        result = client.get_all_store_products(
            max_pages=max_pages,
            category=category,
            max_distance=10000
        )

        if not result.get('success'):
            self.stderr.write(f"Failed to fetch products: {result.get('error')}")
            return

        data = result.get('data', {})
        products = data.get('success', [])

        self.stdout.write(f"Fetched {len(products)} products from Payuee")

        synced, failed = sync_payuee_products_to_db(products)

        self.stdout.write(self.style.SUCCESS(f"Successfully synced {synced} products ({failed} failed)"))
