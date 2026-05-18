
# ============================================================
# FILE 6: orders/serializers.py (FIXED - already correct but verify)
# ============================================================
"""
Serializers for the orders app — aligned with Payuee Escrow API v1.
"""

from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from products.models import Product
from products.serializers import ProductListSerializer


# =============================================================================
# PAYUEE-ALIGNED SERIALIZERS (API Contract Mapping)
# =============================================================================

class PayueeCartMetaSerializer(serializers.Serializer):
    """
    Payuee cart_meta structure for order creation.
    Maps to: cart_items[].cart_meta in POST /v1/order/create
    """
    quantity = serializers.IntegerField(min_value=1, required=True)
    outfit_size = serializers.CharField(required=False, allow_blank=True)
    shoe_size = serializers.CharField(required=False, allow_blank=True)


class PayueeCartItemSerializer(serializers.Serializer):
    """
    Payuee cart item structure for order creation.
    Maps to: cart_items[] in POST /v1/order/create
    Payuee uses INTEGER product IDs, not UUIDs.
    """
    product_id = serializers.IntegerField(required=True, min_value=1)
    cart_meta = PayueeCartMetaSerializer(required=True)


class PayueeShippingSerializer(serializers.Serializer):
    """
    Per-vendor shipping configuration for Payuee order creation.
    Maps to: shipping[] in POST /v1/order/create
    Must match the response from POST /v1/order/shipping-fees exactly.
    """
    vendor_id = serializers.IntegerField(required=True, min_value=1)
    fee = serializers.IntegerField(required=True, min_value=0)
    method_id = serializers.CharField(required=True)
    config_id = serializers.IntegerField(required=True, min_value=1)
    company_name = serializers.CharField(required=True)


class PayueeCustomerSerializer(serializers.Serializer):
    """
    Customer/Delivery info for Payuee order creation.
    Maps to: customer object in POST /v1/order/create
    """
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    phone_number = serializers.CharField(required=True, max_length=20)
    state = serializers.CharField(required=True, max_length=100)
    city = serializers.CharField(required=True, max_length=100)
    address_1 = serializers.CharField(required=True, max_length=500)
    address_2 = serializers.CharField(required=False, allow_blank=True, max_length=500)
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    order_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    zip_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    province = serializers.CharField(required=False, allow_blank=True, max_length=100)
    save_address = serializers.BooleanField(required=False, default=True)


class PayueeShippingFeeItemSerializer(serializers.Serializer):
    """
    Individual cart item for shipping fee calculation.
    Maps to: cart_items[] in POST /v1/order/shipping-fees
    """
    product_id = serializers.IntegerField(required=True, min_value=1)
    eshop_user_id = serializers.IntegerField(required=True, min_value=1)
    quantity = serializers.IntegerField(required=True, min_value=1)


class PayueeShippingFeeRequestSerializer(serializers.Serializer):
    """
    Request payload for Payuee shipping fee calculation.
    Maps to: POST /v1/order/shipping-fees
    """
    vendors = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=True,
        min_length=1,
    )
    state = serializers.CharField(required=True, max_length=100)
    city = serializers.CharField(required=True, max_length=100)
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    cart_items = PayueeShippingFeeItemSerializer(many=True, required=True, min_length=1)


# =============================================================================
# CART ITEM SERIALIZERS
# =============================================================================

class CartItemSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for cart items in cart responses.
    Includes payuee_product_id and payuee_vendor_id so frontend
    can correctly call Payuee APIs with integer IDs.
    """
    
    product = ProductListSerializer(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        coerce_to_string=False,
    )
    # Expose Payuee IDs for frontend API calls
    payuee_product_id = serializers.IntegerField(
        source='product.payuee_product_id',
        read_only=True,
        allow_null=True,
    )
    payuee_vendor_id = serializers.IntegerField(
        source='product.payuee_vendor_id',
        read_only=True,
        allow_null=True,
    )
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'quantity', 'total_price',
            'payuee_product_id', 'payuee_vendor_id',
            'created_at', 'updated_at'
        ]


class CartItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for adding items to local cart.
    Accepts your local product UUID (product_id).
    The view maps this to Payuee's integer product_id when calling their API.
    """
    
    product_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = CartItem
        fields = ['product_id', 'quantity']
    
    def validate_quantity(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, data: dict) -> dict:
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id, status='active')
        except Product.DoesNotExist:
            raise serializers.ValidationError(
                {"product_id": "Product does not exist or is inactive."}
            )
        
        # Validate against Payuee stock if product is Payuee-sourced
        if product.payuee_product_id:
            if product.payuee_stock_remaining is not None and product.payuee_stock_remaining < quantity:
                raise serializers.ValidationError(
                    {"quantity": f"Only {product.payuee_stock_remaining} units available from vendor."}
                )
        elif product.stock_quantity is not None and product.stock_quantity < quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock_quantity} units available."}
            )
        
        self._product = product
        return data
    
    def create(self, validated_data: dict) -> CartItem:
        cart = self.context['cart']
        product = self._product
        quantity = validated_data['quantity']
        
        with transaction.atomic():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save(update_fields=['quantity', 'updated_at'])
        
        return cart_item


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cart item quantity."""
    
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def validate_quantity(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, data: dict) -> dict:
        quantity = data.get('quantity')
        product = self.instance.product
        
        if product.payuee_product_id and product.payuee_stock_remaining is not None:
            if product.payuee_stock_remaining < quantity:
                raise serializers.ValidationError(
                    {"quantity": f"Only {product.payuee_stock_remaining} units available."}
                )
        elif product.stock_quantity is not None and product.stock_quantity < quantity:
            raise serializers.ValidationError(
                {"quantity": f"Only {product.stock_quantity} units available."}
            )
        return data


# =============================================================================
# CART SERIALIZER
# =============================================================================

class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for cart (read-only).
    Removed erroneous 'product' field — a cart has items, not a single product.
    """
    
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, coerce_to_string=False
    )
    total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, coerce_to_string=False
    )
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'total', 'updated_at']


# =============================================================================
# ORDER ITEM SERIALIZER
# =============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items (read-only)."""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_sku', 'product_image',
            'quantity', 'unit_price', 'total_price'
        ]


