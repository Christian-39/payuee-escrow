import logging
from celery import shared_task
from payments.payuee_client import get_payuee_client
from products.views import sync_payuee_products_to_db

logger = logging.getLogger(__name__)


@shared_task(
    name='products.sync_payuee_products',
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min
)
def sync_payuee_products(self, max_pages=5, category='all'):
    """
    Sync products from Payuee API to local database.

    Runs on the Celery beat schedule (see CELERY_BEAT_SCHEDULE in
    gadgethub/settings.py, every 5 hours) and can also be called directly
    or via `manage.py sync_payuee`. This replaces the old
    products/scheduler.py `threading` loop, which duplicated itself if the
    web process was ever scaled to more than one worker - Celery beat
    guarantees a single scheduled dispatch regardless of how many web/
    worker processes are running.
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
            # Transient failures (network errors, Payuee 5xx) are worth a
            # retry via Celery's own backoff rather than silently waiting
            # for the next 5-hour beat tick.
            raise self.retry(exc=Exception(result.get('error', 'Payuee sync failed')))

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
