import logging

logger = logging.getLogger(__name__)


def sync_payuee_products(max_pages=5, category='all'):
    """
    PAYUEE SYNC DISABLED.
    
    This function previously synced products from Payuee API to local database.
    It has been disabled to prevent Payuee products from being stored on your device.
    Only manually-added local products will be displayed.
    """
    logger.info("Payuee product sync is disabled. Only local products are supported.")
    return {
        'success': True,
        'synced': 0,
        'failed': 0,
        'total': 0,
        'message': 'Payuee sync is disabled. Only local products are supported.'
    }


def _sync_single_product(p):
    """
    PAYUEE SYNC DISABLED.
    
    This helper previously synced a single Payuee product to local DB.
    Disabled to save device storage space.
    """
    logger.info("Payuee single product sync is disabled.")
    return None
