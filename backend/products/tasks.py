import logging
from payments.payuee_client import get_payuee_client
from products.models import Category, Product
from django.utils.text import slugify

logger = logging.getLogger(__name__)


def sync_payuee_products(max_pages=5, category='all'):
    """
    Sync products from Payuee API to local database.
    This function is called by Django-Q2 scheduler every 5 hours.
    """
    logger.info("=" * 50)
    logger.info("Starting Payuee product sync...")
    
    try:
        client = get_payuee_client()
        result = client.get_all_store_products(
            max_pages=max_pages,
            category=category,
            max_distance=10000
        )
        
        if not result.get('success'):
            logger.error(f"Payuee sync failed: {result.get('error')}")
            return {'success': False, 'error': result.get('error')}
        
        data = result.get('data', {})
        products = data.get('success', [])
        
        logger.info(f"Fetched {len(products)} products from Payuee")
        
        synced = 0
        failed = 0
        
        for p in products:
            try:
                _sync_single_product(p)
                synced += 1
            except Exception as e:
                logger.error(f"Failed to sync product {p.get('ID')}: {e}")
                failed += 1
                continue
        
        logger.info(f"Payuee sync complete: {synced} synced, {failed} failed")
        logger.info("=" * 50)
        
        return {
            'success': True,
            'synced': synced,
            'failed': failed,
            'total': len(products)
        }
        
    except Exception as e:
        logger.exception("Unexpected error during Payuee sync")
        return {'success': False, 'error': str(e)}


def _sync_single_product(p):
    """Sync a single Payuee product to local DB."""
    product_id = p.get('ID')
    if not product_id:
        raise ValueError("Product has no ID")
    
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
    category_obj, _ = Category.objects.get_or_create(
        slug=category_slug,
        defaults={'name': category_name, 'is_active': True}
    )
    
    # Update or create product
    Product.objects.update_or_create(
        payuee_product_id=str(product_id),
        defaults={
            'name': p['title'],
            'slug': slug,
            'description': p.get('description', ''),
            'short_description': p.get('description', '')[:200] if p.get('description') else '',
            'price': p['selling_price'],
            'compare_at_price': p.get('initial_cost', p['selling_price']),
            'quantity': p.get('stock_remaining', 0),
            'category': category_obj,
            'featured_image': featured_image,
            'source': 'payuee',
            'status': 'active' if p.get('stock_remaining', 0) > 0 else 'out_of_stock',
            'is_featured': p.get('featured', False),
            'average_rating': 0,
            'review_count': p.get('product_review_count', 0),
        }
    )