# =============================================================================
# ORDER STATUS HISTORY SERIALIZER
# =============================================================================

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history."""
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        default='System'
    )
    
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'notes', 'created_by_name', 'created_at']


# =============================================================================
# ORDER SERIALIZERS
# =============================================================================

class OrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for order list views.
    View should annotate item_count=Count('items') for performance.
    """
    
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status',
            'shipping_status', 'total', 'currency', 'item_count',
            'created_at', 'updated_at'
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single order retrieval."""
    
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()
    payuee_order_ids = serializers.JSONField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status', 'shipping_status',
            'payuee_order_ids', 'payuee_escrow_status', 'trans_code',
            'subtotal', 'shipping_cost', 'tax', 'discount', 'total', 'currency',
            'shipping_name', 'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_country', 'shipping_postal_code', 'shipping_phone',
            'billing_name', 'billing_address', 'billing_city', 'billing_state',
            'billing_country', 'billing_postal_code',
            'customer_note', 'admin_note',
            'tracking_number', 'carrier', 'shipped_at', 'delivered_at',
            'items', 'status_history', 'created_at', 'updated_at'
        ]
    
    def get_status_history(self, obj: Order) -> list:
        history = obj.status_history.select_related('created_by').all()[:10]
        return OrderStatusHistorySerializer(history, many=True).data


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating orders through Payuee escrow.
    Handles BOTH local Order creation AND Payuee API payload validation.
    
    Expected input (from frontend):
    {
        "trans_code": "123456",
        "webhook_response_url": "https://yourdomain.com/webhooks/payuee/",
        "customer": {...PayueeCustomerSerializer fields...},
        "cart_items": [
            {"product_id": 12, "cart_meta": {"quantity": 2, "outfit_size": "M"}}
        ],
        "shipping": [
            {"vendor_id": 5, "fee": 2500, "method_id": "distance_based", "config_id": 2, "company_name": "DHL"}
        ]
    }
    """
    
    # Payuee-specific fields (write-only, validated then passed to Payuee client)
    customer = PayueeCustomerSerializer(write_only=True)
    cart_items = PayueeCartItemSerializer(many=True, write_only=True)
    shipping = PayueeShippingSerializer(many=True, write_only=True)
    trans_code = serializers.CharField(
        write_only=True,
        min_length=6,
        max_length=6,
        error_messages={
            'min_length': 'Transaction code must be exactly 6 characters.',
            'max_length': 'Transaction code must be exactly 6 characters.',
        }
    )
    webhook_response_url = serializers.URLField(write_only=True, required=True)
    
    class Meta:
        model = Order
        fields = [
            'shipping_name', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_country', 'shipping_postal_code',
            'shipping_phone', 'customer_note',
            'customer', 'cart_items', 'shipping', 'trans_code', 'webhook_response_url'
        ]
    
    def validate_trans_code(self, value: str) -> str:
        """Validate transaction code is alphanumeric."""
        if not value.isalnum():
            raise serializers.ValidationError(
                "Transaction code must contain only letters and numbers."
            )
        return value.upper()
    
    def validate_cart_items(self, value: list) -> list:
        """Validate cart items reference valid local Payuee products."""
        if not value:
            raise serializers.ValidationError("Cart cannot be empty.")
        
        for idx, item in enumerate(value):
            payuee_product_id = item['product_id']
            
            try:
                product = Product.objects.get(
                    payuee_product_id=payuee_product_id,
                    status='active'
                )
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    {f"cart_items[{idx}]": f"Payuee product {payuee_product_id} not found or inactive."}
                )
            
            # Validate stock
            quantity = item['cart_meta']['quantity']
            if product.payuee_stock_remaining is not None and product.payuee_stock_remaining < quantity:
                raise serializers.ValidationError(
                    {f"cart_items[{idx}]": f"Insufficient stock for {product.name}."}
                )
            
            # Attach local product for create()
            item['_local_product'] = product
        
        return value
    
    def validate_shipping(self, value: list) -> list:
        """Validate shipping covers all vendors in cart."""
        if not value:
            raise serializers.ValidationError("Shipping configuration is required.")
        
        # Extract vendor IDs from validated cart_items
        cart_vendor_ids = set()
        if 'cart_items' in self.initial_data:
            for item in self.initial_data['cart_items']:
                try:
                    product = Product.objects.get(payuee_product_id=item['product_id'])
                    cart_vendor_ids.add(product.payuee_vendor_id)
                except Product.DoesNotExist:
                    pass
        
        shipping_vendor_ids = {s['vendor_id'] for s in value}
        
        missing = cart_vendor_ids - shipping_vendor_ids
        if missing:
            raise serializers.ValidationError(
                f"Missing shipping configuration for vendors: {missing}"
            )
        
        return value
    
    @transaction.atomic
    def create(self, validated_data: dict) -> Order:
        """
        Create local Order record. Payuee API call happens in the view
        using the validated payload from this serializer.
        """
        # Extract Payuee-specific data (not stored directly on Order model)
        customer = validated_data.pop('customer')
        cart_items = validated_data.pop('cart_items')
        shipping = validated_data.pop('shipping')
        trans_code = validated_data.pop('trans_code')
        webhook_response_url = validated_data.pop('webhook_response_url')
        
        # Calculate local totals
        subtotal = Decimal('0.00')
        shipping_cost = Decimal('0.00')
        
        for item in cart_items:
            product = item['_local_product']
            quantity = item['cart_meta']['quantity']
            subtotal += product.price * quantity
        
        for ship in shipping:
            # Payuee returns fee in kobo (smallest unit), convert to NGN
            shipping_cost += Decimal(str(ship['fee'])) / 100
        
        total = subtotal + shipping_cost
        
        # Create local Order
        order = Order.objects.create(
            **validated_data,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            total=total,
            trans_code=trans_code,
            webhook_response_url=webhook_response_url,
            status='pending',
            payment_status='pending',
        )
        
        # Create local OrderItems
        for item in cart_items:
            product = item['_local_product']
            quantity = item['cart_meta']['quantity']
            OrderItem.objects.create(
                order=order,
                product_name=product.name,
                product_sku=product.sku,
                product_image=product.image.url if product.image else None,
                quantity=quantity,
                unit_price=product.price,
                total_price=product.price * quantity,
            )
        
        # Store Payuee payload for the view to use
        order.payuee_payload = {
            'trans_code': trans_code,
            'webhook_response_url': webhook_response_url,
            'customer': customer,
            'cart_items': [
                {
                    'product_id': item['product_id'],
                    'cart_meta': item['cart_meta']
                }
                for item in cart_items
            ],
            'shipping': shipping,
        }
        order.save(update_fields=['payuee_payload'])
        
        # Log status history
        OrderStatusHistory.objects.create(
            order=order,
            status='pending',
            notes='Order created locally, awaiting Payuee escrow confirmation',
        )
        
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status with audit trail."""
    
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = ['status', 'notes']
    
    def update(self, instance: Order, validated_data: dict) -> Order:
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        notes = validated_data.pop('notes', '')
        
        instance = super().update(instance, validated_data)
        
        if old_status != new_status:
            OrderStatusHistory.objects.create(
                order=instance,
                status=new_status,
                notes=notes or f'Status changed from {old_status} to {new_status}',
                created_by=self.context.get('request').user if self.context.get('request') else None,
            )
        
        return instance


class ShippingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shipping information."""
    
    class Meta:
        model = Order
        fields = [
            'tracking_number', 'carrier', 'shipping_status'
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for public order tracking."""
    
    items = OrderItemSerializer(many=True, read_only=True)
    current_status = serializers.CharField(source='status', read_only=True)
    estimated_delivery = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'order_number', 'current_status', 'shipping_status',
            'tracking_number', 'carrier', 'shipped_at', 'delivered_at',
            'estimated_delivery', 'items', 'created_at'
        ]
    
    def get_estimated_delivery(self, obj: Order) -> str | None:
        from datetime import timedelta
        
        if obj.shipped_at:
            estimated = obj.shipped_at + timedelta(days=5)
            return estimated.isoformat()
        return None


class OrderCancelSerializer(serializers.Serializer):
    """
    Serializer for cancelling orders via Payuee API.
    Maps to: POST /v1/order/cancel
    """
    order_id = serializers.IntegerField(required=True, min_value=1)
    trans_code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
    )
    report_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate_trans_code(self, value: str) -> str:
        if not value.isalnum():
            raise serializers.ValidationError(
                "Transaction code must contain only letters and numbers."
            )
        return value.upper()


class OrderVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying delivery via Payuee API.
    Maps to: POST /v1/order/verify
    """
    encrypted = serializers.CharField(required=True)
    customer_id = serializers.IntegerField(required=True, min_value=1)
    trans_code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
    )


