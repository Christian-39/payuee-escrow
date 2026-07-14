import logging

logger = logging.getLogger(__name__)


def start_scheduler():
    """
    PAYUEE SYNC SCHEDULER DISABLED.
    
    The background sync scheduler that ran every 5 hours has been disabled.
    No Payuee products will be synced or stored on your device.
    Only manually-added local products will be available.
    """
    logger.info("Payuee background scheduler is disabled. Only local products are supported.")
    return
