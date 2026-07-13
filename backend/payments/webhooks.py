# ============================================================
# FILE 8: payments/webhooks.py (UPDATED PRODUCTION READY)
# ============================================================
"""
Webhook handlers for Payuee.
Processes incoming encrypted webhooks from Payuee escrow system.
"""

import json
import hmac
import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from orders.models import Order, OrderStatusHistory

logger = logging.getLogger('payuee')

PAYUEE_STATIC_IP = "84.8.135.142"


def get_client_ip(request) -> str:
    """Extract clean tracking IP from remote incoming headers context."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


@csrf_exempt
@require_http_methods(["POST"])
def payuee_webhook(request):
    """
    Handle incoming webhooks from Payuee production event servers.
    Enforces Strict IP whitelisting and Cryptographic Verification.
    """
    # 1. Firewall Rule Validation Check
    client_ip = get_client_ip(request)
    if getattr(settings, 'ENFORCE_PAYUEE_IP_VALIDATION', True):
        if client_ip != PAYUEE_STATIC_IP:
            logger.warning(f"Unauthorized Webhook Attempt blocked from source IP: {client_ip}")
            return JsonResponse({'error': 'Forbidden source origin allocation'}, status=403)

    # 2. Extract Data Bodies
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON format payload parsed inside body context")
        return JsonResponse({'error': 'Invalid JSON format payload'}, status=400)

    # 3. Retrieve Cryptographic Headers
    signature = request.headers.get('X-Signature', '')
    timestamp = request.headers.get('X-Timestamp', '')
    
    if not signature or not timestamp:
        logger.error("Missing validation metrics inside webhook header arrays")
        return JsonResponse({'error': 'Missing verification authentication headers'}, status=401)

    # 4. Verify Payuee Webhook Dot Signature Format: timestamp + '.' + body
    webhook_secret = settings.PAYUEE_WEBHOOK_SECRET
    signed_payload = f"{timestamp}.{body}"
    
    computed_digest = hmac.new(
        webhook_secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    expected_signature = f"sha256={computed_digest}"

    # Use constant-time comparison to secure against timing profile attacks
    if not hmac.compare_digest(signature, expected_signature):
        logger.error("Webhook verification failed. Signature mismatch detected.")
        return JsonResponse({'error': 'Invalid security cryptographic signature token signature'}, status=401)

    # 5. Route Validated Events Structure
    event_type = data.get('event_type')
    order_data = data.get('order', {})
    payuee_order_id = data.get('order_id')

    logger.info(f"Processing verified Payuee Webhook Event: {event_type} for Order: {payuee_order_id}")

    try:
        if event_type == "order.created":
            handle_order_status_update(payuee_order_id, 'escrow_locked', 'escrow_locked', 'Order logged and funds locked within Escrow platform.')
            
        elif event_type == "order.confirmed":
            handle_order_status_update(payuee_order_id, 'confirmed', 'processing', 'Vendor confirmed receipt and is package handling.')
            
        elif event_type == "order.scanned":
            handle_order_status_update(payuee_order_id, 'scanned', 'processing', 'Courier package proximity checks matched on delivery site.')

        elif event_type == "order.delivered":
            handle_order_status_update(payuee_order_id, 'delivered', 'delivered', 'Package handover verified via 2FA cryptographic token code matching pin.')

        elif event_type == "order.released":
            handle_order_status_update(payuee_order_id, 'released', 'completed', 'Escrow lifecycle closed out. Payout engine completed splits distribution cleanly.')

        elif event_type == "order.refunded":
            handle_order_reversal(payuee_order_id, 'refunded', 'Reversal finalized. Core asset values restored back to balance holdings pools.')

        elif event_type == "order.cancelled":
            handle_order_reversal(payuee_order_id, 'cancelled', 'Order cancelled before processing limits timed out.')

        elif event_type == "order.on_hold":
            handle_order_status_update(payuee_order_id, 'hold', 'pending', 'Core operational wallet balance insufficient. Awaiting top up allocations updates.')

        else:
            logger.info(f"Unhandled operational event categorization layer: {event_type}")

        # Payuee requires this exact payload form back to affirm successful processing receipt
        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.exception(f"Error handling event lifecycle updates for: {event_type}")
        return JsonResponse({'error': 'Internal operational engine runtime parsing failure tracker'}, status=500)


def handle_order_status_update(payuee_order_id, payuee_status, local_status, history_note):
    """Update localized system state models tracking fields cleanly."""
    order = Order.objects.filter(payuee_order_id=payuee_order_id).first()
    if order:
        order.payuee_escrow_status = payuee_status
        order.status = local_status
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status=local_status,
            notes=history_note
        )
    else:
        raise Order.DoesNotExist(f"Target transaction ID allocation mapping trace not located: {payuee_order_id}")


def handle_order_reversal(payuee_order_id, local_status, note):
    """Execute item quantity returns safely when handling cancellation reversals."""
    order = Order.objects.filter(payuee_order_id=payuee_order_id).first()
    if order:
        order.status = local_status
        order.payment_status = local_status
        order.payuee_escrow_status = local_status
        order.save()
        
        # Safe structural inventory replacement sequence loop executions
        for item in order.items.all():
            if item.product and item.product.track_inventory:
                item.product.quantity += item.quantity
                item.product.save()
                
        OrderStatusHistory.objects.create(
            order=order,
            status=local_status,
            notes=note
        )
