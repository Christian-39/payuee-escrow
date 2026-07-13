# ============================================================
# FILE 7: payments/views.py (UPDATED - Caching & Admin Views Added)
# ============================================================
"""
Views for the payments app.
Handles wallet, location, logistics, and transaction management.
"""

import logging
import uuid
import re
import requests

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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_shipping(request):
    data = request.data
    required = ['shipping', 'cart_items', 'vendors']
    missing = [f for f in required if f not in data]
    if missing:
        return Response(
            {'success': False, 'error': f'Missing fields: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

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

    vendors = data['vendors']
    if not isinstance(vendors, list) or len(vendors) == 0:
        return Response(
            {'success': False, 'error': 'vendors must be a non-empty array'},
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(f"INCOMING SHIPPING REQUEST: {data}")

    try:
        client = get_payuee_client()
        result = client.get_shipping_fees(
            vendors=data['vendors'],
            shipping=data['shipping'],
            cart_items=data['cart_items']
        )
        return Response(result)
    except Exception as e:
        logger.exception("Error in calculate shipping view")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payuee_order(request):
    try:
        client = get_payuee_client()
        result = client.create_order(request.data)
        return Response(result)
    except Exception as e:
        logger.exception("Unexpected error creating Payuee order")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_payuee_order(request, order_id):
    try:
        client = get_payuee_client()
        result = client.get_order(order_id)
        return Response(result)
    except Exception as e:
        logger.exception(f"Error fetching order {order_id}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_payuee_orders(request):
    try:
        client = get_payuee_client()
        result = client.list_orders()
        return Response(result)
    except Exception as e:
        logger.exception("Error listing orders")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
# ADMIN VIEWS
# ─────────────────────────────────────────────────────────────

class AdminTransactionListView(generics.ListAPIView):
    """Admin endpoint to monitor system transaction logs."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    queryset = Transaction.objects.all().select_related('user', 'order')


class AdminTransactionDetailView(generics.RetrieveAPIView):
    """Admin endpoint to inspect individual transaction profiles."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.all().select_related('user', 'order')
    lookup_field = 'id'


# ─────────────────────────────────────────────────────────────
# PRODUCTS (Passthrough with Caching Hooks)
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_list(request):
    from django.core.cache import cache
    cache_str = str(sorted(request.data.items())) if request.data else 'all'
    cache_key = f"payuee_passthrough_list_{hash(cache_str)}"
    
    result = cache.get(cache_key)
    if not result:
        client = get_payuee_client()
        result = client.search_products(**request.data)
        cache.set(cache_key, result, CACHE_TTL)
    return Response(result)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def products_search(request):
    from django.core.cache import cache
    cache_str = str(sorted(request.data.items())) if request.data else 'query'
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
