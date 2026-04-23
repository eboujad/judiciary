"""
Immutable audit trail — every state change, review, and document action is logged.

Design decisions:
- AuditLog rows are INSERT-only. No UPDATE, no DELETE.
- actor can be NULL for system-initiated actions (payment callbacks, scheduled tasks).
- severity field enables critical alerts (tamper detection) to be surfaced separately.
- ip_address and user_agent stored for forensic analysis.
"""
import uuid
from django.db import models
from django.conf import settings


class AuditSeverity(models.TextChoices):
    INFO     = 'info',     'Info'
    WARNING  = 'warning',  'Warning'
    CRITICAL = 'critical', 'Critical'


class AuditLog(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who did it (null = system / background task)
    actor        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
    )
    actor_role   = models.CharField(max_length=30, blank=True)

    # What was done
    action       = models.CharField(max_length=100, db_index=True,
                                    help_text='e.g. status_changed:draft→pending_accounts')
    # What object was affected
    content_type = models.CharField(max_length=50,
                                    help_text='e.g. case, document, payment, user')
    object_id    = models.CharField(max_length=36, db_index=True)

    note         = models.TextField(blank=True)
    severity     = models.CharField(
        max_length=10, choices=AuditSeverity.choices, default=AuditSeverity.INFO
    )

    # Request context
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.CharField(max_length=500, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        # Prevent accidental updates — enforced at DB level via migration
        indexes  = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        actor = self.actor.email if self.actor else 'system'
        return f'[{self.severity.upper()}] {actor} → {self.action} ({self.content_type}:{self.object_id})'

    def save(self, *args, **kwargs):
        # Capture actor_role at write time so it's preserved even if user role changes later
        if self.actor and not self.actor_role:
            self.actor_role = self.actor.role
        # _state.adding is True only on INSERT — self.pk is truthy even for new UUIDs
        if not self._state.adding:
            raise ValueError('AuditLog records are immutable — updates are not allowed.')
        super().save(*args, **kwargs)
