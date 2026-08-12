"""
Views for the payments app.
Handles wallet and transaction management.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Transaction, Wallet, WalletTransaction
from .serializers import (
    TransactionSerializer,
    WalletSerializer,
    WalletTransactionSerializer
)
from .payuee_client import PayueeClient


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class WalletView(generics.RetrieveAPIView):
    """Get user's wallet."""
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(
            user=self.request.user,
            defaults={'currency': 'USD'}
        )
        return wallet


class WalletTransactionListView(generics.ListAPIView):
    """List wallet transactions."""
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        wallet, created = Wallet.objects.get_or_create(
            user=self.request.user,
            defaults={'currency': 'USD'}
        )
        return WalletTransaction.objects.filter(wallet=wallet)


class TransactionListView(generics.ListAPIView):
    """List user's transactions."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related('order')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_wallet_balance(request):
    """Get wallet balance from Payuee."""
    try:
        client = PayueeClient()
        result = client.get_wallet_balance()
        
        if result['success']:
            # Per docs: GET /v1/wallet/balance returns
            # {"status": "success", "wallet_balance": <int, smallest unit>, "currency": "NGN"}
            # wallet_balance is in the smallest currency unit (kobo for NGN) - convert for display.
            raw_balance = result['data'].get('wallet_balance', 0)
            return Response({
                'success': True,
                'balance': raw_balance / 100,
                'currency': result['data'].get('currency', 'NGN'),
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to fetch balance')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_balance(request):
    """Get Payuee wallet balance (admin only)."""
    try:
        client = PayueeClient()
        result = client.get_wallet_balance()
        
        if result['success']:
            raw_balance = result['data'].get('wallet_balance', 0)
            return Response({
                'success': True,
                'balance': raw_balance / 100,
                'currency': result['data'].get('currency', 'NGN'),
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to fetch balance')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_shipping_fees(request):
    """POST /api/payments/shipping-fees/

    Thin proxy to Payuee's shipping-fees endpoint so the checkout page can
    show a live shipping quote before the order is actually placed. This
    was previously called by the frontend but never existed on the
    backend at all - every shipping calculation 404'd.

    Body: { vendors: [int], state, city, latitude, longitude, cart_items }
    """
    vendors = request.data.get('vendors')
    state = request.data.get('state')
    city = request.data.get('city')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    cart_items = request.data.get('cart_items')

    if not vendors or not state or not city or latitude is None or longitude is None or not cart_items:
        return Response(
            {'success': False, 'error': 'vendors, state, city, latitude, longitude and cart_items are all required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        client = PayueeClient()
        result = client.calculate_shipping_fees(
            vendors=vendors,
            state=state,
            city=city,
            latitude=float(latitude),
            longitude=float(longitude),
            cart_items=cart_items,
        )
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    if not result.get('success'):
        return Response(
            {'success': False, 'error': result.get('error', 'Shipping calculation failed')},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'success': True,
        'shipping': result.get('data', {}).get('shipping', []),
    })


# Admin views
class AdminTransactionListView(generics.ListAPIView):
    """Admin: List all transactions."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    queryset = Transaction.objects.all().select_related('user', 'order')


class AdminTransactionDetailView(generics.RetrieveAPIView):
    """Admin: Get transaction details."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.all().select_related('user', 'order')
    lookup_field = 'id'


# ------------------------------------------------------------------
# Product views (previously missing!)
# ------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def list_store_products(request):
    """
    POST /api/payments/products/

    Thin proxy to Payuee's store products. Supports pagination and filters.
    Body keys: category, page_number, sort_option, min_price, max_price,
               min_weight, max_weight, user_lat, user_lon, max_distance, tags
    """
    client = PayueeClient()
    result = client.get_store_products(
        category=request.data.get('category', 'all'),
        page_number=int(request.data.get('page_number', 1)),
        sort_option=int(request.data.get('sort_option', 8)),
        min_price=request.data.get('min_price'),
        max_price=request.data.get('max_price'),
        min_weight=request.data.get('min_weight'),
        max_weight=request.data.get('max_weight'),
        user_lat=request.data.get('user_lat'),
        user_lon=request.data.get('user_lon'),
        max_distance=int(request.data.get('max_distance', 100)),
        tags=request.data.get('tags'),
    )

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        return Response(
            {'success': False, 'error': result.get('error', 'Product fetch failed')},
            status=status_code if status_code >= 400 else 400
        )

    return Response({
        'success': True,
        'data': result.get('data', {}),
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def search_store_products(request):
    """
    POST /api/payments/products/search/

    Thin proxy to Payuee product search.
    """
    client = PayueeClient()
    result = client.search_products(
        search_term=request.data.get('search_term', ''),
        limit=int(request.data.get('limit', 20)),
        category=request.data.get('category', 'all'),
        page_number=int(request.data.get('page_number', 1)),
        sort_option=int(request.data.get('sort_option', 8)),
        min_price=request.data.get('min_price'),
        max_price=request.data.get('max_price'),
        min_weight=request.data.get('min_weight'),
        max_weight=request.data.get('max_weight'),
        tags=request.data.get('tags'),
    )

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        return Response(
            {'success': False, 'error': result.get('error', 'Search failed')},
            status=status_code if status_code >= 400 else 400
        )

    return Response({
        'success': True,
        'data': result.get('data', {}),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def product_detail(request, product_id):
    """
    GET /api/payments/products/<product_id>/
    """
    client = PayueeClient()
    result = client.get_product(product_id)

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        return Response(
            {'success': False, 'error': result.get('error', 'Product not found')},
            status=status_code if status_code >= 400 else 400
        )

    return Response({
        'success': True,
        'data': result.get('data', {}),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payuee_states(request):
    """GET /api/payments/location/states/"""
    client = PayueeClient()
    result = client.get_states()

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        return Response(
            {'success': False, 'error': result.get('error', 'Failed to fetch states')},
            status=status_code if status_code >= 400 else 400
        )

    return Response({
        'success': True,
        'data': result.get('data', {}),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payuee_cities(request):
    """GET /api/payments/location/cities/?state=Lagos"""
    state = request.query_params.get('state')
    if not state:
        return Response(
            {'success': False, 'error': 'state query parameter is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    client = PayueeClient()
    result = client.get_cities(state)

    if not result.get('success'):
        status_code = result.get('status_code', 400)
        return Response(
            {'success': False, 'error': result.get('error', 'Failed to fetch cities')},
            status=status_code if status_code >= 400 else 400
        )

    return Response({
        'success': True,
        'data': result.get('data', {}),
    })