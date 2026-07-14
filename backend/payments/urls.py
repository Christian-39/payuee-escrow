# ============================================================
# FILE: payments/urls.py (FIXED - Added missing URL aliases)
# ============================================================
"""
URL configuration for payments app.
"""

from django.urls import path
from . import views
from .webhooks import payuee_webhook

urlpatterns = [
    # Wallet
    path('wallet/', views.WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),
    # FIX: Added alias path to match frontend URL convention
    path('wallet-transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions-alt'),
    path('wallet/balance/', views.get_wallet_balance, name='wallet-balance'),
    path('wallet/fund/', views.get_wallet_funding_details, name='wallet-funding'),

    # Location
    path('location/states/', views.get_payuee_states, name='location-states'),
    path('location/cities/', views.get_payuee_cities, name='location-cities'),

    # Logistics
    path('shipping-fees/', views.calculate_shipping, name='shipping-fees'),

    # Orders (Payuee Escrow)
    path('orders/create/', views.create_payuee_order, name='create-payuee-order'),
    path('orders/<int:order_id>/', views.get_payuee_order, name='get-payuee-order'),
    path('orders/', views.list_payuee_orders, name='list-payuee-orders'),

    # Webhook
    path('webhook/payuee/', payuee_webhook, name='payuee-webhook'),

    # Admin
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin-transactions'),
    path('admin/transactions/<uuid:id>/', views.AdminTransactionDetailView.as_view(), name='admin-transaction-detail'),

    # Products (Passthrough)
    path('products/', views.products_list, name='payuee-products'),
    path('products/search/', views.products_search, name='payuee-products-search'),
    path('products/<int:product_id>/', views.product_detail, name='payuee-product-detail'),
]
