"""
Serializers for the orders app.
"""

from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from products.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""
    
    product = ProductListSerializer(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price', 'created_at']


class CartItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding items to cart."""
    
    product_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = CartItem
        fields = ['product_id', 'quantity']
    
    def validate_quantity(self, value):
        """Validate quantity."""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cart item quantity."""
    
    class Meta:
        model = CartItem
        fields = ['quantity']
    
    def validate_quantity(self, value):
        """Validate quantity."""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart."""
    
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'total', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items."""
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'product_sku', 'product_image',
            'quantity', 'unit_price', 'total_price'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list view."""
    
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status',
            'shipping_status', 'total', 'currency', 'item_count',
            'created_at', 'updated_at'
        ]
    
    def get_item_count(self, obj):
        """Get number of items in order."""
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail view."""
    
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status', 'shipping_status',
            'payuee_order_id', 'payuee_escrow_status',
            'subtotal', 'shipping_cost', 'tax', 'discount', 'total', 'currency',
            'shipping_name', 'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_country', 'shipping_postal_code', 'shipping_phone',
            'billing_name', 'billing_address', 'billing_city', 'billing_state',
            'billing_country', 'billing_postal_code',
            'customer_note', 'admin_note',
            'tracking_number', 'carrier', 'shipped_at', 'delivered_at',
            'items', 'status_history', 'created_at', 'updated_at'
        ]
    
    def get_status_history(self, obj):
        """Get order status history."""
        history = obj.status_history.all()[:10]
        return OrderStatusHistorySerializer(history, many=True).data


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""
    
    cart_items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    
    class Meta:
        model = Order
        fields = [
            'shipping_name', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_country', 'shipping_postal_code',
            'shipping_phone', 'customer_note', 'cart_items'
        ]
    
    def validate_cart_items(self, value):
        """Validate cart items."""
        if not value:
            raise serializers.ValidationError("Cart cannot be empty.")
        return value


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status."""
    
    notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = ['status', 'notes']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history."""
    
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True
    )
    
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'notes', 'created_by_name', 'created_at']


class ShippingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shipping information."""
    
    class Meta:
        model = Order
        fields = [
            'tracking_number', 'carrier', 'shipping_status'
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking."""
    
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
    
    def get_estimated_delivery(self, obj):
        """Calculate estimated delivery date."""
        from datetime import timedelta
        
        if obj.shipped_at:
            # Estimate 3-5 business days from shipping
            return obj.shipped_at + timedelta(days=5)
        return None


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process."""
    
    shipping_name = serializers.CharField(required=True)
    shipping_address = serializers.CharField(required=True)
    shipping_city = serializers.CharField(required=True)
    shipping_state = serializers.CharField(required=True)
    shipping_country = serializers.CharField(required=True)
    shipping_postal_code = serializers.CharField(required=True)
    shipping_phone = serializers.CharField(required=True)
    customer_note = serializers.CharField(required=False, allow_blank=True)
    
    # NEW: Required for Payuee
    trans_code = serializers.CharField(required=True, min_length=6, max_length=6)
    latitude = serializers.FloatField(required=False, default=6.5244)
    longitude = serializers.FloatField(required=False, default=3.3792)


class OrderSummarySerializer(serializers.Serializer):
    """Serializer for order summary."""
    
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    item_count = serializers.IntegerField()
