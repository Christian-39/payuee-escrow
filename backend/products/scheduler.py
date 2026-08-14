"""
DEPRECATED - no longer used.

This thread-based scheduler has been replaced by Celery beat (see
`products.sync_payuee_products` in products/tasks.py and
CELERY_BEAT_SCHEDULE in gadgethub/settings.py), which fixes the original
duplication risk properly (a single beat process dispatches the task
regardless of how many web/worker processes exist) rather than papering
over it with a Redis lock.

Kept in the repo only for reference / in case of a rollback; nothing
imports or calls this module anymore (products/apps.py no longer starts
it).
"""

import threading
import time
import logging
from django.conf import settings
from django.utils import timezone

from products.tasks import sync_payuee_products

logger = logging.getLogger(__name__)

_scheduler_thread = None

_SYNC_LOCK_KEY = 'payuee:scheduler:sync-lock'
_SYNC_LOCK_TTL = 60 * 30


def _try_acquire_sync_lock():
    try:
        import redis
        client = redis.from_url(getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'))
        return bool(client.set(_SYNC_LOCK_KEY, '1', nx=True, ex=_SYNC_LOCK_TTL))
    except Exception as e:
        logger.warning(f"Scheduler lock unavailable ({e}) - proceeding without it.")
        return True


def _run_sync_loop():
    """Background thread that runs sync every 5 hours."""
    # Wait 30 seconds on startup for Django to fully initialize
    time.sleep(30)
    
    while True:
        try:
            if _try_acquire_sync_lock():
                logger.info("=" * 50)
                logger.info(f"[{timezone.now()}] Running scheduled Payuee sync...")
                result = sync_payuee_products(max_pages=5, category='all')
                logger.info(f"Sync result: {result}")
            else:
                logger.info("Skipping scheduled Payuee sync - another worker already holds the lock.")
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