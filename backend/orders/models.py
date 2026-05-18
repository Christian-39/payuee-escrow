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
    selected_size = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text='Selected size (clothing or shoe size from Payuee)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product', 'selected_size']
        ordering = ['-created_at']
    
    def __str__(self):
        size_str = f" (Size: {self.selected_size})" if self.selected_size else ""
        return f"{self.product.name}{size_str} x {self.quantity}"
    
    @property
    def total_price(self):
        """Get total price for this item."""
        return self.product.price * self.quantity


class Order(models.Model):
    """Order model with full Payuee escrow integration."""
    
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
    
    # ── Payuee Escrow Status Choices ──
    # Maps to Payuee API order lifecycle: CREATED → ESCROW_LOCKED → CONFIRMED → DELIVERED → RELEASED
    PAYUEE_ESCROW_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('created', 'Created'),
        ('escrow_locked', 'Escrow Locked'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('released', 'Released'),
        ('hold', 'On Hold'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
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
    
    # ── Payuee Integration Fields ──
    # Payuee creates MULTIPLE orders (one per vendor), so we store them as a list
    payuee_order_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='List of Payuee order IDs returned from create_order: [10293, 34523]'
    )
    payuee_escrow_status = models.CharField(
        max_length=50,
        choices=PAYUEE_ESCROW_STATUS_CHOICES,
        default='pending',
        help_text='Payuee escrow lifecycle status'
    )
    
    # Customer transaction PIN (6 digits, set by customer during checkout)
    trans_code = models.CharField(
        max_length=6,
        blank=True,
        help_text='Customer 6-digit transaction PIN for delivery verification'
    )
    
    # Webhook URL for this order
    webhook_response_url = models.URLField(
        blank=True,
        help_text='URL where Payuee sends webhook events for this order'
    )
    
    # Store the exact payload sent to Payuee for debugging/retries
    payuee_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text='Validated payload sent to Payuee API'
    )
    
    # Store Payuee response for reference
    payuee_response = models.JSONField(
        default=dict,
        blank=True,
        help_text='Raw response from Payuee API'
    )
    
    # QR code scan status
    scanned_qr_code = models.BooleanField(
        default=False,
        help_text='Whether delivery QR code has been scanned'
    )
    
    # Credit/settlement processed flag
    credit_processed = models.BooleanField(
        default=False,
        help_text='Whether escrow funds have been released/settled'
    )
    
    # ── Pricing ──
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    
    # ── Shipping Address ──
    shipping_name = models.CharField(max_length=255)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_phone = models.CharField(max_length=20)
    
    # Customer email (from Payuee customer object)
    customer_email = models.EmailField(blank=True, null=True)
    customer_first_name = models.CharField(max_length=100, blank=True, null=True)
    customer_last_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Delivery coordinates
    shipping_latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        blank=True, 
        null=True
    )
    shipping_longitude = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        blank=True, 
        null=True
    )
    
    # ── Billing Address ──
    billing_name = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    billing_postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # ── Notes ──
    customer_note = models.TextField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    
    # ── Tracking ──
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    carrier = models.CharField(max_length=100, blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # Estimated delivery from Payuee
    estimated_delivery_days = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Estimated delivery days from Payuee'
    )
    
    # ── Timestamps ──
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ── Idempotency ──
    idempotency_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text='Unique key for Payuee idempotency'
    )
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['payuee_escrow_status']),
            models.Index(fields=['created_at']),
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
    
    @property
    def primary_payuee_order_id(self):
        """Get the first Payuee order ID for single-order operations."""
        if self.payuee_order_ids and isinstance(self.payuee_order_ids, list):
            return self.payuee_order_ids[0]
        return None
    
    @property
    def is_on_hold(self):
        """Check if order is on hold due to insufficient wallet."""
        return self.payuee_escrow_status == 'hold'
    
    @property
    def can_cancel(self):
        """Check if order can still be cancelled (within 30% of delivery timeline)."""
        if self.payuee_escrow_status in ['cancelled', 'refunded', 'released', 'delivered']:
            return False
        # TODO: Add time-based check (30% of estimated delivery)
        return True


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
    
    # Payuee-specific item fields
    payuee_product_id = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Payuee product ID for this item'
    )
    payuee_vendor_id = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Payuee vendor ID for this item'
    )
    selected_size = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text='Selected size (outfit_size or shoe_size)'
    )
    
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order_items'
        ordering = ['-created_at']
    
    def __str__(self):
        size_str = f" (Size: {self.selected_size})" if self.selected_size else ""
        return f"{self.product_name}{size_str} x {self.quantity}"
    
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