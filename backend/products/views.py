"""
Views for the products app.
Handles product catalog, search, wishlist, and reviews.
"""

from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from payments.payuee_client import get_payuee_client
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

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# Category Views
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


# Product Views
class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        # Fetch and sync from Payuee (with caching to avoid rate limits)
        try:
            client = get_payuee_client()
            result = client.get_store_products()
            # DEBUG LOGGING
            logger.info(f"=== PAYUEE DEBUG ===")
            logger.info(f"Result success: {result.get('success')}")
            logger.info(f"Result error: {result.get('error')}")  # ADD THIS
            logger.info(f"Result status_code: {result.get('status_code')}") 
            logger.info(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
            
            if result['success']:
                logger.info(f"Payuee data keys: {result['data'].keys()}") # DEBUG
                self._sync_payuee_products(result['data'])
        except Exception as e:
            logger.error(f"Failed to sync Payuee products: {e}")
            # Fail silently, serve cached/local products
        
        # Return local products (including synced ones)
        queryset = Product.objects.filter(status='active')
        logger.info(f"Local products count: {queryset.count()}")  # DEBUG
        
        # Apply filters from query params
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
        
        # Apply sorting
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset.select_related('category')
    
    def _sync_payuee_products(self, data):
        """Sync Payuee products to local database."""
        # FIXED: "success" is directly the array of products
        products = data.get('success', [])
        logger.info(f"Payuee returned {len(products)} products")  # DEBUG
        
        for p in products[:5]:
            try:
                # Get first image URL if available
                logger.info(f"Syncing product: {p.get('ID')} - {p.get('title')}")  # DEBUG
                featured_image = None
                if p.get('product_image') and len(p['product_image']) > 0:
                    image_path = p['product_image'][0]['url']
                    featured_image = f"https://payuee.com/image/{image_path}"
                
                # Create slug from product_url_id or title
                slug = p.get('product_url_id', '')
                if not slug:
                    slug = p['title'].lower().replace(' ', '-')[:50]
                
                Product.objects.update_or_create(
                    payuee_product_id=str(p['ID']),
                    defaults={
                        'name': p['title'],
                        'slug': slug,
                        'description': p.get('description', ''),
                        'short_description': p.get('description', '')[:200] if p.get('description') else '',
                        'price': p['selling_price'],
                        'compare_at_price': p.get('initial_cost', p['selling_price']),
                        'quantity': p.get('stock_remaining', 0),
                        'category_id': self._get_or_create_category(p.get('category', 'others')),
                        'featured_image': f"https://payuee.com/image/{p['product_image'][0]['url']}" if p.get('product_image') else None,
                        'source': 'payuee',
                        'status': 'active' if p.get('stock_remaining', 0) > 0 else 'out_of_stock',
                        'is_featured': p.get('featured', False),
                        'average_rating': 0,  # Payuee doesn't provide this
                        'review_count': p.get('product_review_count', 0),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to sync product {p.get('ID')}: {e}")
                continue
    
    def _get_or_create_category(self, category_name):
        """Get or create category by name."""
        from django.utils.text import slugify
        slug = slugify(category_name)
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': category_name, 'is_active': True}
        )
        return category.id


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
        
        # Track product view
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
        """Get client IP address."""
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


# Product Search
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def search_products(request):
    """Search products with advanced filters."""
    serializer = ProductSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    query = data.get('query', '')
    category_id = data.get('category')
    min_price = data.get('min_price')
    max_price = data.get('max_price')
    sort_by = data.get('sort_by', 'relevance')
    
    # Base queryset
    queryset = Product.objects.filter(status='active')
    
    # Apply search query
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query) |
            Q(sku__icontains=query)
        )
    
    # Apply category filter
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    # Apply price filters
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)
    
    # Apply sorting
    if sort_by == 'price_low':
        queryset = queryset.order_by('price')
    elif sort_by == 'price_high':
        queryset = queryset.order_by('-price')
    elif sort_by == 'newest':
        queryset = queryset.order_by('-created_at')
    elif sort_by == 'rating':
        queryset = queryset.order_by('-average_rating')
    
    # Paginate results
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = ProductListSerializer(
            page, 
            many=True, 
            context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)
    
    serializer = ProductListSerializer(
        queryset, 
        many=True, 
        context={'request': request}
    )
    return Response(serializer.data)


# Wishlist Views
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
        
        # Check if already in wishlist
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


# Product Review Views
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
        product_slug = self.kwargs.get('slug')
        product = get_object_or_404(Product, slug=product_slug)
        
        # Check if user has already reviewed this product
        existing_review = ProductReview.objects.filter(
            product=product,
            user=self.request.user
        ).first()
        
        if existing_review:
            raise serializers.ValidationError(
                'You have already reviewed this product.'
            )
        
        # Check if user has purchased this product
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
        
        # Update product rating
        self.update_product_rating(product)
        
        return review
    
    def update_product_rating(self, product):
        """Update product average rating."""
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


# Admin Product Management
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
