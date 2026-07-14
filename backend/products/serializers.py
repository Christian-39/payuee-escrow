"""
Serializers for the products app.
Handles both local DB products and live Payuee products.
"""

from rest_framework import serializers
from .models import Category, Product, ProductReview, Wishlist, ProductView
import logging


logger = logging.getLogger(__name__)


class BaseProductMixin:
    
    def get_full_image_url(self, request, field):
        if field:
            try:
                url = field.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return None
        return None

    def fix_numeric_fields(self, data):
        if 'price' in data and data['price'] is not None:
            data['price'] = float(data['price'])
        
        if 'compare_at_price' in data and data['compare_at_price'] is not None:
            data['compare_at_price'] = float(data['compare_at_price'])
            
        data['average_rating'] = float(data.get('average_rating') or 0.0)
        
        if 'discount_percentage' in data and data['discount_percentage'] is not None:
            data['discount_percentage'] = float(data['discount_percentage'])

        return data


class CategorySerializer(serializers.ModelSerializer, BaseProductMixin):
    
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
        return obj.products.filter(status='active', source='local').count()


class SimpleCategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductReviewSerializer(serializers.ModelSerializer, BaseProductMixin):
    
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
        data['rating'] = float(data.get('rating') or 0.0)
        return data


class ProductListSerializer(serializers.ModelSerializer, BaseProductMixin):
    """
    Serializer that handles BOTH:
    - Local Product model instances (from DB)
    - Plain dicts from Payuee API (live fetch, not saved)
    """
    
    category = SimpleCategorySerializer(read_only=True, required=False)
    is_in_stock = serializers.BooleanField(read_only=True, required=False)
    discount_percentage = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()
    payuee_product_id = serializers.SerializerMethodField()
    eshop_user_id = serializers.SerializerMethodField()
    source = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'price', 'compare_at_price',
            'discount_percentage', 'featured_image', 'category',
            'is_in_stock', 'average_rating', 'review_count',
            'is_featured', 'payuee_product_id', 'eshop_user_id',
            'is_wishlisted', 'created_at', 'source'
        ]

    def get_discount_percentage(self, obj):
        # Handle both Product model and plain dict
        if isinstance(obj, dict):
            return obj.get('discount_percentage', 0)
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            discount = ((obj.compare_at_price - obj.price) / obj.compare_at_price) * 100
            return round(discount, 2)
        return 0

    def get_payuee_product_id(self, obj):
        if isinstance(obj, dict):
            return obj.get('payuee_product_id')
        if obj.payuee_product_id:
            try:
                return int(obj.payuee_product_id)
            except (ValueError, TypeError):
                return None
        return None

    def get_eshop_user_id(self, obj):
        if isinstance(obj, dict):
            return obj.get('eshop_user_id')
        if obj.payuee_vendor_id:
            try:
                return int(obj.payuee_vendor_id)
            except (ValueError, TypeError):
                return None
        return None

    def get_featured_image(self, obj):
        request = self.context.get('request')
        
        # Handle plain dict (from Payuee live fetch)
        if isinstance(obj, dict):
            return obj.get('featured_image')
        
        # Handle Product model
        if obj.source == 'payuee' and obj.featured_image:
            return obj.featured_image
        
        if obj.images:
            try:
                url = obj.images.url
                return request.build_absolute_uri(url) if request else url
            except:
                return None
        
        return None

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if isinstance(obj, dict):
                return False  # Can't wishlist live Payuee products
            return Wishlist.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return self.fix_numeric_fields(data)


class ProductDetailSerializer(serializers.ModelSerializer, BaseProductMixin):
    """
    Handles both local Product instances and Payuee dicts.
    """
    
    category = CategorySerializer(read_only=True, required=False)
    reviews = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(read_only=True, required=False)
    is_low_stock = serializers.BooleanField(read_only=True, required=False)
    discount_percentage = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()
    specifications = serializers.JSONField(required=False)
    related_products = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()
    payuee_product_id = serializers.SerializerMethodField()
    eshop_user_id = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'source', 'payuee_product_id',
            'eshop_user_id', 'description', 'short_description', 'specifications',
            'price', 'compare_at_price', 'discount_percentage', 'currency',
            'quantity', 'is_in_stock', 'is_low_stock', 'low_stock_threshold',
            'featured_image', 'images', 'category', 'status', 'is_featured',
            'meta_title', 'meta_description', 'meta_keywords',
            'average_rating', 'review_count', 'reviews',
            'is_wishlisted', 'related_products', 'created_at', 'updated_at'
        ]

    def _get_attr(self, obj, attr, default=None):
        """Helper to get attr from dict or model."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def get_description(self, obj):
        return self._get_attr(obj, 'description', '')

    def get_short_description(self, obj):
        return self._get_attr(obj, 'short_description', '')

    def get_quantity(self, obj):
        return self._get_attr(obj, 'quantity', 0)

    def get_currency(self, obj):
        return self._get_attr(obj, 'currency', 'NGN')

    def get_status(self, obj):
        return self._get_attr(obj, 'status', 'active')

    def get_discount_percentage(self, obj):
        if isinstance(obj, dict):
            return obj.get('discount_percentage', 0)
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            discount = ((obj.compare_at_price - obj.price) / obj.compare_at_price) * 100
            return round(discount, 2)
        return 0

    def get_payuee_product_id(self, obj):
        if isinstance(obj, dict):
            return obj.get('payuee_product_id')
        if obj.payuee_product_id:
            try:
                return int(obj.payuee_product_id)
            except (ValueError, TypeError):
                return None
        return None

    def get_eshop_user_id(self, obj):
        if isinstance(obj, dict):
            return obj.get('eshop_user_id')
        if obj.payuee_vendor_id:
            try:
                return int(obj.payuee_vendor_id)
            except (ValueError, TypeError):
                return None
        return None

    def get_featured_image(self, obj):
        request = self.context.get('request')
        
        if isinstance(obj, dict):
            return obj.get('featured_image')
        
        if obj.source == 'payuee' and obj.featured_image:
            return obj.featured_image
        
        if obj.images:
            try:
                url = obj.images.url
                return request.build_absolute_uri(url) if request else url
            except:
                return None
        
        return None

    def get_reviews(self, obj):
        # Live Payuee products have no reviews
        if isinstance(obj, dict):
            return []
        
        reviews = ProductReview.objects.filter(
            product=obj,
            is_approved=True
        ).select_related('user')[:10]
        
        return ProductReviewSerializer(reviews, many=True, context=self.context).data

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if isinstance(obj, dict):
                return False
            return Wishlist.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False

    def get_related_products(self, obj):
        if isinstance(obj, dict):
            return []  # Live Payuee products have no related products
        
        if obj.category:
            related = Product.objects.filter(
                category=obj.category,
                status='active',
                source='local'
            ).exclude(id=obj.id)[:4]
            
            return ProductListSerializer(
                related, 
                many=True, 
                context=self.context
            ).data
        return []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return self.fix_numeric_fields(data)


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'sku', 'category', 'description', 
            'short_description', 'specifications',
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
    
    def create(self, validated_data):
        validated_data['source'] = 'local'
        return super().create(validated_data)


class WishlistSerializer(serializers.ModelSerializer):
    
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'created_at']


class WishlistCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Wishlist
        fields = ['product']


class ProductSearchSerializer(serializers.Serializer):
    
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
