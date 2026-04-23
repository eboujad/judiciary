"""
Notification log — every SMS/email sent is recorded for audit and re-send.
"""
import uuid
from django.db import models
from django.conf import settings


class NotificationChannel(models.TextChoices):
    SMS   = 'sms',   'SMS'
    EMAIL = 'email', 'Email'
    PUSH  = 'push',  'Push Notification'


class NotificationStatus(models.TextChoices):
    PENDING  = 'pending',  'Pending'
    SENT     = 'sent',     'Sent'
    FAILED   = 'failed',   'Failed'
    BOUNCED  = 'bounced',  'Bounced'


class Notification(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    channel     = models.CharField(max_length=10, choices=NotificationChannel.choices)
    subject     = models.CharField(max_length=200, blank=True)
    body        = models.TextField()
    status      = models.CharField(max_length=10, choices=NotificationStatus.choices,
                                   default=NotificationStatus.PENDING)
    # Related object (case, payment, etc.)
    content_type = models.CharField(max_length=50, blank=True)
    object_id    = models.CharField(max_length=36, blank=True)

    sent_at     = models.DateTimeField(null=True, blank=True)
    error_msg   = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.channel} to {self.recipient.email} — {self.status}'
