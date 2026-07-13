# ============================================================
# FILE 9: products/views.py (FIXED)
# ============================================================
"""
Views for the products app.
Handles product catalog, search, wishlist, and reviews with strict field guarantees.
"""

import logging
import requests
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.http import Http404

from rest_framework import generics, status, permissions
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

PAYUEE_API_URL = "https://escrow.payuee.com/v1/products"
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
# PRODUCT VIEWS
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
                logger.error(f"Payuee API Catalog Fetch Failed: {e}. Falling back to internal DB.")
                
                queryset = Product.objects.filter(status='active')
                if category_slug:
                    queryset = queryset.filter(category__slug=category_slug)
                
                page_data = self.paginate_queryset(queryset)
                if page_data is not None:
                    serializer = self.get_serializer(page_data, many=True)
                    return self.get_paginated_response(serializer.data)
                
                serializer = self.get_serializer(queryset, many=True)
                return Response({"results": serializer.data}, status=status.HTTP_200_OK)

        return Response(products_data, status=status.HTTP_200_OK)


class ProductDetailView(generics.RetrieveAPIView):
    """Get product details by local database slug with external passthrough resilience."""
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_object(self):
        slug = self.kwargs.get('slug')
        
        # 1. Try active local products
        product = Product.objects.filter(slug=slug, status='active').first()
        if product:
            return product
            
        # 2. Relax status constraints to catch draft/inactive entries
        product = Product.objects.filter(slug=slug).first()
        if product:
            return product
            
        # 3. Fallback check for external ID strings matching lookup parameter
        product = Product.objects.filter(payuee_product_id=slug).first()
        if product:
            return product
            
        raise Http404("Product profile does not exist locally.")
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            # Absolute baseline fallback if product is purely hosted on external Payuee side
            slug_param = self.kwargs.get('slug')
            try:
                res = requests.get(f"{PAYUEE_API_URL}/{slug_param}/", timeout=4)
                if res.status_code == 200:
                    return Response(res.json(), status=status.HTTP_200_OK)
            except Exception:
                pass
            raise Http404("Product profile not found anywhere.")

        # Track view analytics logs safely
        try:
            ProductView.objects.create(
                product=instance,
                user=request.user if request.user.is_authenticated else None,
                session_id=request.session.session_key if hasattr(request, 'session') else None,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except Exception as e:
            logger.warning(f"Failed to write analytics view: {e}")
        
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Explicitly build related products fallback inside response dict
        related_qs = Product.objects.none()
        if instance.category:
            related_qs = Product.objects.filter(category=instance.category).exclude(id=instance.id)[:4]
        
        data['related_products'] = ProductListSerializer(
            related_qs, 
            many=True, 
            context={'request': request}
        ).data

        # Merge external payuee meta objects safely if map exists
        if instance.payuee_product_id:
            cache_key = f"external_payuee_detail_enrich_{instance.payuee_product_id}"
            enriched_info = cache.get(cache_key)
            if not enriched_info:
                try:
                    res = requests.get(f"{PAYUEE_API_URL}/{instance.payuee_product_id}/", timeout=3)
                    if res.status_code == 200:
                        enriched_info = res.json()
                        cache.set(cache_key, enriched_info, CACHE_TTL)
                except Exception as e:
                    logger.warning(f"Could not enrich item details from Payuee: {e}")
            
            if enriched_info:
                data['external_details'] = enriched_info

        return Response(data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# PRODUCT SEARCH
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
        except requests.RequestException:
            queryset = Product.objects.filter(status='active').filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            return Response({"results": ProductListSerializer(queryset, many=True, context={'request': request}).data})

    return Response(search_results, status=status.HTTP_200_OK)


class FeaturedProductsView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(is_featured=True).select_related('category')[:20]


class RelatedProductsView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        product = Product.objects.filter(slug=product_slug).first()
        if product and product.category:
            return Product.objects.filter(category=product.category).exclude(id=product.id)[:8]
        return Product.objects.none()


# ─────────────────────────────────────────────────────────────
# WISHLIST VIEWS
# ─────────────────────────────────────────────────────────────

class WishlistListView(generics.ListAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product', 'product__category')


class WishlistAddView(generics.CreateAPIView):
    serializer_class = WishlistCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data['product']
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        return Response({'message': 'Product configured in wishlist.'}, status=status.HTTP_201_CREATED)


class WishlistRemoveView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return get_object_or_404(Wishlist, user=self.request.user, product_id=self.kwargs.get('product_id'))


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    if wishlist_item:
        wishlist_item.delete()
        return Response({'in_wishlist': False})
    Wishlist.objects.create(user=request.user, product=product)
    return Response({'in_wishlist': True})


# ─────────────────────────────────────────────────────────────
# PRODUCT REVIEW VIEWS
# ─────────────────────────────────────────────────────────────

class ProductReviewListView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return ProductReview.objects.filter(product__slug=self.kwargs.get('slug'), is_approved=True).select_related('user')


class ProductReviewCreateView(generics.CreateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        product = get_object_or_404(Product, slug=self.kwargs.get('slug'))
        serializer.save(product=product, user=self.request.user)


# ─────────────────────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

class AdminProductListCreateView(generics.ListCreateAPIView):
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
    queryset = Product.objects.all()
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_categories_with_products(request):
    categories = Category.objects.filter(is_active=True, parent=None)[:6]
    result = []
    for category in categories:
        products = Product.objects.filter(category=category)[:4]
        result.append({
            'category': CategorySerializer(category).data,
            'products': ProductListSerializer(products, many=True, context={'request': request}).data
        })
    return Response(result)
