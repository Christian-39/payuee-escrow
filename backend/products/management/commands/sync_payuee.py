from django.core.management.base import BaseCommand
from payments.payuee_client import get_payuee_client
from products.models import Category, Product
from django.utils.text import slugify
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
        
        synced = 0
        for p in products:
            try:
                product = self._sync_product(p)
                if product:
                    synced += 1
            except Exception as e:
                logger.error(f"Failed to sync product {p.get('ID')}: {e}")
                continue
        
        self.stdout.write(self.style.SUCCESS(f"Successfully synced {synced} products"))
    
    def _sync_product(self, p):
        """Sync a single Payuee product to local DB."""
        product_id = p.get('ID')
        if not product_id:
            return None
        
        # Get first image URL if available
        featured_image = None
        if p.get('product_image') and len(p['product_image']) > 0:
            image_path = p['product_image'][0]['url']
            featured_image = f"https://payuee.com/image/{image_path}"
        
        # Create slug from product_url_id or title
        slug = p.get('product_url_id', '')
        if not slug:
            slug = slugify(p['title'])[:50]
        
        # Get or create category
        category_name = p.get('category', 'others')
        category_slug = slugify(category_name)
        category, _ = Category.objects.get_or_create(
            slug=category_slug,
            defaults={'name': category_name, 'is_active': True}
        )
        
        # Update or create product
        product, created = Product.objects.update_or_create(
            payuee_product_id=str(product_id),
            defaults={
                'name': p['title'],
                'slug': slug,
                'description': p.get('description', ''),
                'short_description': p.get('description', '')[:200] if p.get('description') else '',
                'price': p['selling_price'],
                'compare_at_price': p.get('initial_cost', p['selling_price']),
                'quantity': p.get('stock_remaining', 0),
                'category': category,
                'featured_image': featured_image,
                'source': 'payuee',
                'status': 'active' if p.get('stock_remaining', 0) > 0 else 'out_of_stock',
                'is_featured': p.get('featured', False),
                'average_rating': 0,
                'review_count': p.get('product_review_count', 0),
            }
        )
        
        action = 'Created' if created else 'Updated'
        logger.info(f"{action} product: {product.name} (ID: {product_id})")
        
        return product