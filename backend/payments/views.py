"""
Views for the payments app.
Handles wallet, location, logistics, and transaction management.
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
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─────────────────────────────────────────────────────────────
# WALLET VIEWS
# ─────────────────────────────────────────────────────────────

class WalletView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        wallet, created = Wallet.objects.get_or_create(
            user=self.request.user,
            defaults={'currency': 'NGN'}
        )
        return wallet


class WalletTransactionListView(generics.ListAPIView):
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
        client = PayueeClient()
        result = client.get_wallet_balance()

        if result.get('success'):
            data = result.get('data', {})
            return Response({
                'success': True,
                'wallet_balance': data.get('wallet_balance', 0),
                'currency': data.get('currency', 'NGN'),
            })
        else:
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
    try:
        client = PayueeClient()
        result = client.get_wallet_funding_details()

        if result.get('success'):
            data = result.get('data', {})
            funding_account = data.get('wallet_funding_account')

            if not funding_account:
                return Response(
                    {
                        'success': False,
                        'error': 'No funding account configured for this wallet.',
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response({
                'success': True,
                'wallet_funding_account': funding_account,
                'wallet_balance': data.get('wallet_balance', 0),
            })
        else:
            error_msg = result.get('error', 'Failed to fetch funding details')
            status_code = result.get('status_code', 400)

            if status_code == 405:
                return Response(
                    {
                        'success': False,
                        'error': 'Wallet funding not available. Contact Payuee support.',
                        'detail': error_msg,
                        'status_code': 405
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            return Response(
                {'success': False, 'error': error_msg, 'status_code': status_code},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.exception("Error fetching funding details")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────────
# LOCATION VIEWS
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payuee_states(request):
    """Get all available states from Payuee."""
    try:
        client = PayueeClient()
        result = client.get_states()

        if result.get('success'):
            data = result.get('data', {})
            return Response({
                'success': True,
                'states': data.get('states', []),
            })
        else:
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch states'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.exception("Error fetching states")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payuee_cities(request):
    """Get cities/wards for a specific state."""
    state = request.query_params.get('state')

    if not state:
        return Response(
            {'success': False, 'error': 'State parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        client = PayueeClient()
        result = client.get_cities(state)

        if result.get('success'):
            data = result.get('data', {})
            return Response({
                'success': True,
                'state': state,
                'cities': data.get('lga', []),
            })
        else:
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to fetch cities'),
                    'status_code': result.get('status_code', 400)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.exception(f"Error fetching cities for state={state}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────────
# LOGISTICS VIEWS
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_shipping(request):
    """Calculate shipping fees for cart items."""
    try:
        client = PayueeClient()
        result = client.get_shipping_fees(**request.data)

        if result.get('success'):
            return Response({
                'success': True,
                'shipping': result.get('data', {}).get('shipping', []),
                'cart': result.get('data', {}).get('cart', []),
            })
        else:
            return Response(
                {'success': False, 'error': result.get('error', 'Failed to calculate shipping')},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.exception("Error calculating shipping")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────────
# ORDER VIEWS (Payuee Escrow)
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payuee_order(request):
    """Create an order through Payuee escrow."""
    try:
        client = PayueeClient()
        result = client.create_order(**request.data)

        if result.get('success'):
            return Response({
                'success': True,
                'order_ids': result.get('data', {}).get('order_ids', []),
                'message': result.get('data', {}).get('message', 'Order created'),
                'status': result.get('data', {}).get('status'),
            })
        else:
            status_code = result.get('status_code', 400)
            http_status = status.HTTP_402 if status_code == 402 else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    'success': False,
                    'error': result.get('error', 'Failed to create order'),
                    'status_code': status_code,
                },
                status=http_status
            )
    except Exception as e:
        logger.exception("Error creating Payuee order")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payuee_order(request, order_id):
    """Get Payuee order details."""
    try:
        client = PayueeClient()
        result = client.get_order(int(order_id))

        if result.get('success'):
            return Response({
                'success': True,
                'order': result.get('data', {}),
            })
        else:
            return Response(
                {'success': False, 'error': result.get('error', 'Order not found')},
                status=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        logger.exception(f"Error fetching order {order_id}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payuee_orders(request):
    """List paginated Payuee orders."""
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 15))

    try:
        client = PayueeClient()
        result = client.list_orders(page=page, limit=limit)

        if result.get('success'):
            return Response({
                'success': True,
                'orders': result.get('data', {}).get('data', []),
                'pagination': result.get('data', {}).get('pagination', {}),
            })
        else:
            return Response(
                {'success': False, 'error': result.get('error', 'Failed to list orders')},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        logger.exception("Error listing orders")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_balance(request):
    """Get Payuee wallet balance (admin only)."""
    return get_wallet_balance(request._request)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_payuee_wallet_funding_details(request):
    """Get Payuee wallet funding details (admin only)."""
    return get_wallet_funding_details(request._request)


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


# ─────────────────────────────────────────────────────────────
# PRODUCTS (Passthrough)
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_list(request):
    client = get_payuee_client()
    result = client.get_store_products(**request.data)
    return Response(result)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_search(request):
    client = get_payuee_client()
    result = client.search_products(**request.data)
    return Response(result)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def product_detail(request, product_id):
    client = get_payuee_client()
    result = client.get_product(int(product_id))
    return Response(result)