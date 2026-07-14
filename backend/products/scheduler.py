import threading
import time
import logging
from django.utils import timezone

from products.tasks import sync_payuee_products

logger = logging.getLogger(__name__)

_scheduler_thread = None


def _run_sync_loop():
    """Background thread that runs sync every 5 hours."""
    # Wait 30 seconds on startup for Django to fully initialize
    time.sleep(30)
    
    while True:
        try:
            logger.info("=" * 50)
            logger.info(f"[{timezone.now()}] Running scheduled Payuee sync...")
            result = sync_payuee_products(max_pages=5, category='all')
            logger.info(f"Sync result: {result}")
        except Exception as e:
            logger.exception("Scheduled sync failed")
        
        # Sleep for 5 hours
        logger.info("Next sync in 5 hours...")
        time.sleep(5 * 60 * 60)  # 5 hours in seconds


def start_scheduler():
    """Start the background sync scheduler."""
    global _scheduler_thread
    
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        logger.info("Scheduler already running")
        return
    
    _scheduler_thread = threading.Thread(target=_run_sync_loop, daemon=True)
    _scheduler_thread.start()
    logger.info("Background scheduler started: Payuee sync every 5 hours")