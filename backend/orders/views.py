"""
Views for the orders app.
Handles cart, checkout, and order management.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from requests.exceptions import Timeout, RequestException
from django.utils import timezone
import uuid

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
import logging

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Cart Views
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get product
        product_id = serializer.validated_data['product_id']
        product = get_object_or_404(Product, id=product_id, status='active')
        
        # Check stock
        quantity = serializer.validated_data['quantity']
        if product.track_inventory and product.quantity < quantity:
            return Response(
                {'error': f'Only {product.quantity} items available in stock.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity
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


# Order Views
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
    logger.info(f"=== CHECKOUT START ===")
    logger.info(f"User: {request.user.email}")
    
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

        # Stock validation
        for item in cart_items:
            if item.product.track_inventory and item.product.quantity < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for {item.product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = serializer.validated_data
        logger.info(f"Shipping to: {data['shipping_city']}")

        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        shipping_cost = 0
        tax = subtotal * Decimal('0.08')
        discount = 0
        total = subtotal + shipping_cost + tax - discount
        logger.info(f"Total: {total}")

        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax=tax,
                discount=discount,
                total=total,
                currency='USD',
                shipping_name=data['shipping_name'],
                shipping_address=data['shipping_address'],
                shipping_city=data['shipping_city'],
                shipping_state=data['shipping_state'],
                shipping_country=data['shipping_country'],
                shipping_postal_code=data['shipping_postal_code'],
                shipping_phone=data['shipping_phone'],
                customer_note=data.get('customer_note', ''),
                idempotency_key=str(uuid.uuid4())
            )
            logger.info(f"Order created: {order.id}")

            # Create order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_sku=item.product.sku,
                    product_image=item.product.featured_image,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                    total_price=item.total_price
                )

                if item.product.track_inventory:
                    item.product.quantity -= item.quantity
                    item.product.save()

            # === PAYUEE ESCROW CALL ===
            logger.info("=== PAYUEE CALL START ===")
            payuee_result = None

            try:
                from payments.payuee_client import PayueeClient
                payuee_client = PayueeClient()

                payuee_items = [i for i in cart_items if i.product.payuee_vendor_id]

                if not payuee_items:
                    # Cart has no Payuee-sourced products (e.g. local-only
                    # catalog items) - nothing to place in escrow.
                    logger.info("No Payuee-sourced items in cart - skipping escrow order creation.")
                    payuee_result = {'success': False, 'error': 'no_payuee_items'}
                else:
                    vendor_ids = sorted({i.product.payuee_vendor_id for i in payuee_items})

                    # NOTE: customer_latitude/longitude are not currently
                    # collected by CheckoutSerializer. Defaulting to 0.0 here
                    # is a stopgap - add lat/lon fields to the checkout form
                    # and pass real values through for accurate shipping.
                    customer_lat = getattr(order, 'shipping_latitude', 0.0) or 0.0
                    customer_lon = getattr(order, 'shipping_longitude', 0.0) or 0.0

                    shipping_result = payuee_client.calculate_shipping_fees(
                        vendors=vendor_ids,
                        state=order.shipping_state,
                        city=order.shipping_city,
                        latitude=customer_lat,
                        longitude=customer_lon,
                        cart_items=[
                            {
                                'product_id': i.product.payuee_product_id,
                                'eshop_user_id': i.product.payuee_vendor_id,
                                'quantity': i.quantity,
                            }
                            for i in payuee_items
                        ],
                    )

                    if not shipping_result.get('success'):
                        logger.warning(f"Payuee shipping-fees call failed: {shipping_result.get('error')}")
                        payuee_result = {'success': False, 'error': shipping_result.get('error', 'shipping_unavailable')}
                    else:
                        shipping_array = shipping_result['data'].get('shipping', [])

                        # NOTE: trans_code must be a code the customer knows
                        # (per Payuee docs, never silently auto-generate
                        # without the customer's awareness). CheckoutSerializer
                        # doesn't currently collect one - using the order's
                        # idempotency_key as a stopgap so the call is well-formed;
                        # replace with a real customer-entered PIN once the
                        # checkout form collects it.
                        trans_code = getattr(order, 'trans_code', None) or order.idempotency_key[:6]

                        payuee_result = payuee_client.create_order(
                            order,
                            payuee_items,
                            trans_code=trans_code,
                            shipping=shipping_array,
                            customer_latitude=customer_lat,
                            customer_longitude=customer_lon,
                        )

                logger.info(f"Payuee result: {payuee_result}")

            except Timeout as e:
                logger.error(f"Payuee Timeout: {e}")
                payuee_result = {'success': False, 'error': 'timeout'}

            except RequestException as e:
                logger.error(f"Payuee RequestException: {e}")
                payuee_result = {'success': False, 'error': 'request_failed'}

            except Exception as e:
                logger.error(f"Payuee unexpected error: {e}", exc_info=True)
                payuee_result = {'success': False, 'error': str(e)}

            logger.info(f"=== PAYUEE CALL END ===")

            # Clear cart
            cart.items.all().delete()
            logger.info("Cart cleared")

            # Handle result
            if payuee_result and payuee_result.get('success'):
                logger.info("Payuee SUCCESS")
                # POST /v1/order/create returns "order_ids": [...] (one per
                # vendor) rather than a single order_id - store the first as
                # our primary reference and keep the rest in escrow_status
                # notes for now (a proper multi-vendor order model is a
                # bigger change than this fix covers).
                order_ids = payuee_result.get('order_ids') or []
                order.payuee_order_id = str(order_ids[0]) if order_ids else None
                order.payuee_escrow_status = payuee_result.get('status', 'created')
                order.status = 'pending' if payuee_result.get('status') != 'ON_HOLD' else 'pending'
                order.payment_status = 'pending'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='pending',
                    notes=f"Payuee escrow initiated. order_ids={order_ids}. {payuee_result.get('message', '')}".strip()
                )

                return Response({
                    'message': 'Order created successfully.',
                    'order': OrderDetailSerializer(order).data,
                    'payuee_order_ids': order_ids,
                }, status=status.HTTP_201_CREATED)

            else:
                # Payuee failed - order still created
                logger.warning(f"Payuee failed: {payuee_result}")
                order.status = 'pending'
                order.payment_status = 'pending'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status='pending',
                    notes=f'Order created. Payuee error: {payuee_result.get("error") if payuee_result else "unknown"}'
                )

                return Response({
                    'message': 'Order created. Payment pending.',
                    'order': OrderDetailSerializer(order).data,
                    'payment_url': None,
                    'warning': 'Payment service temporarily unavailable.'
                }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Checkout crash: {str(e)}", exc_info=True)
        return Response(
            {"error": "Something went wrong during checkout"},
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
    
    subtotal = sum(item.total_price for item in cart_items)
    shipping_cost = 0
    tax = subtotal * Decimal(0.08)
    discount = 0
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


# Admin Order Management
class AdminOrderListView(generics.ListAPIView):
    """Admin: List all orders."""
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = Order.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by payment status
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
        
        # Update order status
        instance.status = new_status
        
        # Update related statuses
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
        
        # Create status history
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
    """
    Verify order delivery via Payuee (POST /v1/order/verify).

    Per Payuee's docs, this requires the encrypted payload from scanning the
    customer's delivery QR code (POST /v1/order/scan-qr) plus the customer's
    id and the transaction code they provide at the door - these must be
    supplied by the caller (e.g. a delivery-agent mobile view), not
    fabricated here.
    """
    order = get_object_or_404(Order, order_number=order_number)

    if not order.payuee_order_id:
        return Response(
            {'error': 'This order is not associated with Payuee.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    encrypted = request.data.get('encrypted')
    customer_id = request.data.get('customer_id')
    trans_code = request.data.get('trans_code')

    if not all([encrypted, customer_id, trans_code]):
        return Response(
            {'error': 'encrypted, customer_id, and trans_code are all required (scan the delivery QR code first via /v1/order/scan-qr).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    payuee_client = PayueeClient()
    result = payuee_client.verify_delivery(encrypted, customer_id, trans_code)
    
    if result['success']:
        order.status = 'delivered'
        order.shipping_status = 'delivered'
        order.delivered_at = timezone.now()
        order.payuee_escrow_status = 'completed'
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            status='delivered',
            notes='Delivery verified via Payuee escrow.',
            created_by=request.user
        )
        
        return Response({
            'message': 'Delivery verified successfully.',
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