
# ============================================================
# FILE 10: payments/serializers.py (FIXED - already correct, just verify)
# ============================================================
"""
Serializers for the payments app.
"""

from rest_framework import serializers
from .models import Transaction, Wallet, WalletTransaction


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions."""
    
    order_number = serializers.CharField(
        source='order.order_number',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'transaction_type', 'status',
            'order', 'order_number', 'user', 'user_email',
            'amount', 'currency', 'fee', 'net_amount',
            'payuee_transaction_id', 'description', 'metadata',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'user_email', 'balance', 'currency',
            'daily_limit', 'monthly_limit', 'is_active',
            'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for wallet transactions."""
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'balance_after',
            'description', 'reference_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WalletFundingSerializer(serializers.Serializer):
    """Serializer for wallet funding."""
    
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='USD')
    payment_method = serializers.ChoiceField(
        choices=[
            ('card', 'Credit/Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('crypto', 'Cryptocurrency')
        ]
    )


class PayoutSerializer(serializers.Serializer):
    """Serializer for payout requests."""
    
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='USD')
    bank_account = serializers.CharField()
    bank_name = serializers.CharField()
    account_name = serializers.CharField()
