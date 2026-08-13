from django.urls import path
from .views import (
    WalletView,
    WalletTransactionListView,
    TransactionListView,
    get_wallet_balance,
    get_payuee_wallet_balance,
    AdminTransactionListView,
    AdminTransactionDetailView,
    PayueeLocationStatesView,
    PayueeLocationCitiesView,
    PayueeWalletFundingView,
    PayueeAuthStatusView,
)

urlpatterns = [
    # Wallet
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', WalletTransactionListView.as_view(), name='wallet_transactions'),
    path('wallet/balance/', get_wallet_balance, name='wallet_balance'),
    path('wallet/fund/', PayueeWalletFundingView.as_view(), name='payuee_wallet_fund'),

    # Location (Payuee proxy)
    path('location/states/', PayueeLocationStatesView.as_view(), name='payuee-location-states'),
    path('location/cities/', PayueeLocationCitiesView.as_view(), name='payuee-location-cities'),
    
    # Payuee health check
    path('auth-status/', PayueeAuthStatusView.as_view(), name='payuee-auth-status'),
    
    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transactions'),
    
    # Admin
    path('admin/wallet/balance/', get_payuee_wallet_balance, name='admin_payuee_balance'),
    path('admin/transactions/', AdminTransactionListView.as_view(), name='admin_transactions'),
    path('admin/transactions/<uuid:id>/', AdminTransactionDetailView.as_view(), name='admin_transaction_detail'),
]