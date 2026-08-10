"""
Models for the products app.
Handles product catalog, categories, and inventory.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid

User = get_user_model()


class Category(models.Model):
    """Product category model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True) 
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True) 
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model for both local and Payuee products."""
    
    PRODUCT_SOURCE_CHOICES = [
        ('local', 'Local'),
        ('payuee', 'Payuee'),
    ]
    
    PRODUCT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Product identification
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    
    # Product source (local or Payuee)
    source = models.CharField(
        max_length=10, 
        choices=PRODUCT_SOURCE_CHOICES, 
        default='local'
    )
    payuee_product_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text='Payuee product ID (integer, e.g., 92, 255)'
    )
    payuee_vendor_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text='Payuee vendor ID (eshop_user_id, e.g., 19, 51) - required for shipping-fee calculation'
    )
    payuee_vendor_type = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='Vendor subscription type (basic, premium, etc.)'
    )
    payuee_category = models.CharField(
        max_length=50, blank=True, null=True, db_index=True,
        help_text='Payuee category (e.g., outfits, jewelry, gadgets)'
    )
    payuee_product_url_id = models.CharField(
        max_length=255, blank=True, null=True,
        help_text='Payuee product URL slug (e.g., "italian-shoe-90")'
    )
    payuee_net_weight = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True,
        help_text='Product weight in kg from Payuee'
    )
    payuee_stock_remaining = models.PositiveIntegerField(
        blank=True, null=True,
        help_text='Stock count from Payuee API (stock_remaining field)'
    )
    payuee_estimated_delivery = models.PositiveIntegerField(
        blank=True, null=True,
        help_text='Estimated delivery days from Payuee'
    )
    payuee_clothing_sizes = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Available clothing sizes from Payuee (e.g., "S,M,L,XL")'
    )
    payuee_shoe_sizes = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Available shoe sizes from Payuee (e.g., "30-40")'
    )
    payuee_tags = models.JSONField(blank=True, default=list, help_text='Product tags from Payuee API')
    payuee_featured = models.BooleanField(default=False, help_text='Featured flag from Payuee')
    payuee_on_sale = models.BooleanField(default=False, help_text='On sale flag from Payuee')
    payuee_last_synced = models.DateTimeField(
        blank=True, null=True,
        help_text='Last time product data was synced from Payuee'
    )
    
    # Categorization
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='products'
    )
    
    # Product details
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True, null=True)
    specifications = models.JSONField(default=dict, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    cost_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True
    )
    currency = models.CharField(max_length=3, default='NGN')
    
    # Inventory
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    track_inventory = models.BooleanField(default=True)
    
    # Images
    featured_image = models.URLField(blank=True, null=True)
    images = models.JSONField(
        blank=True, default=list,
        help_text='List of image URLs. For Payuee products, prepend https://payuee.com/image/'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PRODUCT_STATUS_CHOICES,
        default='active'
    )
    is_featured = models.BooleanField(default=False)
    
    # SEO
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=500, blank=True, null=True)
    
    # Ratings
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00
    )
    review_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin who created/updated
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created'
    )
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['source']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        if not self.track_inventory:
            return True
        return self.quantity > 0
    
    @property
    def is_low_stock(self):
        """Check if product is low in stock."""
        if not self.track_inventory:
            return False
        return self.quantity <= self.low_stock_threshold
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.compare_at_price and self.compare_at_price > self.price:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount, 2)
        return 0


class ProductReview(models.Model):
    """Product review model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_reviews'
        unique_together = ['product', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name} - {self.rating} stars"


class Wishlist(models.Model):
    """User wishlist model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlisted_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'wishlists'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class ProductView(models.Model):
    """Track product views for analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='views'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    session_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_views'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.created_at}"