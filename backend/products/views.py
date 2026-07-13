# ============================================================
# FILE 9: products/views.py (UPDATED - Core App Catalog View)
# ============================================================
"""
Views for the products app.
Handles product catalog, search, wishlist, and reviews using an external API.
"""

import logging
import requests
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Category, Product, ProductReview, Wishlist, ProductView
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductReviewSerializer,
    WishlistSerializer,
    WishlistCreateSerializer,
    ProductSearchSerializer
)

logger = logging.getLogger(__name__)

PAYUEE_API_URL = "https://escrow.payuee.com/v1/products"  # Tracks active environment structure
CACHE_TTL = 600  # 10 minutes


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─────────────────────────────────────────────────────────────
# CATEGORY VIEWS
# ─────────────────────────────────────────────────────────────

class CategoryListView(generics.ListAPIView):
    """List all active categories."""
    queryset = Category.objects.filter(is_active=True, parent=None)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class CategoryDetailView(generics.RetrieveAPIView):
    """Get category details with products."""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


# ─────────────────────────────────────────────────────────────
# PRODUCT VIEWS — INTEGRATED WITH PAYUEE EXTERNAL API
# ─────────────────────────────────────────────────────────────

class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def list(self, request, *args, **kwargs):
        category_slug = request.query_params.get('category', '')
        min_price = request.query_params.get('min_price', '')
        max_price = request.query_params.get('max_price', '')
        in_stock = request.query_params.get('in_stock', '')
        ordering = request.query_params.get('ordering', '-created_at')
        page = request.query_params.get('page', '1')

        # Cache key mappings
        cache_key = f"payuee_catalog_list_{category_slug}_{min_price}_{max_price}_{in_stock}_{ordering}_{page}"
        products_data = cache.get(cache_key)

        if not products_data:
            params = {
                'category': category_slug,
                'min_price': min_price,
                'max_price': max_price,
                'in_stock': in_stock,
                'ordering': ordering,
                'page': page
            }
            params = {k: v for k, v in params.items() if v}

            try:
                response = requests.get(PAYUEE_API_URL, params=params, timeout=5)
                response.raise_for_status()
                products_data = response.json()
                cache.set(cache_key, products_data, CACHE_TTL)
            except requests.RequestException as e:
                logger.error(f"Payuee API Catalog Fetch Failed: {e}")
                return Response(
                    {"error": "Failed to fetch listings from external product service."},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        return Response(products_data, status=status.HTTP_200_OK)


class ProductDetailView(generics.RetrieveAPIView):
    """Get product details."""
    queryset = Product.objects.filter(status='active')
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        ProductView.objects.create(
            product=instance,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key if hasattr(request, 'session') else None,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FeaturedProductsView(generics.ListAPIView):
    """Get featured products."""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Product.objects.filter(
            status='active',
            is_featured=True
        ).select_related('category')[:20]


class RelatedProductsView(generics.ListAPIView):
    """Get related products for a product."""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug)
        
        if product.category:
            return Product.objects.filter(
                category=product.category,
                status='active'
            ).exclude(id=product.id)[:8]
        return Product.objects.none()


# ─────────────────────────────────────────────────────────────
# PRODUCT SEARCH — INTEGRATED WITH PAYUEE EXTERNAL API
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def search_products(request):
    """Search products via external service with advanced filters."""
    serializer = ProductSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    query = data.get('query', '')
    category_id = data.get('category', '')
    min_price = data.get('min_price', '')
    max_price = data.get('max_price', '')
    sort_by = data.get('sort_by', 'relevance')
    page = request.query_params.get('page', '1')

    cache_key = f"payuee_search_query_{query}_{category_id}_{min_price}_{max_price}_{sort_by}_{page}"
    search_results = cache.get(cache_key)

    if not search_results:
        params = {
            'search': query,
            'category': category_id,
            'min_price': min_price,
            'max_price': max_price,
            'sort_by': sort_by,
            'page': page
        }
        params = {k: v for k, v in params.items() if v}

        try:
            response = requests.get(PAYUEE_API_URL, params=params, timeout=5)
            response.raise_for_status()
            search_results = response.json()
            cache.set(cache_key, search_results, CACHE_TTL)
        except requests.RequestException as e:
            logger.error(f"Payuee Search Endpoint Failure: {e}")
            return Response(
                {"error": "Product catalog query service is temporarily offline."},
                status=status.HTTP_502_BAD_GATEWAY
            )

    return Response(search_results, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# WISHLIST VIEWS
# ─────────────────────────────────────────────────────────────

class WishlistListView(generics.ListAPIView):
    """List user's wishlist items."""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product', 'product__category')


class WishlistAddView(generics.CreateAPIView):
    """Add product to wishlist."""
    serializer_class = WishlistCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            return Response(
                {'message': 'Product is already in your wishlist.'},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'message': 'Product added to wishlist.',
                'wishlist_item': WishlistSerializer(wishlist_item).data
            },
            status=status.HTTP_201_CREATED
        )


class WishlistRemoveView(generics.DestroyAPIView):
    """Remove product from wishlist."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        product_id = self.kwargs.get('product_id')
        return get_object_or_404(
            Wishlist,
            user=self.request.user,
            product_id=product_id
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': 'Product removed from wishlist.'},
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist(request, product_id):
    """Toggle product in wishlist."""
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        product=product
    ).first()
    
    if wishlist_item:
        wishlist_item.delete()
        return Response({
            'in_wishlist': False,
            'message': 'Product removed from wishlist.'
        })
    else:
        Wishlist.objects.create(user=request.user, product=product)
        return Response({
            'in_wishlist': True,
            'message': 'Product added to wishlist.'
        })


# ─────────────────────────────────────────────────────────────
# PRODUCT REVIEW VIEWS
# ─────────────────────────────────────────────────────────────

class ProductReviewListView(generics.ListAPIView):
    """List reviews for a product."""
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug)
        return ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).select_related('user')


class ProductReviewCreateView(generics.CreateAPIView):
    """Create a product review."""
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        from rest_framework import serializers as drf_serializers
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug)
        
        existing_review = ProductReview.objects.filter(
            product=product,
            user=self.request.user
        ).first()
        
        if existing_review:
            raise drf_serializers.ValidationError(
                'You have already reviewed this product.'
            )
        
        from orders.models import OrderItem
        is_verified = OrderItem.objects.filter(
            order__user=self.request.user,
            product=product,
            order__status='delivered'
        ).exists()
        
        review = serializer.save(
            product=product,
            user=self.request.user,
            is_verified_purchase=is_verified
        )
        
        self.update_product_rating(product)
        return review
    
    def update_product_rating(self, product):
        ratings = ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        
        product.average_rating = ratings['avg_rating'] or 0
        product.review_count = ratings['count'] or 0
        product.save()


# ─────────────────────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

class AdminProductListCreateView(generics.ListCreateAPIView):
    """Admin: List and create products."""
    queryset = Product.objects.all()
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: Retrieve, update, delete product."""
    queryset = Product.objects.all()
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_categories_with_products(request):
    """Get categories with their products for homepage."""
    categories = Category.objects.filter(
        is_active=True,
        parent=None
    )[:6]
    
    result = []
    for category in categories:
        products = Product.objects.filter(
            category=category,
            status='active'
        ).select_related('category')[:4]
        
        result.append({
            'category': CategorySerializer(category).data,
            'products': ProductListSerializer(
                products, 
                many=True,
                context={'request': request}
            ).data
        })
    
    return Response(result)
