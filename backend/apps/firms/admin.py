from django.contrib import admin
from .models import LawFirm, Lawyer


class LawyerInline(admin.TabularInline):
    model  = Lawyer
    extra  = 0
    fields = ['user', 'bar_number', 'specialisation', 'is_active']
    readonly_fields = ['user']


@admin.register(LawFirm)
class LawFirmAdmin(admin.ModelAdmin):
    list_display  = ['name', 'bar_number', 'status', 'lawyer_count', 'created_at']
    list_filter   = ['status']
    search_fields = ['name', 'bar_number', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'approved_at']
    inlines       = [LawyerInline]

    actions = ['approve_firms']

    def approve_firms(self, request, queryset):
        from django.utils import timezone
        from .models import FirmStatus
        updated = queryset.filter(status=FirmStatus.PENDING).update(
            status=FirmStatus.ACTIVE,
            approved_at=timezone.now(),
            approved_by=request.user,
        )
        self.message_user(request, f'{updated} firm(s) approved.')
    approve_firms.short_description = 'Approve selected firms'


@admin.register(Lawyer)
class LawyerAdmin(admin.ModelAdmin):
    list_display  = ['user', 'firm', 'bar_number', 'specialisation', 'is_active']
    list_filter   = ['is_active', 'firm']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'bar_number']
