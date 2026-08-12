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
