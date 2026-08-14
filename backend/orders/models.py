"""
Models for the orders app.
Handles cart, orders, and order items.
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Cart(models.Model):
    """Shopping cart model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Cart - {self.user.email}"
    
    @property
    def total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        """Get cart subtotal."""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total(self):
        """Get cart total (same as subtotal for now)."""
        return self.subtotal


class CartItem(models.Model):
    """Cart item model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    @property
    def total_price(self):
        """Get total price for this item."""
        return self.product.price * self.quantity


class Order(models.Model):
    """Order model."""
    
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    SHIPPING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Order identification
    order_number = models.CharField(max_length=50, unique=True)
    
    # User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Order status
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    shipping_status = models.CharField(
        max_length=20,
        choices=SHIPPING_STATUS_CHOICES,
        default='pending'
    )
    
    # Payuee integration
    payuee_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Payuee order ID for escrow'
    )
    payuee_escrow_status = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Shipping address
    shipping_name = models.CharField(max_length=255)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_phone = models.CharField(max_length=20)
    
    # Billing address
    billing_name = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Notes
    customer_note = models.TextField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    carrier = models.CharField(max_length=100, blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Idempotency key for Payuee
    idempotency_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    # Coordinates for the shipping address - required by Payuee's
    # shipping-fees and order/create endpoints (accurate distance-based
    # shipping calculation). Previously not collected at all; the checkout
    # view silently defaulted to 0.0,0.0.
    shipping_latitude = models.FloatField(blank=True, null=True)
    shipping_longitude = models.FloatField(blank=True, null=True)

    # DEPRECATED / WRITE-DISABLED: this used to store the customer's raw
    # 6-digit Payuee transaction PIN in plaintext, which is a security
    # issue (the PIN is already correctly hashed on
    # User.payuee_transaction_pin_hash - it never needed a second, unhashed
    # copy here). `orders/views.py` no longer writes to this field; the PIN
    # is verified via User.check_payuee_pin() and passed to Payuee in
    # memory only, never persisted on the Order. Field is kept (rather than
    # dropped) to avoid a destructive migration on an existing table -
    # existing rows may still contain plaintext PINs from before this fix
    # and should be nulled out via a data-migration/backfill.
    trans_code = models.CharField(max_length=6, blank=True, null=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['payuee_order_id']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        """Generate order number if not set."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number."""
        import random
        import string
        from datetime import datetime
        
        # Format: GH-YYYYMMDD-XXXXX
        date_str = datetime.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"GH-{date_str}-{random_str}"


class OrderItem(models.Model):
    """Order item model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True, null=True)
    product_image = models.URLField(blank=True, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_items'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        """Calculate total price before saving."""
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.status}"
