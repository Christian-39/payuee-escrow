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

def _normalize_payuee_list_payload(raw, list_key):
    """
    Normalize a Payuee list-style response into the shape the frontend
    actually expects: {"success": true, "<list_key>": [...]}.

    Root cause of "cities dropdown never opens after selecting a state":
    Payuee's API (same as /v1/products - see
    payments/payuee_client.py::get_all_store_products, which already works
    around this) confusingly returns the payload array itself under a
    literal "success" key, e.g. {"success": [...states or cities...]},
    NOT a boolean success flag alongside a "states"/"cities" key. These two
    views were forwarding that raw shape straight through
    (`Response(data, ...)`), so on the frontend
    (usePayueeLocation.fetchCities) `response.data.success` happened to be
    a truthy non-empty array (so no error surfaced) but
    `response.data.cities` was always undefined - the cities list state
    was set to `[]` every time, so the dropdown opened with zero rows and
    looked like it "wasn't dropping down". States can appear to work if
    Payuee's states payload additionally happens to include a `states` key
    another way, but the two endpoints must not be assumed to differ -
    this normalizer future-proofs both against whichever exact shape
    Payuee actually returns.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in (list_key, 'lga', 'success', 'data', 'results'):
            value = raw.get(key)
            if isinstance(value, list):
                return value
    return []


class PayueeLocationStatesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client = get_payuee_client()
        result = client.get_states()
        logger.debug(f"Payuee states response: {result}")

        if result.get('success'):
            states = _normalize_payuee_list_payload(result.get('data'), 'states')
            return Response({'success': True, 'states': states}, status=status.HTTP_200_OK)

        logger.error(f"Payuee states failed: {result}")
        return Response(
            {'success': False, 'error': result.get('error', 'Failed to fetch states')},
            status=result.get('status_code', status.HTTP_502_BAD_GATEWAY)
        )


class PayueeLocationCitiesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        state = request.query_params.get('state')
        if not state:
            return Response(
                {'success': False, 'error': 'state query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = get_payuee_client()
        result = client.get_cities(state)
        logger.debug(f"Payuee cities response for state={state}: {result}")
        logger.info(f"PAYUEE CITIES RAW for state={state}: {result}")

        if result.get('success'):
            cities = _normalize_payuee_list_payload(result.get('data'), 'cities')
            return Response({'success': True, 'cities': cities}, status=status.HTTP_200_OK)

        logger.error(f"Payuee cities failed: {result}")
        return Response(
            {'success': False, 'error': result.get('error', 'Failed to fetch cities')},
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