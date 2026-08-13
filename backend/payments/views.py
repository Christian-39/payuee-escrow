import logging
from rest_framework.views import APIView
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
from .payuee_client import get_payuee_client

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class WalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(
            user=self.request.user,
            defaults={'currency': 'USD'}
        )
        return wallet


class WalletTransactionListView(generics.ListAPIView):
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
    try:
        client = get_payuee_client()
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
        logger.exception("Payuee wallet balance error")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_balance(request):
    try:
        client = get_payuee_client()
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
        logger.exception("Admin Payuee wallet balance error")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Admin views
class AdminTransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    queryset = Transaction.objects.all().select_related('user', 'order')


class AdminTransactionDetailView(generics.RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.all().select_related('user', 'order')
    lookup_field = 'id'


# ------------------------------------------------------------------
# Payuee Location Proxy Views
# ------------------------------------------------------------------

class PayueeLocationStatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client = get_payuee_client()
        result = client.get_states()
        logger.debug(f"Payuee states response: {result}")

        if result.get('success'):
            data = result.get('data') or []
            return Response(data, status=status.HTTP_200_OK)

        logger.error(f"Payuee states failed: {result}")
        return Response(
            {'error': result.get('error', 'Failed to fetch states')},
            status=result.get('status_code', status.HTTP_502_BAD_GATEWAY)
        )


class PayueeLocationCitiesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        state = request.query_params.get('state')
        if not state:
            return Response(
                {'error': 'state query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = get_payuee_client()
        result = client.get_cities(state)
        logger.debug(f"Payuee cities response for state={state}: {result}")

        if result.get('success'):
            # Defensive: never return None to the frontend
            data = result.get('data') or []
            return Response(data, status=status.HTTP_200_OK)

        logger.error(f"Payuee cities failed: {result}")
        return Response(
            {'error': result.get('error', 'Failed to fetch cities')},
            status=result.get('status_code', status.HTTP_502_BAD_GATEWAY)
        )


# ------------------------------------------------------------------
# Missing Payuee Proxy Views
# ------------------------------------------------------------------

class PayueeWalletFundingView(APIView):
    """Proxy: GET /v1/wallet/fund"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client = get_payuee_client()
        result = client.get_wallet_funding_details()
        logger.debug(f"Payuee wallet fund response: {result}")

        if result.get('success'):
            data = result.get('data') or {}
            return Response(data, status=status.HTTP_200_OK)

        logger.error(f"Payuee wallet fund failed: {result}")
        return Response(
            {'error': result.get('error', 'Failed to fetch funding details')},
            status=result.get('status_code', status.HTTP_502_BAD_GATEWAY)
        )


class PayueeAuthStatusView(APIView):
    """Proxy: GET /v1/auth-status — quick credential health check."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client = get_payuee_client()
        result = client.test_auth()
        logger.debug(f"Payuee auth-status response: {result}")

        if result.get('success'):
            data = result.get('data') or {}
            return Response(data, status=status.HTTP_200_OK)

        logger.error(f"Payuee auth-status failed: {result}")
        return Response(
            {'error': result.get('error', 'Failed to check Payuee auth status')},
            status=result.get('status_code', status.HTTP_502_BAD_GATEWAY)
        )