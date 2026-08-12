"""
Serializers for the products app.
"""

from rest_framework import serializers
from .models import Category, Product, ProductReview, Wishlist, ProductView
import logging


logger = logging.getLogger(__name__)

# =========================
# MIXINS & HELPERS
# =========================

class BaseProductMixin:
    """Reusable helper for images and numeric safety."""
    
    def get_full_image_url(self, request, field):
        if field:
            try:
                url = field.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return None
        return None

    def fix_numeric_fields(self, data):
        """
        Forces numeric fields to be returned as floats/numbers 
        to prevent JavaScript 'toFixed' errors on the frontend.
        """
        # Handle Price
        if 'price' in data and data['price'] is not None:
            data['price'] = float(data['price'])
        
        # Handle Compare Price
        if 'compare_at_price' in data and data['compare_at_price'] is not None:
            data['compare_at_price'] = float(data['compare_at_price'])
            
        # Handle Rating (The main culprit for the toFixed error)
        data['average_rating'] = float(data.get('average_rating') or 0.0)
        
        # Handle Discount
        if 'discount_percentage' in data and data['discount_percentage'] is not None:
            data['discount_percentage'] = float(data['discount_percentage'])

        return data


# =========================
# CATEGORY SERIALIZERS
# =========================

class CategorySerializer(serializers.ModelSerializer, BaseProductMixin):
    """Serializer for categories."""
    
    subcategories = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 
            'parent', 'subcategories', 'product_count', 'is_active'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        return self.get_full_image_url(request, obj.image)

    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_active=True)
        return CategorySerializer(subcategories, many=True, context=self.context).data

    def get_product_count(self, obj):
        return obj.products.filter(status='active').count()


class SimpleCategorySerializer(serializers.ModelSerializer):
    """Simple category serializer for product listings."""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


# =========================
# PRODUCT REVIEW
# =========================

class ProductReviewSerializer(serializers.ModelSerializer, BaseProductMixin):
    """Serializer for product reviews."""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_image = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user_name', 'user_image', 'rating', 'title',
            'comment', 'is_verified_purchase', 'helpful_count', 'created_at'
        ]
        read_only_fields = ['is_approved', 'helpful_count']

    def get_user_image(self, obj):
        request = self.context.get('request')
        if hasattr(obj.user, 'profile_image'):
            return self.get_full_image_url(request, obj.user.profile_image)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure rating in reviews is also a float
        data['rating'] = float(data.get('rating') or 0.0)
        return data


# =========================
# PRODUCT LIST
# =========================

class ProductListSerializer(serializers.ModelSerializer, BaseProductMixin):
    """Serializer for product list view."""
    
    category = SimpleCategorySerializer(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        read_only=True
    )
    is_wishlisted = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'price', 'compare_at_price',
            'discount_percentage', 'featured_image', 'category',
            'is_in_stock', 'average_rating', 'review_count',
            'is_featured', 'is_wishlisted', 'created_at', 'source'
        ]

    def get_featured_image(self, obj):
        request = self.context.get('request')

        # featured_image is a plain URLField for both local and Payuee
        # products (not a Django ImageField) - it's already a full URL.
        if obj.featured_image:
            return obj.featured_image

        # Fall back to the first entry of the `images` JSON list.
        if obj.images:
            url = obj.images[0]
            return request.build_absolute_uri(url) if request and url.startswith('/') else url

        return None

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return self.fix_numeric_fields(data)


# =========================
# PRODUCT DETAIL
# =========================

class ProductDetailSerializer(serializers.ModelSerializer, BaseProductMixin):
    """Serializer for product detail view."""
    
    category = CategorySerializer(read_only=True)
    reviews = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        read_only=True
    )
    is_wishlisted = serializers.SerializerMethodField()
    specifications = serializers.JSONField()
    related_products = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'source', 'payuee_product_id',
            'description', 'short_description', 'specifications',
            'price', 'compare_at_price', 'discount_percentage', 'currency',
            'quantity', 'is_in_stock', 'is_low_stock', 'low_stock_threshold',
            'featured_image', 'images', 'category', 'status', 'is_featured',
            'meta_title', 'meta_description', 'meta_keywords',
            'average_rating', 'review_count', 'reviews',
            'is_wishlisted', 'related_products', 'created_at', 'updated_at'
        ]

    def get_featured_image(self, obj):
        request = self.context.get('request')

        if obj.featured_image:
            return obj.featured_image

        if obj.images:
            url = obj.images[0]
            return request.build_absolute_uri(url) if request and url.startswith('/') else url

        return None

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False

    def get_reviews(self, obj):
        # Only approved reviews, newest first, capped so a heavily-reviewed
        # product doesn't return an unbounded payload here. Use
        # /products/<slug>/reviews/ for full paginated review browsing.
        qs = obj.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')[:20]
        return ProductReviewSerializer(qs, many=True, context=self.context).data

    def get_related_products(self, obj):
        """Get related products from same category."""
        if obj.category:
            related = Product.objects.filter(
                category=obj.category,
                status='active'
            ).exclude(id=obj.id)[:4]
            
            # Debug log
            logger.info(f"Found {related.count()} related products for {obj.id}")
            
            return ProductListSerializer(
                related, 
                many=True, 
                context=self.context
            ).data
        return []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return self.fix_numeric_fields(data)


# =========================
# CREATE / UPDATE
# =========================

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating products."""
    
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'source', 'payuee_product_id',
            'category', 'description', 'short_description', 'specifications',
            'price', 'compare_at_price', 'cost_price', 'currency',
            'quantity', 'low_stock_threshold', 'track_inventory',
            'featured_image', 'images', 'status', 'is_featured',
            'meta_title', 'meta_description', 'meta_keywords'
        ]

    def validate_slug(self, value):
        instance = self.instance
        if Product.objects.filter(slug=value).exclude(
            id=instance.id if instance else None
        ).exists():
            raise serializers.ValidationError(
                "A product with this slug already exists."
            )
        return value


# =========================
# WISHLIST
# =========================

class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items."""
    
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'created_at']


class WishlistCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding items to wishlist."""
    
    class Meta:
        model = Wishlist
        fields = ['product']


# =========================
# SEARCH
# =========================

class ProductSearchSerializer(serializers.Serializer):
    """Serializer for product search."""
    
    query = serializers.CharField(required=True, min_length=2)
    category = serializers.UUIDField(required=False, allow_null=True)
    min_price = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    max_price = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )
    sort_by = serializers.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('newest', 'Newest First'),
            ('rating', 'Highest Rated')
        ],
        default='relevance'
    )