# =============================================================================
# CHECKOUT & SUMMARY SERIALIZERS
# =============================================================================

class CheckoutSerializer(serializers.Serializer):
    """
    Serializer for checkout process (pre-order validation).
    Gathers customer info and validates Payuee transaction PIN.
    """
    
    # Customer info (maps to Payuee customer object)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    phone_number = serializers.CharField(required=True, max_length=20)
    
    # Shipping address
    shipping_name = serializers.CharField(required=True, max_length=255)
    shipping_address = serializers.CharField(required=True, max_length=500)
    shipping_city = serializers.CharField(required=True, max_length=100)
    shipping_state = serializers.CharField(required=True, max_length=100)
    shipping_country = serializers.CharField(required=True, max_length=100)
    shipping_postal_code = serializers.CharField(required=True, max_length=20)
    shipping_phone = serializers.CharField(required=True, max_length=20)
    customer_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    # Location (for Payuee shipping calculation)
    latitude = serializers.FloatField(required=False, default=6.5244)
    longitude = serializers.FloatField(required=False, default=3.3792)
    
    # Transaction code (customer sets this — 6 digits per Payuee docs)
    trans_code = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        error_messages={
            'min_length': 'Transaction code must be exactly 6 characters.',
            'max_length': 'Transaction code must be exactly 6 characters.',
        }
    )
    
    def validate_trans_code(self, value: str) -> str:
        if not value.isalnum():
            raise serializers.ValidationError(
                "Transaction code must contain only letters and numbers."
            )
        return value.upper()


class OrderSummarySerializer(serializers.Serializer):
    """Serializer for order summary (calculated, not persisted)."""
    
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    shipping_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    tax = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    discount = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    total = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False
    )
    item_count = serializers.IntegerField(min_value=0)
    currency = serializers.CharField(default='NGN', read_only=True)
