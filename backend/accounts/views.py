"""
Views for the accounts app.
Handles user authentication, registration, and profile management.
"""

import re
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.utils import timezone

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
    UserPreferencesSerializer,
    CustomTokenObtainPairSerializer,
    PayueePinSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view that returns user data with tokens."""
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """View for user registration."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Return user data
        return Response({
            'message': 'User registered successfully.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserProfileUpdateView(generics.UpdateAPIView):
    """View for updating user profile details."""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'message': 'Profile updated successfully.',
            'user': UserSerializer(instance).data
        })


class ChangePasswordView(generics.UpdateAPIView):
    """View for changing user password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Wrong password.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user preferences."""
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_profile_image(request):
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import uuid

    image = request.FILES.get('profile_image')

    if not image:
        return Response(
            {'error': 'No image provided.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if image.content_type not in allowed_types:
        return Response(
            {'error': 'Invalid file type.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate size
    if image.size > 5 * 1024 * 1024:
        return Response(
            {'error': 'File too large (max 5MB).'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate filename
    ext = image.name.split('.')[-1]
    filename = f"profiles/{request.user.id}/{uuid.uuid4()}.{ext}"

    # Save file
    path = default_storage.save(filename, ContentFile(image.read()))

    # Save PATH (not URL)
    request.user.profile_image = path
    request.user.save()

    return Response({
        'message': 'Uploaded successfully',
        'profile_image': request.user.profile_image.url
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get user statistics."""
    user = request.user
    
    # Import order model here to avoid circular imports
    from orders.models import Order
    
    stats = {
        'total_orders': Order.objects.filter(user=user).count(),
        'pending_orders': Order.objects.filter(user=user, status='pending').count(),
        'completed_orders': Order.objects.filter(user=user, status='delivered').count(),
        'wishlist_count': user.wishlist_items.count() if hasattr(user, 'wishlist_items') else 0,
        'member_since': user.created_at,
        'profile_complete': user.has_complete_profile
    }
    
    return Response(stats)


# ── NEW: Payuee Transaction PIN Endpoints ──

@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def profile(request):
    """
    Get or update user profile including Payuee transaction PIN.
    Used by CheckoutPage to fetch saved PIN.
    """
    user = request.user

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        # Handle Payuee PIN update with dedicated serializer
        pin = request.data.get('payuee_transaction_pin')
        if pin is not None:
            pin_serializer = PayueePinSerializer(data={'payuee_transaction_pin': pin})
            if not pin_serializer.is_valid():
                return Response(pin_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            user.payuee_transaction_pin = pin_serializer.validated_data['payuee_transaction_pin']
            user.save()
            
            return Response({
                'message': 'Payuee transaction PIN updated successfully.',
                'payuee_transaction_pin': user.payuee_transaction_pin
            })

        # Handle other profile fields
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_payuee_pin(request):
    """
    Dedicated endpoint for setting/updating Payuee transaction PIN.
    Called from profile security settings page.
    """
    serializer = PayueePinSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    pin = serializer.validated_data['payuee_transaction_pin']
    request.user.payuee_transaction_pin = pin
    request.user.save()
    
    return Response({
        'message': 'Payuee transaction PIN set successfully.',
        'payuee_transaction_pin': pin
    }, status=status.HTTP_200_OK)