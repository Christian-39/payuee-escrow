"""
Views for the payments app.
Handles wallet, location, logistics, and transaction management.
"""

import logging
import uuid

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
            # Payuee returns balance in kobo (smallest unit) — convert to NGN
            raw_balance = data.get('wallet_balance', 0)
            balance_ngn = raw_balance / 100.0
            return Response({
                'success': True,
                'wallet_balance_kobo': raw_balance,
                'wallet_balance': balance_ngn,
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

            # Also convert wallet balance to NGN
            raw_balance = data.get('wallet_balance', 0)
            return Response({
                'success': True,
                'wallet_funding_account': funding_account,
                'wallet_balance_kobo': raw_balance,
                'wallet_balance': raw_balance / 100.0,
            })
        else:
            error_msg = result.get('error', 'Failed to fetch funding details')
            status_code = result.get('status_code', 400)
            
            logger.error(f"Payuee funding details error: {status_code} - {error_msg}")

            # Return the actual status code from Payuee, not always 503
            if status_code == 401:
                http_status = status.HTTP_401_UNAUTHORIZED
            elif status_code == 404:
                http_status = status.HTTP_404_NOT_FOUND
            elif status_code == 405:
                http_status = status.HTTP_405_METHOD_NOT_ALLOWED
            else:
                http_status = status.HTTP_400_BAD_REQUEST

            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'status_code': status_code,
                },
                status=http_status
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
    """
    Create an order through Payuee escrow.
    
    Expected request body:
    {
        "trans_code": "123456",
        "webhook_response_url": "https://yourdomain.com/webhooks/payuee/",
        "customer": {...},
        "cart_items": [
            {"product_id": 12, "cart_meta": {"quantity": 2, "outfit_size": "M"}}
        ],
        "shipping": [
            {"vendor_id": 5, "fee": 2500, "method_id": "distance_based", "config_id": 2, "company_name": "DHL"}
        ]
    }
    """
    data = request.data
    
    # ── Validate required top-level fields ──
    required_top = ['trans_code', 'customer', 'cart_items', 'shipping']
    missing = [f for f in required_top if f not in data]
    if missing:
        return Response(
            {'success': False, 'error': f'Missing required fields: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # ── Validate customer fields ──
    customer = data['customer']
    cust_required = [
        'email', 'first_name', 'last_name', 'phone_number',
        'state', 'city', 'address_1', 'latitude', 'longitude'
    ]
    cust_missing = [f for f in cust_required if f not in customer]
    if cust_missing:
        return Response(
            {'success': False, 'error': f'Missing customer fields: {", ".join(cust_missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ── Validate cart_items ──
    cart_items = data['cart_items']
    if not cart_items or not isinstance(cart_items, list):
        return Response(
            {'success': False, 'error': 'cart_items must be a non-empty list'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    for i, item in enumerate(cart_items):
        if 'product_id' not in item:
            return Response(
                {'success': False, 'error': f'cart_items[{i}] missing product_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # BUG FIX #1: Ensure cart_meta exists with quantity inside it
        if 'cart_meta' not in item:
            item['cart_meta'] = {}
        if 'quantity' not in item['cart_meta']:
            item['cart_meta']['quantity'] = item.get('quantity', 1)

    # ── Validate shipping ──
    shipping = data['shipping']
    if not shipping or not isinstance(shipping, list):
        return Response(
            {'success': False, 'error': 'shipping must be a non-empty list'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    ship_required = ['vendor_id', 'fee', 'method_id', 'config_id', 'company_name']
    for i, s in enumerate(shipping):
        s_missing = [f for f in ship_required if f not in s]
        if s_missing:
            return Response(
                {'success': False, 'error': f'shipping[{i}] missing fields: {", ".join(s_missing)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ── Generate idempotency key ──
    idempotency_key = data.get('idempotency_key') or f"order-{request.user.id}-{uuid.uuid4().hex[:12]}"

    # ── Resolve webhook URL (BUG FIX #5) ──
    webhook_url = data.get('webhook_response_url')
    if not webhook_url:
        webhook_url = getattr(settings, 'PAYUEE_WEBHOOK_URL', None)
    if not webhook_url:
        logger.error("PAYUEE_WEBHOOK_URL not configured in settings")
        return Response(
            {'success': False, 'error': 'webhook_response_url is required. Set PAYUEE_WEBHOOK_URL in settings or pass it in the request.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ── DEBUG: Log the exact payload we will send (BUG FIX #4) ──
    import json
    debug_payload = {
        "trans_code": data['trans_code'],
        "webhook_response_url": webhook_url,
        "customer": customer,
        "cart_items": cart_items,
        "shipping": shipping,
    }
    logger.info(f"PAYUEE ORDER PAYLOAD: {json.dumps(debug_payload, indent=2)}")

    # ── Call Payuee ──
    try:
        client = PayueeClient()
        result = client.create_order(
            trans_code=data['trans_code'],
            webhook_response_url=webhook_url,
            customer=customer,
            cart_items=cart_items,
            shipping=shipping,
            idempotency_key=idempotency_key
        )

        logger.info(f"PAYUEE ORDER RESPONSE: {result}")

        if result.get('success'):
            response_data = result.get('data', {})
            
            # Handle ON_HOLD (insufficient wallet)
            if response_data.get('status') == 'ON_HOLD':
                return Response({
                    'success': True,
                    'status': 'ON_HOLD',
                    'order_ids': response_data.get('order_ids', []),
                    'message': response_data.get('message', 'Please fund your wallet to process this order'),
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # Normal success
            return Response({
                'success': True,
                'order_ids': response_data.get('order_ids', []),
                'message': response_data.get('message', 'Order created successfully'),
                'status': response_data.get('status'),
            }, status=status.HTTP_201_CREATED)
        else:
            # Payuee returned an error
            status_code = result.get('status_code', 400)
            error_msg = result.get('error', 'Failed to create order')
            
            logger.error(f"PAYUEE ORDER ERROR: {status_code} - {error_msg}")
            
            http_status = status.HTTP_400_BAD_REQUEST
            if status_code == 402:
                http_status = status.HTTP_402_PAYMENT_REQUIRED
            elif status_code == 401:
                http_status = status.HTTP_401_UNAUTHORIZED
            elif status_code == 404:
                http_status = status.HTTP_404_NOT_FOUND
            
            return Response(
                {
                    'success': False,
                    'error': error_msg,
                    'status_code': status_code,
                },
                status=http_status
            )
            
    except ValueError as e:
        logger.warning(f"Validation error creating order: {e}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception("Unexpected error creating Payuee order")
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
    result = client.search_products(**request.data)
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