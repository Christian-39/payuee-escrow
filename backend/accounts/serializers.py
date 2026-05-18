"""
Serializers for the accounts app.
Handles user registration, login, and profile management.
"""

import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user data."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to response
        data['user'] = UserSerializer(self.user).data
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    
    full_name = serializers.CharField(read_only=True)
    has_complete_profile = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone_number', 'profile_image', 'address', 'city', 'state',
            'country', 'postal_code', 'dark_mode', 'email_notifications',
            'push_notifications', 'marketing_emails', 'is_admin', 'is_vendor',
            'email_verified', 'has_complete_profile', 'payuee_transaction_pin',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email_verified', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 
            'password', 'password_confirm', 'phone_number'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_image',
            'address', 'city', 'state', 'country', 'postal_code',
            'dark_mode', 'email_notifications', 'push_notifications',
            'marketing_emails', 'payuee_transaction_pin'
        ]
    
    def validate_payuee_transaction_pin(self, value):
        """Validate Payuee transaction PIN format."""
        if value is None or value == '':
            return value
        
        pin_str = str(value).strip()
        
        # Must be exactly 6 digits
        if not re.match(r'^\d{6}$', pin_str):
            raise serializers.ValidationError(
                'Payuee transaction PIN must be exactly 6 digits.'
            )
        
        # Block weak/common PINs
        weak_pins = {'000000', '111111', '222222', '333333', '444444',
                     '555555', '666666', '777777', '888888', '999999', '123456'}
        if pin_str in weak_pins:
            raise serializers.ValidationError(
                'Please choose a more secure PIN (avoid sequential or repeated digits).'
            )
        
        return pin_str


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password": "Password fields didn't match."}
            )
        return attrs


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences."""
    
    class Meta:
        model = User
        fields = [
            'dark_mode', 'email_notifications', 
            'push_notifications', 'marketing_emails'
        ]


class PayueePinSerializer(serializers.Serializer):
    """Standalone serializer for setting/updating Payuee transaction PIN."""
    
    payuee_transaction_pin = serializers.CharField(
        required=True,
        min_length=6,
        max_length=6,
        help_text='6-digit Payuee transaction PIN for escrow order authorization'
    )
    
    def validate_payuee_transaction_pin(self, value):
        pin_str = str(value).strip()
        
        # Must be exactly 6 digits
        if not re.match(r'^\d{6}$', pin_str):
            raise serializers.ValidationError(
                'PIN must be exactly 6 digits (numbers only).'
            )
        
        # Block weak/common PINs
        weak_pins = {'000000', '111111', '222222', '333333', '444444',
                     '555555', '666666', '777777', '888888', '999999', '123456'}
        if pin_str in weak_pins:
            raise serializers.ValidationError(
                'Please choose a more secure PIN (avoid sequential or repeated digits).'
            )
        
        return pin_str