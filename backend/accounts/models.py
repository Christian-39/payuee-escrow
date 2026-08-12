"""
Custom User Model for GadgetHub
Extends Django's AbstractUser with additional fields.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class User(AbstractUser):
    """Custom user model with additional fields for e-commerce."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/',blank=True, null=True)
    
    # Address fields
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # User preferences
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    
    # User roles
    is_admin = models.BooleanField(default=False)
    is_vendor = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)

    # Payuee escrow transaction PIN - stored as a hash, never in plaintext.
    # Reuses Django's password hasher (set_password/check_password style)
    # rather than a bespoke scheme.
    payuee_transaction_pin_hash = models.CharField(max_length=128, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def has_payuee_pin(self):
        return bool(self.payuee_transaction_pin_hash)

    def set_payuee_pin(self, raw_pin):
        from django.contrib.auth.hashers import make_password
        self.payuee_transaction_pin_hash = make_password(raw_pin)

    def check_payuee_pin(self, raw_pin):
        from django.contrib.auth.hashers import check_password
        if not self.payuee_transaction_pin_hash:
            return False
        return check_password(raw_pin, self.payuee_transaction_pin_hash)

    @property
    def has_complete_profile(self):
        """Check if user has completed their profile."""
        return all([
            self.phone_number,
            self.address,
            self.city,
            self.state,
            self.country,
            self.postal_code
        ])


class UserActivity(models.Model):
    """Track user activity for analytics."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_activities'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type}"
