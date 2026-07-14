# ============================================================
# FILE: payments/views.py (UPDATED - Compatible with new payuee_client)
# ============================================================
"""
Views for the payments app.
Handles wallet, location, logistics, and transaction management.
"""

import logging
import uuid
import re
import json

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
CACHE_TTL = 600  # 10 minutes cache


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

        if not result.get('success'):
            error_msg = result.get('error', 'Failed to fetch funding details')
            status_code = result.get('status_code', 400)
            logger.error(f"Payuee funding details error: {status_code} - {error_msg}")
            return Response({'success': False, 'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        data = result.get('data', {})
        funding_accounts = data.get('success', [])

        if not funding_accounts:
            return Response(
                {
                    'success': False,
                    'error': 'No funding account configured for this wallet.',
                },
                status=status.HTTP_404_NOT_FOUND
            )

        primary_account = funding_accounts[0]
        raw_balance = data.get('wallet_balance', 0)
        return Response({
            'success': True,
            'wallet_funding_account': {
                'id': primary_account.get('ID'),
                'account_number': primary_account.get('AccountNumber'),
                'account_name': primary_account.get('AccountName'),
                'account_reference': primary_account.get('AccountReference'),
                'bank_name': primary_account.get('BankName'),
                'bank_code': primary_account.get('BankCode'),
                'currency': primary_account.get('Currency', 'NGN'),
                'reference': primary_account.get('Reference'),
                'status': primary_account.get('Status'),
            },
            'wallet_balance_kobo': raw_balance,
            'wallet_balance': raw_balance / 100.0,
            'currency': data.get('currency', 'NGN'),
        })
    except Exception as e:
        logger.exception("Error in wallet funding details view")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ─────────────────────────────────────────────────────────────
# LOCATION VIEWS
# ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_payuee_states(request):
    try:
        client = get_payuee_client()
        result = client.get_states()
        return Response(result)
    except Exception as e:
        logger.exception("Error fetching states")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_payuee_cities(request):
    state = request.query_params.get('state', '')
    if not state:
        return Response({'success': False, 'error': 'State query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        client = get_payuee_client()
        result = client.get_cities(state)
        return Response(result)
    except Exception as e:
        logger.exception("Error fetching cities")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────
# LOGISTICS VIEWS
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_shipping(request):
    """
    Calculate shipping fees for cart items via Payuee logistics.
    Expected body:
    {
        "vendors": [...],
        "state": "Lagos",
        "city": "Ikeja",
        "latitude": 6.5244,
        "longitude": 3.3792,
        "cart_items": [...]
    }
    """
    data = request.data

    # Validate required fields
    required = ['vendors', 'state', 'city', 'latitude', 'longitude', 'cart_items']
    missing = [f for f in required if f not in data]
    if missing:
        return Response(
            {'success': False, 'error': f'Missing required fields: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate cart_items
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
        if 'cart_meta' not in item:
            item['cart_meta'] = {}
        if 'quantity' not in item['cart_meta']:
            item['cart_meta']['quantity'] = item.get('quantity', 1)

    # Validate vendors
    vendors = data['vendors']
    if not isinstance(vendors, list) or len(vendors) == 0:
        return Response(
            {'success': False, 'error': 'vendors must be a non-empty array'},
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(f"INCOMING SHIPPING REQUEST: {json.dumps(data, indent=2)}")

    try:
        client = get_payuee_client()
        # FIXED: Pass correct kwargs matching payuee_client.get_shipping_fees()
        result = client.get_shipping_fees(
            vendors=data['vendors'],
            state=data['state'],
            city=data['city'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            cart_items=data['cart_items']
        )

        logger.info(f"PAYUEE SHIPPING RESULT: {result}")

        if result.get('success'):
            payuee_data = result.get('data', {})
            return Response({
                'success': True,
                'shipping': payuee_data.get('shipping', []),
                'cart': payuee_data.get('cart', []),
            })
        else:
            return Response(
                {'success': False, 'error': result.get('error', 'Unknown error')},
                status=status.HTTP_400_BAD_REQUEST
            )

    except requests.Timeout:
        logger.error("Payuee API timeout")
        return Response(
            {'success': False, 'error': 'Shipping service timeout. Please try again.'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except Exception as e:
        logger.exception("Error in calculate shipping view")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────
# ORDER VIEWS (Payuee Escrow)
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payuee_order(request):
    """
    Create an order through Payuee escrow.
    Expected body:
    {
        "trans_code": "123456",
        "webhook_response_url": "https://yourdomain.com/webhooks/payuee/",
        "customer": {...},
        "cart_items": [...],
        "shipping": [...]
    }
    """
    data = request.data

    # Validate required top-level fields
    required_top = ['trans_code', 'customer', 'cart_items', 'shipping']
    missing = [f for f in required_top if f not in data]
    if missing:
        return Response(
            {'success': False, 'error': f'Missing required fields: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate trans_code format
    trans_code = str(data.get('trans_code', '')).strip()
    if not trans_code or not re.match(r'^\d{6}$', trans_code):
        return Response(
            {'success': False, 'error': 'trans_code must be exactly 6 digits (customer-created PIN)'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate customer fields
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

    # Validate cart_items
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
        if 'cart_meta' not in item:
            item['cart_meta'] = {}
        if 'quantity' not in item['cart_meta']:
            item['cart_meta']['quantity'] = item.get('quantity', 1)

    # Validate shipping
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

    # Generate idempotency key
    idempotency_key = data.get('idempotency_key') or f"order-{request.user.id}-{uuid.uuid4().hex[:12]}"

    # Resolve webhook URL
    from django.conf import settings
    webhook_url = data.get('webhook_response_url')
    if not webhook_url:
        webhook_url = getattr(settings, 'PAYUEE_WEBHOOK_URL', None)
    if not webhook_url:
        logger.error("PAYUEE_WEBHOOK_URL not configured in settings")
        return Response(
            {'success': False, 'error': 'webhook_response_url is required. Set PAYUEE_WEBHOOK_URL in settings or pass it in the request.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Debug log payload
    debug_payload = {
        "trans_code": trans_code,
        "webhook_response_url": webhook_url,
        "customer": customer,
        "cart_items": cart_items,
        "shipping": shipping,
    }
    logger.info(f"PAYUEE ORDER PAYLOAD: {json.dumps(debug_payload, indent=2)}")

    # FIXED: Call create_order with correct kwargs (not raw request.data)
    try:
        client = get_payuee_client()
        result = client.create_order(
            trans_code=trans_code,
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

            return Response({
                'success': True,
                'order_ids': response_data.get('order_ids', []),
                'message': response_data.get('message', 'Order created successfully'),
                'status': response_data.get('status'),
            }, status=status.HTTP_201_CREATED)
        else:
            status_code = result.get('status_code', 400)
            error_msg = result.get('error', 'Failed to create order')

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
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payuee_order(request, order_id):
    try:
        client = get_payuee_client()
        result = client.get_order(int(order_id))
        return Response(result)
    except Exception as e:
        logger.exception(f"Error fetching order {order_id}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payuee_orders(request):
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 15))
    try:
        client = get_payuee_client()
        result = client.list_orders(page=page, limit=limit)
        return Response(result)
    except Exception as e:
        logger.exception("Error listing orders")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

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
# PRODUCTS (Passthrough with Caching)
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_list(request):
    """
    List products from Payuee store.
    Uses get_store_products (not search_products) for browsing.
    """
    from django.core.cache import cache
    
    # Build cache key from request data
    cache_data = dict(request.data) if request.data else {}
    cache_data['endpoint'] = 'list'
    cache_str = json.dumps(cache_data, sort_keys=True)
    cache_key = f"payuee_passthrough_list_{hash(cache_str)}"
    
    result = cache.get(cache_key)
    if not result:
        client = get_payuee_client()
        # FIXED: Use get_store_products for listing, not search_products
        result = client.get_store_products(**request.data)
        cache.set(cache_key, result, CACHE_TTL)
    return Response(result)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_search(request):
    """
    Search products from Payuee store.
    Uses search_products for keyword/filter search.
    """
    from django.core.cache import cache
    
    cache_data = dict(request.data) if request.data else {}
    cache_data['endpoint'] = 'search'
    cache_str = json.dumps(cache_data, sort_keys=True)
    cache_key = f"payuee_passthrough_search_{hash(cache_str)}"
    
    result = cache.get(cache_key)
    if not result:
        client = get_payuee_client()
        result = client.search_products(**request.data)
        cache.set(cache_key, result, CACHE_TTL)
    return Response(result)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def product_detail(request, product_id):
    from django.core.cache import cache
    cache_key = f"payuee_passthrough_detail_{product_id}"
    
    result = cache.get(cache_key)
    if not result:
        client = get_payuee_client()
        result = client.get_product(int(product_id))
        cache.set(cache_key, result, CACHE_TTL)
    return Response(result)
