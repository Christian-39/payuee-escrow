import logging

logger = logging.getLogger(__name__)


def start_scheduler():
    """
    PAYUEE BACKGROUND SYNC DISABLED.
    
    Products are fetched LIVE from Payuee API per request.
    No scheduled sync runs to save device resources.
    """
    logger.info("Payuee background sync disabled. Live fetching enabled.")
    return
