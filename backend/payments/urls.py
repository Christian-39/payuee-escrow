"""
URL configuration for the payments app.
"""

from django.urls import path
from .views import (
    WalletView,
    WalletTransactionListView,
    TransactionListView,
    get_wallet_balance,
    get_payuee_wallet_balance,
    calculate_shipping_fees,
    AdminTransactionListView,
    AdminTransactionDetailView
)

urlpatterns = [
    # Wallet
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', WalletTransactionListView.as_view(), name='wallet_transactions'),
    path('wallet/balance/', get_wallet_balance, name='wallet_balance'),

    # Shipping (proxies Payuee - keeps the secret key server-side)
    path('shipping-fees/', calculate_shipping_fees, name='shipping_fees'),

    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transactions'),
    
    # Admin
    path('admin/wallet/balance/', get_payuee_wallet_balance, name='admin_payuee_balance'),
    path('admin/transactions/', AdminTransactionListView.as_view(), name='admin_transactions'),
    path('admin/transactions/<uuid:id>/', AdminTransactionDetailView.as_view(), name='admin_transaction_detail'),
]
