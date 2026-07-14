"""
Views for the products app.
Fetches Payuee products LIVE from API without saving to database.
Only manually-added local products are stored in DB.
"""

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
import logging

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

# Import Payuee client for live fetching
from payments.payuee_client import PayueeClient, get_payuee_client

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─────────────────────────────────────────────────────────────
# HELPER: Convert Payuee product dict to Product-like object
# ─────────────────────────────────────────────────────────────

def payuee_product_to_dict(p):
    """
    Convert a Payuee API product dict into a format
    that matches our Product serializer fields.
    No database saving — just format for display.
    """
    # Get first image URL
    featured_image = None
    if p.get('product_image') and len(p['product_image']) > 0:
        image_path = p['product_image'][0].get('url', '')
        if image_path:
            featured_image = f"https://payuee.com/image/{image_path}"
    
    # Calculate discount
    selling_price = float(p.get('selling_price', 0))
    initial_cost = float(p.get('initial_cost', selling_price))
    discount = 0
    if initial_cost > selling_price:
        discount = round(((initial_cost - selling_price) / initial_cost) * 100, 2)
    
    return {
        'id': f"payuee_{p.get('ID')}",  # Prefix to avoid ID collision
        'name': p.get('title', 'Unknown Product'),
        'slug': p.get('product_url_id', f"product-{p.get('ID')}"),
        'sku': str(p.get('ID', '')),
        'price': selling_price,
        'compare_at_price': initial_cost if initial_cost != selling_price else None,
        'discount_percentage': discount,
        'featured_image': featured_image,
        'category': None,  # Will be handled separately if needed
        'is_in_stock': p.get('stock_remaining', 0) > 0,
        'average_rating': 0.0,
        'review_count': p.get('product_review_count', 0),
        'is_featured': p.get('featured', False),
        'is_wishlisted': False,  # Can't wishlist non-saved products
        'created_at': None,
        'source': 'payuee',
        'payuee_product_id': p.get('ID'),
        'eshop_user_id': p.get('eshop_user_id'),
        'description': p.get('description', ''),
        'short_description': (p.get('description', '') or '')[:200],
        'quantity': p.get('stock_remaining', 0),
        'currency': 'NGN',
        'status': 'active' if p.get('stock_remaining', 0) > 0 else 'out_of_stock',
        'specifications': {},
        'images': [],
        'is_low_stock': False,
        'low_stock_threshold': 10,
        'meta_title': None,
        'meta_description': None,
        'meta_keywords': None,
    }


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
# PRODUCT LIST — LIVE FETCH FROM PAYUEE + LOCAL DB
# ─────────────────────────────────────────────────────────────

class ProductListView(generics.ListAPIView):
    """
    List products: fetches Payuee products LIVE from API
    and combines with local products. Nothing is saved to DB.
    """
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Only return LOCAL products from DB
        # Payuee products are fetched separately in list()
        queryset = Product.objects.filter(status='active', source='local')
        
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        in_stock = self.request.query_params.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(quantity__gt=0)
        
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset.select_related('category')
    
    def list(self, request, *args, **kwargs):
        # Get local products from DB
        local_queryset = self.get_queryset()
        local_page = self.paginate_queryset(local_queryset)
        
        local_serializer = self.get_serializer(
            local_page if local_page is not None else local_queryset,
            many=True,
            context={'request': request}
        )
        local_data = local_serializer.data
        
        # Fetch Payuee products LIVE (not saved to DB)
        payuee_data = []
        try:
            client = get_payuee_client()
            category = request.query_params.get('category', 'all')
            result = client.get_all_store_products(
                max_pages=2,  # Limit pages to avoid slow response
                category=category if category != 'all' else 'all'
            )
            
            if result.get('success'):
                products = result.get('data', {}).get('success', [])
                for p in products:
                    payuee_data.append(payuee_product_to_dict(p))
                    
        except Exception as e:
            logger.error(f"Error fetching live Payuee products: {e}")
            # Continue with just local products if Payuee fails
        
        # Combine: local products first, then Payuee products
        combined_data = local_data + payuee_data
        
        # Apply pagination to combined results
        page_size = self.paginator.page_size
        page_number = int(request.query_params.get('page', 1))
        start = (page_number - 1) * page_size
        end = start + page_size
        paginated_data = combined_data[start:end]
        
        return Response({
            'count': len(combined_data),
            'next': f"?page={page_number + 1}" if end < len(combined_data) else None,
            'previous': f"?page={page_number - 1}" if page_number > 1 else None,
            'results': paginated_data
        })


# ─────────────────────────────────────────────────────────────
# PRODUCT DETAIL — LIVE FETCH FROM PAYUEE + LOCAL DB
# ─────────────────────────────────────────────────────────────

