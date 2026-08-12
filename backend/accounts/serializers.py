"""
Serializers for the accounts app.
Handles user registration, login, and profile management.
"""

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
    has_payuee_pin = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone_number', 'profile_image', 'address', 'city', 'state',
            'country', 'postal_code', 'dark_mode', 'email_notifications',
            'push_notifications', 'marketing_emails', 'is_admin', 'is_vendor',
            'email_verified', 'has_complete_profile', 'has_payuee_pin',
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
            'marketing_emails'
        ]


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


class SetPayueePinSerializer(serializers.Serializer):
    """Serializer for setting/updating the Payuee escrow transaction PIN.
    Field name matches what the frontend (PayueePinModal) already posts.
    """
    payuee_transaction_pin = serializers.CharField(write_only=True, min_length=6, max_length=6)

    WEAK_PINS = {
        '000000', '111111', '222222', '333333', '444444',
        '555555', '666666', '777777', '888888', '999999',
        '123456', '654321', '121212', '112233', '123123',
    }

    def validate_payuee_transaction_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only numbers.')
        if value in self.WEAK_PINS:
            raise serializers.ValidationError('Please choose a more secure PIN (avoid simple patterns).')
        return value
