"""
Admin configuration for orders app.
"""

from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class CartItemInline(admin.TabularInline):
    """Cart item inline."""
    model = CartItem
    extra = 0
    readonly_fields = ['total_price']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Cart admin."""
    
    list_display = ['user', 'total_items', 'subtotal', 'updated_at']
    search_fields = ['user__email']
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    """Order item inline."""
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']


class OrderStatusHistoryInline(admin.TabularInline):
    """Order status history inline."""
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order admin."""
    
    list_display = [
        'order_number', 'user', 'total', 'status',
        'payment_status', 'shipping_status', 'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'shipping_status', 'created_at'
    ]
    search_fields = ['order_number', 'user__email', 'shipping_name']
    list_editable = ['status', 'payment_status', 'shipping_status']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payuee_order_id', 'payuee_escrow_status')
        }),
        ('Payment', {
            'fields': ('payment_status', 'subtotal', 'shipping_cost', 'tax', 'discount', 'total', 'currency')
        }),
        ('Shipping', {
            'fields': (
                'shipping_status', 'shipping_name', 'shipping_address',
                'shipping_city', 'shipping_state', 'shipping_country',
                'shipping_postal_code', 'shipping_phone'
            )
        }),
        ('Billing', {
            'fields': (
                'billing_name', 'billing_address', 'billing_city',
                'billing_state', 'billing_country', 'billing_postal_code'
            ),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'carrier', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('customer_note', 'admin_note'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order item admin."""
    
    list_display = [
        'order', 'product_name', 'quantity', 'unit_price', 'total_price'
    ]
    search_fields = ['order__order_number', 'product_name']
