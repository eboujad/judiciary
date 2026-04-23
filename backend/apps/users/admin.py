from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'full_name', 'role', 'is_active', 'is_verified', 'created_at']
    list_filter   = ['role', 'is_active', 'is_verified', 'two_fa_enabled']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering      = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Role & Access', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified')}),
        ('2FA', {'fields': ('two_fa_enabled', 'two_fa_method')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'last_login_at')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'used', 'created_at', 'expires_at']
    list_filter  = ['used']
