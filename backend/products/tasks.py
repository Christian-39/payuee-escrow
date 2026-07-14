import logging

logger = logging.getLogger(__name__)


def sync_payuee_products(max_pages=5, category='all'):
    """
    PAYUEE SYNC DISABLED.
    
    Products are now fetched LIVE from Payuee API on every request.
    They are NOT saved to the database to save device storage.
    Only manually-added local products are stored in DB.
    """
    logger.info("Payuee DB sync is disabled. Products fetched live from API.")
    return {
        'success': True,
        'synced': 0,
        'failed': 0,
        'total': 0,
        'message': 'Payuee DB sync disabled. Products fetched live from API.'
    }


def _sync_single_product(p):
    """
    PAYUEE SYNC DISABLED.
    """
    logger.info("Payuee DB sync is disabled.")
    return None
