# ============================================================
# FILE 2: orders/views.py (FIXED - Payuee integration)
# ============================================================
"""
Views for the orders app.
Handles cart, checkout, and order management.
"""

import json
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from products.models import Product
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderStatusUpdateSerializer,
    ShippingUpdateSerializer,
    OrderTrackingSerializer,
    CheckoutSerializer,
    OrderSummarySerializer
)
from payments.payuee_client import PayueeClient

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ════════════════════════════════════════════════════════════
# CART VIEWS
# ════════════════════════════════════════════════════════════

class CartView(generics.RetrieveAPIView):
    """Get user's cart."""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


class AddToCartView(generics.CreateAPIView):
    """Add product to cart."""
    serializer_class = CartItemCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # 1. Print exactly what the frontend is sending
        print("--- RAW INCOMING DATA ---")
        print(request.data)
        
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            # 2. Print exactly what fields are broken or missing
            print("--- SERIALIZER ERROR DETAILS ---")
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # ... rest of your existing working code remains the same ...
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = serializer.validated_data['product_id']
        product = get_object_or_404(Product, id=product_id, status='active')
        
        quantity = serializer.validated_data['quantity']
        if product.track_inventory and product.quantity < quantity:
            return Response(
                {'error': f'Only {product.quantity} items available in stock.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if product.source == 'payuee' and not product.payuee_product_id:
            return Response(
                {'error': 'This product is not properly linked to Payuee.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            new_quantity = cart_item.quantity + quantity
            if product.track_inventory and product.quantity < new_quantity:
                return Response(
                    {'error': f'Cannot add more. Only {product.quantity} items available.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = new_quantity
            cart_item.save()

        return Response({
            'message': 'Product added to cart.',
            'cart_item': CartItemSerializer(cart_item).data,
            'cart': CartSerializer(cart).data
        }, status=status.HTTP_201_CREATED)


class UpdateCartItemView(generics.UpdateAPIView):
    """Update cart item quantity."""
    serializer_class = CartItemUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart = get_object_or_404(Cart, user=self.request.user)
        item_id = self.kwargs.get('item_id')
        return get_object_or_404(CartItem, id=item_id, cart=cart)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data['quantity']
        product = instance.product

        # Check stock
        if product.track_inventory and product.quantity < quantity:
            return Response(
                {'error': f'Only {product.quantity} items available in stock.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.quantity = quantity
        instance.save()

        # Get updated cart
        cart = instance.cart

        return Response({
            'message': 'Cart updated.',
            'cart_item': CartItemSerializer(instance).data,
            'cart': CartSerializer(cart).data
        })


class RemoveFromCartView(generics.DestroyAPIView):
    """Remove item from cart."""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart = get_object_or_404(Cart, user=self.request.user)
        item_id = self.kwargs.get('item_id')
        return get_object_or_404(CartItem, id=item_id, cart=cart)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        cart = instance.cart
        self.perform_destroy(instance)

        return Response({
            'message': 'Item removed from cart.',
            'cart': CartSerializer(cart).data
        })


class ClearCartView(generics.DestroyAPIView):
    """Clear all items from cart."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()

        return Response({
            'message': 'Cart cleared.',
            'cart': CartSerializer(cart).data
        })


# ════════════════════════════════════════════════════════════
# ORDER VIEWS
# ════════════════════════════════════════════════════════════

class OrderListView(generics.ListAPIView):
    """List user's orders."""
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('user').prefetch_related('items')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order details."""
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderTrackingView(generics.RetrieveAPIView):
    """Track order status."""
    serializer_class = OrderTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def checkout(request):
    """
    Process checkout and create Payuee escrow order.

    Flow:
    1. Validate cart items and Payuee linkage
    2. Calculate totals
    3. Call Payuee logistics for shipping fees
    4. Create local order record
    5. Call Payuee to create escrow order
    6. Handle ON_HOLD (insufficient wallet) or success
    """
    logger.info(f"=== CHECKOUT START === User: {request.user.email}")

    try:
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info("Serializer valid")

        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all().select_related('product')
        logger.info(f"Cart items: {cart_items.count()}")

        if not cart_items:
            return Response(
                {'error': 'Your cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── Stock validation ──
        for item in cart_items:
            if item.product.track_inventory and item.product.quantity < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for {item.product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = serializer.validated_data
        logger.info(f"Shipping to: {data['shipping_city']}")

        # ── CRITICAL FIX: Get trans_code from validated data ──
        trans_code = data.get('trans_code')
        if not trans_code:
            return Response(
                {'error': 'Transaction PIN (trans_code) is required. Please provide your 6-digit PIN.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # CRITICAL FIX: Validate trans_code is exactly 6 digits
        trans_code_str = str(trans_code).strip()
        if len(trans_code_str) != 6 or not trans_code_str.isdigit():
            return Response(
                {'error': 'trans_code must be exactly 6 digits.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        shipping_cost = Decimal('0')
        tax = subtotal * Decimal('0.08')
        discount = Decimal('0')
        total = subtotal + shipping_cost + tax - discount
        logger.info(f"Subtotal: {subtotal}, Tax: {tax}, Total: {total}")

        # ── CRITICAL FIX: Build Payuee customer dict per docs ──
        # https://payuee.com/doc/documentation
        customer = {
            "email": request.user.email,
            "first_name": request.user.first_name or data['shipping_name'].split()[0],
            "last_name": request.user.last_name or ' '.join(data['shipping_name'].split()[1:]) if len(data['shipping_name'].split()) > 1 else '',
            "phone_number": data['shipping_phone'],
            "state": data['shipping_state'],
            "city": data['shipping_city'],
            "address_1": data['shipping_address'],
            "address_2": data.get('shipping_address_2', ''),
            "latitude": float(data.get('latitude', 6.5244)),
            "longitude": float(data.get('longitude', 3.3792)),
            "order_note": data.get('customer_note', ''),
            "zip_code": data.get('shipping_postal_code', ''),
            "province": data.get('province', ''),
            "save_address": True,
        }

        # ── CRITICAL FIX: Build Payuee cart_items — ONLY use payuee_product_id ──
        payuee_cart_items = []
        vendors = set()

        for item in cart_items:
            # Validate Payuee product linkage
            if not item.product.payuee_product_id:
                return Response(
                    {'error': f'"{item.product.name}" is not linked to a Payuee product. Remove and re-add to cart.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate Payuee vendor linkage
            if not item.product.payuee_vendor_id:
                return Response(
                    {'error': f'"{item.product.name}" is missing vendor info (payuee_vendor_id).'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payuee_item = {
                "product_id": int(item.product.payuee_product_id),
                "cart_meta": {
                    "quantity": item.quantity,
                }
            }
            # Add outfit_size if applicable (e.g., clothing)
            if item.selected_size:
                payuee_item['cart_meta']['outfit_size'] = item.selected_size

            payuee_cart_items.append(payuee_item)
            vendors.add(int(item.product.payuee_vendor_id))

        # ── CRITICAL FIX: Calculate shipping via Payuee logistics ──
        payuee_client = PayueeClient()
        shipping = []

        if vendors:
            try:
                shipping_result = payuee_client.get_shipping_fees(
                    vendors=list(vendors),
                    state=customer['state'],
                    city=customer['city'],
                    latitude=customer['latitude'],
                    longitude=customer['longitude'],
                    cart_items=[
                        {
                            "product_id": int(item.product.payuee_product_id),
                            "eshop_user_id": int(item.product.payuee_vendor_id),
                            "quantity": item.quantity,
                        }
                        for item in cart_items
                    ]
                )

                if shipping_result.get('success'):
                    shipping = shipping_result.get('data', {}).get('shipping', [])
                    shipping_cost = Decimal(str(sum(s['fee'] for s in shipping)))
                    total = subtotal + shipping_cost + tax - discount
                    logger.info(f"Shipping calculated: {shipping_cost} via {shipping}")
                else:
                    error_msg = shipping_result.get('error', 'Unknown shipping error')
                    logger.warning(f"Shipping calculation failed: {error_msg}")
                    # Continue without shipping — Payuee may calculate on their side
            except Exception as e:
                logger.error(f"Shipping calculation error: {e}")
                # Continue without shipping — don't block checkout

        # ── CRITICAL FIX: Webhook URL from settings ──
        webhook_url = getattr(settings, 'PAYUEE_WEBHOOK_URL', None)
        if not webhook_url:
            logger.error("PAYUEE_WEBHOOK_URL not configured in settings")
            return Response(
                {'error': 'Payment webhook URL not configured. Contact support.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ── DEBUG: Log Payuee payload ──
        payuee_payload = {
            "trans_code": trans_code_str,
            "webhook_response_url": webhook_url,
            "customer": customer,
            "cart_items": payuee_cart_items,
            "shipping": shipping,
        }
        logger.info(f"PAYUEE PAYLOAD: {json.dumps(payuee_payload, indent=2, default=str)}")

        with transaction.atomic():
            # Create local order FIRST (before Payuee call)
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax=tax,
                discount=discount,
                total=total,
                currency='NGN',
                shipping_name=data['shipping_name'],
                shipping_address=data['shipping_address'],
                shipping_city=data['shipping_city'],
                shipping_state=data['shipping_state'],
                shipping_country=data.get('shipping_country', 'Nigeria'),
                shipping_postal_code=data.get('shipping_postal_code', ''),
                shipping_phone=data['shipping_phone'],
                customer_note=data.get('customer_note', ''),
                idempotency_key=str(uuid.uuid4()),
                status='pending',
                payment_status='pending',
            )
            logger.info(f"Local order created: {order.id}")

            # Create local order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_sku=item.product.sku or '',
                    product_image=item.product.featured_image or '',
                    payuee_product_id=item.product.payuee_product_id,
                    payuee_vendor_id=item.product.payuee_vendor_id,
                    selected_size=item.selected_size,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    total_price=item.total_price
                )

                # Atomic stock decrement
                Product.objects.filter(id=item.product_id).update(
                    quantity=F('quantity') - item.quantity
                )

            # ── CALL PAYUEE ──
            logger.info("=== PAYUEE ORDER CREATE START ===")

            payuee_result = payuee_client.create_order(
                trans_code=trans_code_str,
                webhook_response_url=webhook_url,
                customer=customer,
                cart_items=payuee_cart_items,
                shipping=shipping,
                idempotency_key=order.idempotency_key
            )
            logger.info(f"PAYUEE RESPONSE: {payuee_result}")

            # Clear cart
            cart.items.all().delete()

            # Handle Payuee response
            if payuee_result and payuee_result.get('success'):
                response_data = payuee_result.get('data', {})

                # Save Payuee order IDs
                order_ids = response_data.get('order_ids', [])
                if order_ids:
                    order.payuee_order_ids = order_ids
                    # Set primary order ID for tracking
                    if not order.primary_payuee_order_id and order_ids:
                        order.primary_payuee_order_id = order_ids[0]

                order_status = response_data.get('status', 'CREATED')
                order.payuee_escrow_status = order_status.lower() if order_status else 'created'

                # ── CRITICAL FIX: Handle ON_HOLD (insufficient wallet) ──
                if order_status == 'ON_HOLD':
                    order.status = 'on_hold'
                    order.payment_status = 'on_hold'
                    order.save()

                    OrderStatusHistory.objects.create(
                        order=order,
                        status='on_hold',
                        notes=f'Payuee escrow ON_HOLD: Wallet needs funding. Order IDs: {order_ids}'
                    )

                    return Response({
                        'message': 'Order created but ON HOLD. Please fund your wallet within 24 hours.',
                        'order': OrderDetailSerializer(order).data,
                        'status': 'ON_HOLD',
                        'order_ids': order_ids,
                        'wallet_funding_required': True,
                    }, status=status.HTTP_402_PAYMENT_REQUIRED)

                # Normal success — escrow locked
                order.status = 'pending'
                order.payment_status = 'escrow_locked'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='pending',
                    notes=f'Payuee escrow created. Order IDs: {order_ids}'
                )

                return Response({
                    'message': 'Order created successfully.',
                    'order': OrderDetailSerializer(order).data,
                    'order_ids': order_ids,
                    'status': order_status,
                    'escrow_status': 'locked',
                }, status=status.HTTP_201_CREATED)

            else:
                # Payuee failed — order exists locally but payment failed
                error_msg = payuee_result.get('error', 'Unknown Payuee error') if payuee_result else 'No response from Payuee'
                status_code = payuee_result.get('status_code', 500) if payuee_result else 500

                logger.error(f"Payuee failed: {status_code} - {error_msg}")

                order.status = 'payment_failed'
                order.payment_status = 'failed'
                order.payuee_error = error_msg
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='payment_failed',
                    notes=f'Payuee error: {error_msg}'
                )

                return Response({
                    'message': 'Order saved locally but Payuee payment failed.',
                    'order': OrderDetailSerializer(order).data,
                    'error': error_msg,
                    'status_code': status_code,
                }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception("Checkout crash")
        return Response(
            {"error": "Something went wrong during checkout", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_order_summary(request):
    """Get order summary before checkout."""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all().select_related('product')

    if not cart_items:
        return Response(
            {'error': 'Your cart is empty.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # CRITICAL FIX: Validate all cart items are Payuee-linked
    unlinked_items = [item.product.name for item in cart_items 
                      if item.product.source == 'payuee' and not item.product.payuee_product_id]
    if unlinked_items:
        return Response(
            {'error': f'Some items are not linked to Payuee: {", ".join(unlinked_items)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    subtotal = sum(item.total_price for item in cart_items)
    shipping_cost = Decimal('0')
    tax = subtotal * Decimal('0.08')
    discount = Decimal('0')
    total = subtotal + shipping_cost + tax - discount

    summary = {
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'discount': discount,
        'total': total,
        'item_count': sum(item.quantity for item in cart_items)
    }

    return Response(summary)


# ════════════════════════════════════════════════════════════
# ADMIN ORDER MANAGEMENT
# ════════════════════════════════════════════════════════════

class AdminOrderListView(generics.ListAPIView):
    """Admin: List all orders."""
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Order.objects.all()

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset.select_related('user').prefetch_related('items')


class AdminOrderDetailView(generics.RetrieveAPIView):
    """Admin: Get order details."""
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_number'
    queryset = Order.objects.all()


class AdminOrderStatusUpdateView(generics.UpdateAPIView):
    """Admin: Update order status."""
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_number'
    queryset = Order.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = instance.status
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        instance.status = new_status

        if new_status == 'shipped':
            instance.shipping_status = 'shipped'
            instance.shipped_at = timezone.now()
        elif new_status == 'delivered':
            instance.shipping_status = 'delivered'
            instance.delivered_at = timezone.now()
        elif new_status == 'cancelled':
            # Restore inventory
            for item in instance.items.all():
                if item.product and item.product.track_inventory:
                    item.product.quantity += item.quantity
                    item.product.save()

        instance.save()

        OrderStatusHistory.objects.create(
            order=instance,
            status=new_status,
            notes=notes or f'Status changed from {old_status} to {new_status}',
            created_by=request.user
        )

        return Response({
            'message': 'Order status updated.',
            'order': OrderDetailSerializer(instance).data
        })


class AdminShippingUpdateView(generics.UpdateAPIView):
    """Admin: Update shipping information."""
    serializer_class = ShippingUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_number'
    queryset = Order.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Shipping information updated.',
            'order': OrderDetailSerializer(instance).data
        })


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def verify_order_delivery(request, order_number):
    """Verify order delivery via Payuee QR scan + PIN."""
    order = get_object_or_404(Order, order_number=order_number)

    if not order.primary_payuee_order_id:
        return Response(
            {'error': 'This order is not associated with Payuee.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    payuee_client = PayueeClient()

    # Get encrypted payload from request (scanned QR code)
    encrypted = request.data.get('encrypted')
    customer_id = request.data.get('customer_id')
    trans_code = request.data.get('trans_code')

    if not all([encrypted, customer_id, trans_code]):
        return Response(
            {'error': 'encrypted, customer_id, and trans_code are required for verification.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = payuee_client.verify_order(
        encrypted=encrypted,
        customer_id=int(customer_id),
        trans_code=str(trans_code)
    )

    if result.get('success'):
        order.status = 'delivered'
        order.shipping_status = 'delivered'
        order.delivered_at = timezone.now()
        order.payuee_escrow_status = 'released'
        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status='delivered',
            notes='Delivery verified via Payuee escrow QR + PIN.',
            created_by=request.user
        )

        return Response({
            'message': 'Delivery verified successfully. Escrow released.',
            'order': OrderDetailSerializer(order).data
        })
    else:
        return Response(
            {
                'error': 'Failed to verify delivery.',
                'details': result.get('error')
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders_count(request):
    count = Order.objects.filter(user=request.user).count()
    return Response({'count': count})