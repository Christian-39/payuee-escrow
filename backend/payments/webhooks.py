"""
Webhook handlers for Payuee.
Processes incoming webhooks from Payuee's escrow system.

Docs: https://payuee.com/doc/documentation#webhooks-system
Documented event types: order.created, order.on_hold, order.scanned,
order.delivered, order.refunded, order.cancelled, order.report.
"""

import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .payuee_client import PayueeClient
from orders.models import Order, OrderStatusHistory

logger = logging.getLogger('payuee')


@csrf_exempt
@require_http_methods(["POST"])
def payuee_webhook(request):
    """Handle incoming webhooks from Payuee."""

    # Signature verification must run against the *raw* body bytes, before
    # any JSON parsing/re-serialization (parsed-then-reserialized JSON can
    # differ byte-for-byte from what Payuee signed).
    raw_body = request.body

    signature = request.headers.get('X-Payuee-Signature', '')
    timestamp = request.headers.get('X-Payuee-Timestamp', '')
    webhook_secret = getattr(settings, 'WEBHOOK_SECRET', '') or settings.PAYUEE_API_SECRET

    is_valid = PayueeClient.verify_webhook_signature(
        payload=raw_body,
        signature=signature,
        secret=webhook_secret,
        timestamp=timestamp,
    )

    if not is_valid:
        logger.error("Payuee webhook rejected: invalid or missing signature")
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    try:
        data = json.loads(raw_body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error("Payuee webhook: invalid JSON body")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event_type = data.get('event_type')
    order_id = data.get('order_id')
    order_payload = data.get('order', {})

    logger.info(f"Received Payuee webhook: {event_type} (order_id={order_id})")

    handlers = {
        'order.created': handle_order_created,
        'order.on_hold': handle_order_on_hold,
        'order.scanned': handle_order_scanned,
        'order.delivered': handle_order_delivered,
        'order.refunded': handle_order_refunded,
        'order.cancelled': handle_order_cancelled,
        'order.report': handle_order_report,
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.warning(f"Unhandled Payuee webhook event type: {event_type}")
        # Still acknowledge with 200 so Payuee doesn't retry an event we
        # deliberately don't act on.
        return JsonResponse({'status': 'success'})

    try:
        handler(order_id, order_payload)
    except Order.DoesNotExist:
        logger.error(f"Payuee webhook {event_type}: no local order for payuee_order_id={order_id}")
        # Per docs, Payuee retries until it gets a 200. If we don't recognize
        # the order (e.g. it was never persisted due to an earlier bug), a
        # 500 here would trigger infinite retries for an order we'll never
        # match - acknowledge instead and rely on logging/alerting.
        return JsonResponse({'status': 'success', 'note': 'order not found locally'})
    except Exception as e:
        logger.error(f"Error processing Payuee webhook {event_type}: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'status': 'success'})


def _get_order(order_id):
    return Order.objects.get(payuee_order_id=str(order_id))


def handle_order_created(order_id, order_payload):
    order = _get_order(order_id)
    order.payuee_escrow_status = 'created'
    order.status = 'confirmed'
    order.save()
    OrderStatusHistory.objects.create(
        order=order, status='confirmed',
        notes=f'Escrow order created (Payuee order_id={order_id}).'
    )


def handle_order_on_hold(order_id, order_payload):
    order = _get_order(order_id)
    order.payuee_escrow_status = 'on_hold'
    order.save()
    OrderStatusHistory.objects.create(
        order=order, status=order.status,
        notes='Order placed ON HOLD by Payuee - wallet needs funding within 24 hours or the order will be cancelled.'
    )


def handle_order_scanned(order_id, order_payload):
    order = _get_order(order_id)
    order.payuee_escrow_status = 'scanned'
    order.shipping_status = 'shipped'
    order.save()
    OrderStatusHistory.objects.create(
        order=order, status=order.status,
        notes='Delivery QR code scanned - awaiting final PIN verification.'
    )


def handle_order_delivered(order_id, order_payload):
    order = _get_order(order_id)
    order.status = 'delivered'
    order.shipping_status = 'delivered'
    order.delivered_at = timezone.now()
    order.payuee_escrow_status = 'released'
    order.payment_status = 'paid'
    order.save()
    OrderStatusHistory.objects.create(
        order=order, status='delivered',
        notes='Delivery verified. Escrow funds released to vendor.'
    )


def handle_order_refunded(order_id, order_payload):
    order = _get_order(order_id)
    order.status = 'refunded'
    order.payment_status = 'refunded'
    order.payuee_escrow_status = 'refunded'
    order.save()

    for item in order.items.all():
        if item.product and item.product.track_inventory:
            item.product.quantity += item.quantity
            item.product.save()

    OrderStatusHistory.objects.create(
        order=order, status='refunded',
        notes='Order refunded by Payuee. Escrow funds returned to wallet.'
    )


def handle_order_cancelled(order_id, order_payload):
    order = _get_order(order_id)
    order.status = 'cancelled'
    order.payuee_escrow_status = 'cancelled'
    order.save()
    OrderStatusHistory.objects.create(
        order=order, status='cancelled',
        notes='Order cancelled via Payuee.'
    )


def handle_order_report(order_id, order_payload):
    order = _get_order(order_id)
    OrderStatusHistory.objects.create(
        order=order, status=order.status,
        notes='Order was reported/flagged for review via Payuee.'
    )
