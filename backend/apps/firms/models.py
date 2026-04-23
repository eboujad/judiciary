"""
Law Firm & Lawyer models.

Design decisions:
- LawFirm is the billing/registration entity. Lawyers are sub-accounts.
- A Lawyer's bar_number is validated against the Gambia Bar Association.
- FirmStatus: only 'active' firms can submit new cases.
- Bar numbers are unique system-wide to prevent duplicate registrations.
"""
import uuid
from django.db import models
from apps.users.models import User


class FirmStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending Approval'
    ACTIVE    = 'active',    'Active'
    SUSPENDED = 'suspended', 'Suspended'
    REVOKED   = 'revoked',   'Revoked'


class LawFirm(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200)
    bar_number      = models.CharField(max_length=50, unique=True, help_text='Gambia Bar Association firm registration number')
    address         = models.TextField()
    phone           = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    status          = models.CharField(max_length=20, choices=FirmStatus.choices, default=FirmStatus.PENDING)

    # The firm's admin user — can create lawyer sub-accounts
    admin_user      = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name='managed_firm', null=True, blank=True
    )

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    approved_at     = models.DateTimeField(null=True, blank=True)
    approved_by     = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_firms'
    )

    class Meta:
        db_table = 'law_firms'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.bar_number})'

    @property
    def is_active(self):
        return self.status == FirmStatus.ACTIVE

    @property
    def lawyer_count(self):
        return self.lawyers.filter(is_active=True).count()


class Lawyer(models.Model):
    """
    Extended profile for LAWYER-role users.
    Created by a FirmAdmin when they add a lawyer sub-account.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lawyer_profile')
    firm        = models.ForeignKey(LawFirm, on_delete=models.CASCADE, related_name='lawyers')
    bar_number  = models.CharField(max_length=50, unique=True, help_text='Individual bar registration number')
    specialisation = models.CharField(max_length=200, blank=True, help_text='e.g. Commercial, Criminal, Family')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lawyers'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f'{self.user.full_name} — {self.firm.name}'
