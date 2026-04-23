from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['recipient', 'channel', 'subject', 'status', 'created_at', 'sent_at']
    list_filter   = ['channel', 'status']
    search_fields = ['recipient__email', 'subject', 'body']
    readonly_fields = ['id', 'created_at', 'sent_at']
