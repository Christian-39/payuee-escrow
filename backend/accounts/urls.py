"""
URL configuration for the accounts app.
"""

from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    UserRegistrationView,
    UserProfileView,
    UserProfileUpdateView,
    ChangePasswordView,
    UserPreferencesView,
    upload_profile_image,
    set_payuee_pin,
    user_stats
)

urlpatterns = [
    # Authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    
    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile_update'),
    path('profile/image/', upload_profile_image, name='upload_profile_image'),
    path('profile/stats/', user_stats, name='user_stats'),
    
    # Password
    path('password/change/', ChangePasswordView.as_view(), name='change_password'),

    # Payuee escrow transaction PIN
    path('set-payuee-pin/', set_payuee_pin, name='set_payuee_pin'),
    
    # Preferences
    path('preferences/', UserPreferencesView.as_view(), name='preferences'),
]
