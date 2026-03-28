"""
Serializers for admin dashboard API.
"""

from rest_framework import serializers
from accounts.models import User
from products.models import Product, Category
from orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price']


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list view."""
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'customer_email',
            'total', 'currency', 'status', 'payment_status',
            'item_count', 'created_at'
        ]
    
    def get_customer_name(self, obj):
        if obj.shipping_name:
            return obj.shipping_name
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return 'N/A'
    
    def get_customer_email(self, obj):
        if obj.user:
            return obj.user.email
        return None
    
    def get_item_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order view."""
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status', 'currency',
            'subtotal', 'shipping_cost', 'tax', 'discount', 'total',
            'customer_name', 'customer_email', 'customer_phone',
            'shipping_name', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_country', 'shipping_postal_code',
            'shipping_phone', 'tracking_number', 'shipping_carrier',
            'created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at',
            'admin_notes', 'customer_notes', 'items'
        ]
    
    def get_customer_name(self, obj):
        return obj.shipping_name or (obj.user.get_full_name() if obj.user else '')
    
    def get_customer_email(self, obj):
        return obj.user.email if obj.user else ''
    
    def get_customer_phone(self, obj):
        return obj.shipping_phone or (obj.user.phone_number if obj.user else '')


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders."""
    
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'tracking_number', 'shipping_carrier',
            'shipping_name', 'shipping_phone', 'shipping_address',
            'shipping_city', 'shipping_state', 'shipping_country',
            'shipping_postal_code', 'admin_notes'
        ]
    
    def update(self, instance, validated_data):
        # Track status changes for timestamp updates
        new_status = validated_data.get('status')
        if new_status and new_status != instance.status:
            from django.utils import timezone
            if new_status == 'shipped' and not instance.shipped_at:
                instance.shipped_at = timezone.now()
            elif new_status == 'delivered' and not instance.delivered_at:
                instance.delivered_at = timezone.now()
            elif new_status == 'paid' and not instance.paid_at:
                instance.paid_at = timezone.now()
        
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    order_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'phone_number', 'is_admin', 'is_active',
            'email_verified', 'created_at', 'order_count', 'total_spent'
        ]
    
    def get_order_count(self, obj):
        return obj.orders.count()
    
    def get_total_spent(self, obj):
        from django.db.models import Sum
        total = obj.orders.filter(
            status__in=['delivered', 'confirmed']
        ).aggregate(total=Sum('total'))['total']
        return float(total) if total else 0


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for product data."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'price', 'sale_price', 'quantity',
            'category', 'category_name', 'status', 'featured',
            'created_at', 'updated_at'
        ]


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""
    sales = serializers.DictField()
    orders = serializers.DictField()
    customers = serializers.DictField()
    products = serializers.DictField()
    revenue = serializers.DictField()