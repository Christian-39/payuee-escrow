
# ============================================================
# FILE 8: webhooks.py (FIXED - already mostly correct, verify signature)
# ============================================================
"""
Webhook handlers for Payuee.
Processes incoming webhooks from Payuee escrow system.
"""

import json
import logging
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
    """
    Handle incoming webhooks from Payuee.
    
    Expected webhook events:
    - order.created: Order created in Payuee
    - order.paid: Payment received
    - order.verified: Delivery verified, funds released
    - order.refunded: Order refunded
    - wallet.funded: Wallet funded
    """
    
    # Get webhook data
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Get headers for signature verification
    signature = request.headers.get('X-Signature', '')
    timestamp = request.headers.get('X-Timestamp', '')
    
    # Verify signature
    try:
        client = PayueeClient()
        is_valid = client.verify_webhook_signature(
            signature=signature,
            timestamp=timestamp,
            method='POST',
            path='/api/webhooks/payuee',
            body=body
        )
        
        if not is_valid:
            logger.error("Invalid webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    except Exception as e:
        logger.error(f"Signature verification error: {str(e)}")
        return JsonResponse({'error': 'Signature verification failed'}, status=401)
    
    # Process webhook
    event_type = data.get('event')
    event_data = data.get('data', {})
    
    logger.info(f"Received webhook: {event_type}")
    
    # Handle different event types
    handlers = {
        'order.created': handle_order_created,
        'order.paid': handle_order_paid,
        'order.verified': handle_order_verified,
        'order.refunded': handle_order_refunded,
        'wallet.funded': handle_wallet_funded,
    }
    
    handler = handlers.get(event_type)
    if handler:
        try:
            handler(event_data)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    else:
        logger.warning(f"Unknown webhook event type: {event_type}")
        return JsonResponse({'status': 'ignored', 'reason': 'Unknown event type'})


def handle_order_created(data):
    """Handle order.created webhook."""
    payuee_order_id = data.get('order_id')
    reference_id = data.get('reference_id')
    
    logger.info(f"Order created in Payuee: {payuee_order_id}")
    
    try:
        order = Order.objects.get(id=reference_id)
        # CRITICAL FIX: Use payuee_order_ids (JSONField list) instead of payuee_order_id
        if not order.payuee_order_ids:
            order.payuee_order_ids = []
        if payuee_order_id not in order.payuee_order_ids:
            order.payuee_order_ids.append(payuee_order_id)
        order.payuee_escrow_status = 'created'
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes=f'Order created in Payuee escrow (ID: {payuee_order_id})'
        )
    
    except Order.DoesNotExist:
        logger.error(f"Order not found: {reference_id}")
        raise


def handle_order_paid(data):
    """Handle order.paid webhook."""
    payuee_order_id = data.get('order_id')
    amount = data.get('amount')
    currency = data.get('currency')
    
    logger.info(f"Payment received for order: {payuee_order_id}")
    
    try:
        # CRITICAL FIX: Search in payuee_order_ids JSONField list
        order = Order.objects.filter(payuee_order_ids__contains=[payuee_order_id]).first()
        if not order:
            order = Order.objects.filter(payuee_order_ids__contains=payuee_order_id).first()
        
        if not order:
            logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
            raise Order.DoesNotExist(f"Order with Payuee ID {payuee_order_id} not found")
            
        order.payment_status = 'paid'
        order.payuee_escrow_status = 'escrow_locked'
        order.status = 'confirmed'
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='confirmed',
            notes=f'Payment received: {currency} {amount}. Funds held in escrow.'
        )
    
    except Order.DoesNotExist:
        logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
        raise


def handle_order_verified(data):
    """Handle order.verified webhook."""
    payuee_order_id = data.get('order_id')
    
    logger.info(f"Order verified in Payuee: {payuee_order_id}")
    
    try:
        # CRITICAL FIX: Search in payuee_order_ids JSONField list
        order = Order.objects.filter(payuee_order_ids__contains=[payuee_order_id]).first()
        if not order:
            order = Order.objects.filter(payuee_order_ids__contains=payuee_order_id).first()
        
        if not order:
            logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
            raise Order.DoesNotExist(f"Order with Payuee ID {payuee_order_id} not found")
            
        order.status = 'delivered'
        order.shipping_status = 'delivered'
        order.delivered_at = timezone.now()
        order.payuee_escrow_status = 'released'
        order.credit_processed = True
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='delivered',
            notes='Delivery verified. Funds released from escrow to seller.'
        )
    
    except Order.DoesNotExist:
        logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
        raise


def handle_order_refunded(data):
    """Handle order.refunded webhook."""
    payuee_order_id = data.get('order_id')
    amount = data.get('amount')
    reason = data.get('reason', '')
    
    logger.info(f"Order refunded in Payuee: {payuee_order_id}")
    
    try:
        # CRITICAL FIX: Search in payuee_order_ids JSONField list
        order = Order.objects.filter(payuee_order_ids__contains=[payuee_order_id]).first()
        if not order:
            order = Order.objects.filter(payuee_order_ids__contains=payuee_order_id).first()
        
        if not order:
            logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
            raise Order.DoesNotExist(f"Order with Payuee ID {payuee_order_id} not found")
            
        order.status = 'refunded'
        order.payment_status = 'refunded'
        order.payuee_escrow_status = 'refunded'
        order.save()
        
        # Restore inventory
        for item in order.items.all():
            if item.product and item.product.track_inventory:
                item.product.quantity += item.quantity
                item.product.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='refunded',
            notes=f'Order refunded. Amount: {amount}. Reason: {reason}'
        )
    
    except Order.DoesNotExist:
        logger.error(f"Order not found for Payuee ID: {payuee_order_id}")
        raise


def handle_wallet_funded(data):
    """Handle wallet.funded webhook."""
    amount = data.get('amount')
    currency = data.get('currency')
    transaction_id = data.get('transaction_id')
    
    logger.info(f"Wallet funded: {currency} {amount}")
    
    # You might want to store this in a transactions table
    # For now, just log it
    logger.info(f"Transaction ID: {transaction_id}")
    
    # TODO: Store transaction in database if needed
    # Transaction.objects.create(
    #     transaction_id=transaction_id,
    #     amount=amount,
    #     currency=currency,
    #     type='wallet_funding'
    # )
