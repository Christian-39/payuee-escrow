"""
URL configuration for payments app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # User wallet endpoints
    path('wallet/balance/', views.get_wallet_balance, name='wallet-balance'),
    path('wallet/funding-details/', views.get_wallet_funding_details, name='wallet-funding-details'),
    path('wallet-transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),

    # Admin wallet endpoints
    path('admin/wallet/balance/', views.get_payuee_wallet_balance, name='admin-wallet-balance'),
    path('admin/wallet/funding-details/', views.get_payuee_wallet_funding_details, name='admin-wallet-funding-details'),
    path('admin/wallet-transactions/', views.WalletTransactionListView.as_view(), name='admin-wallet-transactions'),
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin-transactions'),
    path('admin/transactions/<int:id>/', views.AdminTransactionDetailView.as_view(), name='admin-transaction-detail'),

    # Debug
    path('products-list/', views.products_list, name='products-list'),
]