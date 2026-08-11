"""
Admin configuration for payments app.
"""

from django.contrib import admin
from .models import Transaction, Wallet, WalletTransaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Transaction admin."""
    
    list_display = [
        'transaction_id', 'transaction_type', 'amount',
        'currency', 'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'currency', 'created_at']
    search_fields = ['transaction_id', 'user__email', 'order__order_number']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']


class WalletTransactionInline(admin.TabularInline):
    """Wallet transaction inline."""
    model = WalletTransaction
    extra = 0
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Wallet admin."""
    
    list_display = [
        'user', 'balance', 'currency', 'is_active', 'is_verified', 'created_at'
    ]
    list_filter = ['currency', 'is_active', 'is_verified', 'created_at']
    search_fields = ['user__email']
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Wallet transaction admin."""
    
    list_display = [
        'wallet', 'transaction_type', 'amount', 'balance_after', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['wallet__user__email', 'description']
