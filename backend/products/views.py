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
from django.core.cache import cache
from django.utils import timezone
from django.utils.text import slugify
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
    page_size = 20
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


PAYUEE_BOOTSTRAP_LOCK_KEY = 'payuee:bootstrap:lock'
PAYUEE_BOOTSTRAP_FAILED_KEY = 'payuee:bootstrap:last_error'
PAYUEE_BOOTSTRAP_LOCK_TTL = 60          # prevent concurrent requests from all triggering a fetch
PAYUEE_BOOTSTRAP_BACKOFF_TTL = 300      # if Payuee is down, don't hammer it on every request


def sync_payuee_products_to_db(products, cap=None):
    """
    Upsert a list of raw Payuee product dicts (as returned under the
    'success' key by /v1/products or /v1/products/search) into the local
    Product table. Shared by the request-time bootstrap, the management
    command, and the scheduled background task so there is a single source
    of truth for field mapping.

    Returns (synced_count, failed_count).
    """
    synced = 0
    failed = 0
    items = products if cap is None else products[:cap]

    for p in items:
        try:
            image_urls = [
                f"https://payuee.com/image/{img['url']}"
                for img in (p.get('product_image') or [])
                if img.get('url')
            ]
            featured_image = image_urls[0] if image_urls else None

            slug = p.get('product_url_id') or slugify(p.get('title', ''))[:50] or f"product-{p.get('ID')}"

            category_slug = slugify(p.get('category', 'others'))
            category, _ = Category.objects.get_or_create(
                slug=category_slug,
                defaults={'name': p.get('category', 'others'), 'is_active': True}
            )

            stock_remaining = p.get('stock_remaining', 0) or 0

            Product.objects.update_or_create(
                payuee_product_id=p['ID'],
                defaults={
                    'name': p.get('title', f"Product {p['ID']}"),
                    'slug': slug,
                    'description': p.get('description', ''),
                    'short_description': (p.get('description') or '')[:200],
                    'price': p.get('selling_price', 0),
                    'compare_at_price': p.get('initial_cost') or p.get('selling_price', 0),
                    'quantity': stock_remaining,
                    'category': category,
                    'featured_image': featured_image,
                    'images': image_urls,
                    'source': 'payuee',
                    'status': 'active' if stock_remaining > 0 else 'out_of_stock',
                    'is_featured': p.get('featured', False),
                    'review_count': p.get('product_review_count', 0),
                    'payuee_vendor_id': p.get('eshop_user_id'),
                    'payuee_vendor_type': p.get('vendor_type'),
                    'payuee_category': p.get('category'),
                    'payuee_product_url_id': p.get('product_url_id'),
                    'payuee_net_weight': p.get('net_weight'),
                    'payuee_stock_remaining': stock_remaining,
                    'payuee_estimated_delivery': p.get('estimated_delivery'),
                    'payuee_clothing_sizes': p.get('clothing_sizes') or None,
                    'payuee_shoe_sizes': p.get('shoe_sizes') or None,
                    'payuee_featured': p.get('featured', False),
                    'payuee_on_sale': p.get('on_sale', False),
                    'payuee_last_synced': timezone.now(),
                }
            )
            synced += 1
        except Exception as e:
            logger.error(f"Failed to sync Payuee product {p.get('ID')}: {e}")
            failed += 1
            continue

    return synced, failed


# Product Views
class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        self._maybe_bootstrap_from_payuee()

        queryset = Product.objects.filter(status='active')

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

    def _maybe_bootstrap_from_payuee(self):
        """
        Cold-start safety net only: if the local catalog has never been
        synced from Payuee at all (e.g. first deploy, before the scheduled
        background job / `sync_payuee` management command has run), do a
        one-time, rate-limited, bounded fetch so the site isn't empty.

        This intentionally does NOT run on every request - regular product
        freshness is the responsibility of `products.tasks.sync_payuee_products`
        (scheduled) or `python manage.py sync_payuee` (manual), both of which
        now work correctly since PayueeClient.get_all_store_products exists.
        """
        if Product.objects.filter(source='payuee').exists():
            return

        if cache.get(PAYUEE_BOOTSTRAP_LOCK_KEY) or cache.get(PAYUEE_BOOTSTRAP_FAILED_KEY):
            return

        cache.set(PAYUEE_BOOTSTRAP_LOCK_KEY, True, PAYUEE_BOOTSTRAP_LOCK_TTL)

        try:
            client = get_payuee_client()
            result = client.get_all_store_products(max_pages=3, category='all', max_distance=10000)

            if not result.get('success'):
                logger.error(f"Payuee cold-start bootstrap failed: {result.get('error')}")
                cache.set(PAYUEE_BOOTSTRAP_FAILED_KEY, result.get('error'), PAYUEE_BOOTSTRAP_BACKOFF_TTL)
                return

            products = result.get('data', {}).get('success', [])
            synced, failed = sync_payuee_products_to_db(products)
            logger.info(f"Payuee cold-start bootstrap: synced={synced} failed={failed}")

        except Exception as e:
            logger.error(f"Payuee cold-start bootstrap exception: {e}")
            cache.set(PAYUEE_BOOTSTRAP_FAILED_KEY, str(e), PAYUEE_BOOTSTRAP_BACKOFF_TTL)


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_wishlist_count(request):
    """Count of the current user's wishlist items (used by the profile page)."""
    count = Wishlist.objects.filter(user=request.user).count()
    return Response({'count': count})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_reviews_count(request):
    """Count of reviews the current user has written (used by the profile page)."""
    count = ProductReview.objects.filter(user=request.user).count()
    return Response({'count': count})


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
        
        # Only purchased (delivered) products can be reviewed - this is
        # enforced, not just recorded as a cosmetic flag.
        from orders.models import OrderItem
        is_verified = OrderItem.objects.filter(
            order__user=self.request.user,
            product=product,
            order__status='delivered'
        ).exists()

        if not is_verified:
            raise serializers.ValidationError(
                'You can only review products from orders that have been delivered to you.'
            )
        
        # Verified-purchase reviews are auto-approved. is_approved defaults
        # to False on the model (for a manual admin moderation path), but
        # nothing ever flipped it to True except editing it by hand in
        # Django admin - so every review was invisible on the storefront
        # forever. Since we now only accept reviews from real delivered
        # orders, auto-approving is safe; admins can still unpublish a
        # review via is_approved in Django admin if needed.
        review = serializer.save(
            product=product,
            user=self.request.user,
            is_verified_purchase=True,
            is_approved=True,
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
