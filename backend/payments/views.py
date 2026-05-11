"""
Views for the payments app.
Handles wallet and transaction management.
"""

import logging

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
from .payuee_client import PayueeClient, get_payuee_client

logger = logging.getLogger(__name__)


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
            defaults={'currency': 'NGN'}
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
            defaults={'currency': 'NGN'}
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
    """
    Get wallet balance from Payuee.

    Returns:
        {
            "success": true,
            "wallet_balance": 250000,
            "currency": "NGN"
        }
    """
    try:
        client = PayueeClient()
        result = client.get_wallet_balance()

        logger.info(f"Payuee wallet balance raw response: {result}")

        if result.get('success'):
            data = result.get('data', {})
            # Payuee returns: {"status": "success", "wallet_balance": 250000, "currency": "NGN"}
            return Response({
                'success': True,
                'wallet_balance': data.get('wallet_balance', 0),
                'currency': data.get('currency', 'NGN'),
            })
        else:
            logger.error(f"Payuee balance error: {result}")
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch balance'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.exception("Error fetching wallet balance")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_wallet_funding_details(request):
    """
    Get Payuee wallet funding details (virtual account for bank transfer).

    Returns:
        {
            "success": true,
            "wallet_funding_account": {
                "account_name": "PAYUEE NETWORK LIMITED",
                "account_number": "1385097053",
                "bank_name": "Paga Bank",
                "bank_code": "100002"
            },
            "wallet_balance": 250000
        }
    """
    try:
        client = PayueeClient()
        result = client.get_wallet_funding_details()

        logger.info(f"Payuee funding details raw response: {result}")

        if result.get('success'):
            data = result.get('data', {})
            funding_account = data.get('wallet_funding_account')

            if not funding_account:
                logger.warning("Payuee returned success but wallet_funding_account is missing/None")
                return Response(
                    {
                        'success': False,
                        'error': 'No funding account configured for this wallet. Contact Payuee support.',
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                'success': True,
                'wallet_funding_account': funding_account,
                'wallet_balance': data.get('wallet_balance', 0),
            })
        else:
            logger.error(f"Payuee funding details error: {result}")
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch funding details'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.exception("Error fetching funding details")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_balance(request):
    """Get Payuee wallet balance (admin only)."""
    try:
        client = PayueeClient()
        result = client.get_wallet_balance()

        logger.info(f"Admin wallet balance raw response: {result}")

        if result.get('success'):
            data = result.get('data', {})
            return Response({
                'success': True,
                'wallet_balance': data.get('wallet_balance', 0),
                'currency': data.get('currency', 'NGN'),
            })
        else:
            logger.error(f"Admin balance error: {result}")
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch balance'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.exception("Admin error fetching balance")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_funding_details(request):
    """Get Payuee wallet funding details (admin only)."""
    try:
        client = PayueeClient()
        result = client.get_wallet_funding_details()

        logger.info(f"Admin funding details raw response: {result}")

        if result.get('success'):
            data = result.get('data', {})
            funding_account = data.get('wallet_funding_account')

            if not funding_account:
                return Response(
                    {
                        'success': False,
                        'error': 'No funding account configured. Contact Payuee support.',
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                'success': True,
                'wallet_funding_account': funding_account,
                'wallet_balance': data.get('wallet_balance', 0),
            })
        else:
            logger.error(f"Admin funding details error: {result}")
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch funding details'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.exception("Admin error fetching funding details")
        return Response(
            {'success': False, 'error': str(e)},
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


@api_view(['GET'])
def products_list(request):
    client = get_payuee_client()
    result = client.get_store_products()

    logger.info(f"Payuee products result: {result}")

    return Response(result)