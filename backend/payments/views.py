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
            return Response({
                'success': True,
                'balance': result['data'].get('balance', 0),
                'currency': result['data'].get('currency', 'USD'),
                'pending_balance': result['data'].get('pending_balance', 0)
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
            return Response({
                'success': True,
                'balance': result['data']
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
