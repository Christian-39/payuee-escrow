from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserActivity


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin with image preview."""

    list_display = [
        'email',
        'full_name',
        'phone_number',
        'image_preview',  # ✅ ADDED
        'is_admin',
        'is_active',
        'email_verified',
        'created_at'
    ]

    list_filter = ['is_admin', 'is_active', 'email_verified', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),

        ('Personal info', {
            'fields': (
                'first_name',
                'last_name',
                'phone_number',
                'profile_image',
                'image_preview',  # ✅ SHOW PREVIEW HERE
            )
        }),

        ('Address', {
            'fields': (
                'address', 'city', 'state', 'country', 'postal_code'
            )
        }),

        ('Permissions', {
            'fields': (
                'is_active', 'is_admin', 'is_vendor',
                'is_staff', 'is_superuser', 'groups', 'user_permissions'
            )
        }),

        ('Preferences', {
            'fields': (
                'dark_mode', 'email_notifications',
                'push_notifications', 'marketing_emails'
            )
        }),

        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'image_preview']  # ✅ ADD HERE

    # ✅ IMAGE PREVIEW FUNCTION
    def image_preview(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius:50%; object-fit:cover;" />',
                obj.profile_image.url
            )
        return "No Image"

    image_preview.short_description = "Profile Image"


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """User activity admin."""

    list_display = ['user', 'activity_type', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__email', 'description']
    readonly_fields = ['created_at']