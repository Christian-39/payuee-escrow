import logging
from payments.payuee_client import get_payuee_client
from products.views import sync_payuee_products_to_db

logger = logging.getLogger(__name__)


def sync_payuee_products(max_pages=5, category='all'):
    """
    Sync products from Payuee API to local database.
    This function is called by Django-Q2 scheduler every 5 hours
    (see products/scheduler.py) and by `manage.py sync_payuee`.
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

        synced, failed = sync_payuee_products_to_db(products)

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