class ProductDetailView(generics.RetrieveAPIView):
    """
    Get product details: checks local DB first,
    if not found, fetches LIVE from Payuee API.
    Nothing is saved to DB.
    """
    queryset = Product.objects.filter(status='active', source='local')
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        
        # Try to find in local DB first
        try:
            instance = Product.objects.get(slug=slug, source='local')
            
            # Track product view for local products
            ProductView.objects.create(
                product=instance,
                user=request.user if request.user.is_authenticated else None,
                session_id=request.session.session_key if hasattr(request, 'session') else None,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except Product.DoesNotExist:
            # Not in local DB — try Payuee LIVE
            pass
        
        # Check if it's a Payuee product (slug might contain payuee ID)
        # Try to fetch from Payuee by treating slug as product_url_id
        try:
            client = get_payuee_client()
            
            # Search for product by URL ID in Payuee
            result = client.search_products(
                search_term=slug,
                limit=10
            )
            
            if result.get('success'):
                products = result.get('data', {}).get('success', [])
                for p in products:
                    if p.get('product_url_id') == slug or str(p.get('ID')) in slug:
                        product_dict = payuee_product_to_dict(p)
                        # Convert to Product-like object for serializer
                        return Response(product_dict)
            
            # If not found by search, try direct ID if slug is numeric
            if slug.isdigit():
                result = client.get_product(int(slug))
                if result.get('success'):
                    p = result.get('data', {})
                    product_dict = payuee_product_to_dict(p)
                    return Response(product_dict)
                    
        except Exception as e:
            logger.error(f"Error fetching live Payuee product detail: {e}")
        
        return Response(
            {'detail': 'Product not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class FeaturedProductsView(generics.ListAPIView):
    """Get featured products — local only."""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Product.objects.filter(
            status='active',
            is_featured=True,
            source='local'
        ).select_related('category')[:20]


class RelatedProductsView(generics.ListAPIView):
    """Get related products for a product."""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug, source='local')
        
        if product.category:
            return Product.objects.filter(
                category=product.category,
                status='active',
                source='local'
            ).exclude(id=product.id)[:8]
        return Product.objects.none()


# ─────────────────────────────────────────────────────────────
# PRODUCT SEARCH — LIVE FETCH FROM PAYUEE + LOCAL DB
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def search_products(request):
    """
    Search products: searches local DB + fetches LIVE from Payuee.
    Nothing is saved to DB.
    """
    serializer = ProductSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    query = data.get('query', '')
    category_id = data.get('category')
    min_price = data.get('min_price')
    max_price = data.get('max_price')
    sort_by = data.get('sort_by', 'relevance')
    
    # Search local products
    local_queryset = Product.objects.filter(status='active', source='local')
    
    if query:
        local_queryset = local_queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(sku__icontains=query)
        )
    
    if category_id:
        local_queryset = local_queryset.filter(category_id=category_id)
    
    if min_price:
        local_queryset = local_queryset.filter(price__gte=min_price)
    if max_price:
        local_queryset = local_queryset.filter(price__lte=max_price)
    
    if sort_by == 'price_low':
        local_queryset = local_queryset.order_by('price')
    elif sort_by == 'price_high':
        local_queryset = local_queryset.order_by('-price')
    elif sort_by == 'newest':
        local_queryset = local_queryset.order_by('-created_at')
    elif sort_by == 'rating':
        local_queryset = local_queryset.order_by('-average_rating')
    
    local_serializer = ProductListSerializer(
        local_queryset,
        many=True,
        context={'request': request}
    )
    local_results = local_serializer.data
    
    # Search Payuee LIVE
    payuee_results = []
    try:
        client = get_payuee_client()
        result = client.search_products(
            search_term=query,
            limit=50,
            category='all'
        )
        
        if result.get('success'):
            products = result.get('data', {}).get('success', [])
            for p in products:
                payuee_dict = payuee_product_to_dict(p)
                # Apply price filters to Payuee results too
                price = payuee_dict.get('price', 0)
                if min_price and price < float(min_price):
                    continue
                if max_price and price > float(max_price):
                    continue
                payuee_results.append(payuee_dict)
                
    except Exception as e:
        logger.error(f"Error searching live Payuee products: {e}")
    
    # Combine results
    combined = local_results + payuee_results
    
    # Apply sorting to combined
    if sort_by == 'price_low':
        combined.sort(key=lambda x: float(x.get('price', 0)))
    elif sort_by == 'price_high':
        combined.sort(key=lambda x: float(x.get('price', 0)), reverse=True)
    
    # Paginate
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(combined, request)
    
    if page is not None:
        return paginator.get_paginated_response(page)
    
    return Response(combined)


# ─────────────────────────────────────────────────────────────
# WISHLIST VIEWS — LOCAL ONLY
# ─────────────────────────────────────────────────────────────

class WishlistListView(generics.ListAPIView):
    """List user's wishlist items — local products only."""
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user,
            product__source='local'
        ).select_related('product', 'product__category')


class WishlistAddView(generics.CreateAPIView):
    """Add product to wishlist — local products only."""
    serializer_class = WishlistCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product = serializer.validated_data['product']
        
        # Only local products can be wishlisted
        if product.source != 'local':
            return Response(
                {'message': 'Only local products can be added to wishlist.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
    """Toggle product in wishlist — local products only."""
    product = get_object_or_404(Product, id=product_id)
    
    if product.source != 'local':
        return Response(
            {'message': 'Only local products can be added to wishlist.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
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
# PRODUCT REVIEW VIEWS — LOCAL ONLY
# ─────────────────────────────────────────────────────────────

class ProductReviewListView(generics.ListAPIView):
    """List reviews for a product — local products only."""
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug, source='local')
        return ProductReview.objects.filter(
            product=product,
            is_approved=True
        ).select_related('user')


class ProductReviewCreateView(generics.CreateAPIView):
    """Create a product review — local products only."""
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        from rest_framework import serializers as drf_serializers
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug, source='local')
        
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
# ADMIN VIEWS — LOCAL ONLY
# ─────────────────────────────────────────────────────────────

class AdminProductListCreateView(generics.ListCreateAPIView):
    """Admin: List and create local products only."""
    queryset = Product.objects.filter(source='local')
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, source='local')


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: Manage local products only."""
    queryset = Product.objects.filter(source='local')
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_categories_with_products(request):
    """Get categories with their LOCAL products for homepage."""
    categories = Category.objects.filter(
        is_active=True,
        parent=None
    )[:6]
    
    result = []
    for category in categories:
        products = Product.objects.filter(
            category=category,
            status='active',
            source='local'
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
