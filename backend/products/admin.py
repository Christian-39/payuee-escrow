"""
Admin configuration for products app.
"""

from django.contrib import admin
from .models import Category, Product, ProductReview, Wishlist, ProductView


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin."""
    
    list_display = ['name', 'slug', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin."""
    
    list_display = [
        'name', 'sku', 'category', 'price', 'quantity',
        'status', 'is_featured', 'source', 'created_at'
    ]
    list_filter = [
        'status', 'is_featured', 'source', 'category', 'created_at'
    ]
    search_fields = ['name', 'sku', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'quantity', 'status', 'is_featured']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category', 'source', 'payuee_product_id')
        }),
        ('Description', {
            'fields': ('description', 'short_description', 'specifications')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price', 'cost_price', 'currency')
        }),
        ('Inventory', {
            'fields': ('quantity', 'low_stock_threshold', 'track_inventory')
        }),
        ('Images', {
            'fields': ('featured_image', 'images')
        }),
        ('Status', {
            'fields': ('status', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Ratings', {
            'fields': ('average_rating', 'review_count'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """Product review admin."""
    
    list_display = [
        'product', 'user', 'rating', 'is_verified_purchase',
        'is_approved', 'created_at'
    ]
    list_filter = ['rating', 'is_verified_purchase', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__email', 'comment']
    list_editable = ['is_approved']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Wishlist admin."""
    
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__email', 'product__name']


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    """Product view admin."""
    
    list_display = ['product', 'user', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'user__email']
