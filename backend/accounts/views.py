"""
Views for the accounts app.
Handles user authentication, registration, and profile management.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
    UserPreferencesSerializer,
    CustomTokenObtainPairSerializer,
    SetPayueePinSerializer
)
from .authentication import CSRF_COOKIE_NAME, generate_csrf_token

User = get_user_model()

ACCESS_COOKIE = settings.SIMPLE_JWT.get('AUTH_COOKIE_ACCESS', 'access_token')
REFRESH_COOKIE = settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')


def _cookie_kwargs(max_age, http_only):
    """Shared cookie flags. SameSite=None (needed for the cross-origin
    frontend<->API setup - see accounts/authentication.py docstring) only
    works if Secure is also set, which is why AUTH_COOKIE_SECURE defaults
    to True outside DEBUG."""
    kwargs = {
        'max_age': max_age,
        'httponly': http_only,
        'secure': settings.AUTH_COOKIE_SECURE,
        'samesite': settings.AUTH_COOKIE_SAMESITE,
        'path': '/',
    }
    if settings.AUTH_COOKIE_DOMAIN:
        kwargs['domain'] = settings.AUTH_COOKIE_DOMAIN
    return kwargs


def _set_auth_cookies(response, access, refresh=None):
    access_lifetime = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
    response.set_cookie(ACCESS_COOKIE, str(access), **_cookie_kwargs(access_lifetime, http_only=True))

    if refresh is not None:
        refresh_lifetime = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
        response.set_cookie(REFRESH_COOKIE, str(refresh), **_cookie_kwargs(refresh_lifetime, http_only=True))

    # Non-httpOnly on purpose: the frontend JS must be able to read this
    # one to echo it back in the X-CSRF-Token header (double-submit
    # pattern - see accounts/authentication.py).
    response.set_cookie(
        CSRF_COOKIE_NAME, generate_csrf_token(),
        **_cookie_kwargs(int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()), http_only=False)
    )
    return response


def _clear_auth_cookies(response):
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE_NAME):
        response.delete_cookie(name, path='/', domain=settings.AUTH_COOKIE_DOMAIN)
    return response


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login view. Tokens are set as httpOnly cookies rather than returned
    in the response body (see module docstring / accounts/authentication.py)."""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.pop('access', None)
            refresh = response.data.pop('refresh', None)
            _set_auth_cookies(response, access, refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh view that reads the refresh token from the httpOnly cookie
    instead of requiring it in the request body, and writes the rotated
    tokens back as cookies."""

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_token:
            return Response({'detail': 'No refresh token cookie.'}, status=status.HTTP_401_UNAUTHORIZED)

        request.data['refresh'] = refresh_token
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.pop('access', None)
            # ROTATE_REFRESH_TOKENS=True means a new refresh token comes
            # back too; without re-setting the cookie here, the client
            # would keep sending the now-blacklisted original refresh
            # token on every subsequent refresh and get logged out.
            new_refresh = response.data.pop('refresh', None)
            _set_auth_cookies(response, access, new_refresh)
        return response


class LogoutView(APIView):
    """Blacklists the current refresh token (now that
    rest_framework_simplejwt.token_blacklist is installed - see
    settings.py) and clears all auth cookies."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass  # already invalid/expired - nothing to blacklist

        response = Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        return _clear_auth_cookies(response)


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

    # ✅ Save PATH (not URL)
    request.user.profile_image = path
    request.user.save()

    return Response({
        'message': 'Uploaded successfully',
        'profile_image': request.user.profile_image.url
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def set_payuee_pin(request):
    """Set or update the user's Payuee escrow transaction PIN. The PIN is
    hashed server-side (see User.set_payuee_pin) and never stored or
    returned in plaintext."""
    serializer = SetPayueePinSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    request.user.set_payuee_pin(serializer.validated_data['payuee_transaction_pin'])
    request.user.save(update_fields=['payuee_transaction_pin_hash'])

    return Response({'message': 'Payuee PIN set successfully.', 'has_payuee_pin': True})


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
