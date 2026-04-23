"""
Payment models — MUSU mobile money gateway integration.

Design decisions:
- One Payment per Case (OneToOne). A case cannot have two active payments.
- Payment is initiated with amount_due calculated from selected CourtForms.
- MUSU sends a signed webhook callback; we verify the signature before
  confirming payment (prevents fake confirmations).
- amount_paid may differ from amount_due (overpayment/underpayment) — both
  are stored so Accounts can flag discrepancies.
- PaymentReceipt is generated server-side on confirmation for archival.
"""
import uuid
from django.db import models
from django.conf import settings


class PaymentStatus(models.TextChoices):
    PENDING   = 'pending',   'Pending — awaiting payment'
    INITIATED = 'initiated', 'Initiated — sent to MUSU'
    CONFIRMED = 'confirmed', 'Confirmed — payment received'
    FAILED    = 'failed',    'Failed'
    REFUNDED  = 'refunded',  'Refunded'


class Payment(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case             = models.OneToOneField(
        'cases.Case', on_delete=models.CASCADE, related_name='payment'
    )

    # Fee calculation — sum of all CaseForm fees
    amount_due       = models.DecimalField(max_digits=10, decimal_places=2, help_text='GMD')
    # Amount actually received from MUSU (may differ)
    amount_paid      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status           = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )

    # MUSU gateway fields
    musu_reference   = models.CharField(
        max_length=100, unique=True, null=True, blank=True,
        help_text='Reference returned by MUSU on initiation'
    )
    musu_transaction_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text='Final transaction ID in MUSU system'
    )
    payer_phone      = models.CharField(max_length=20, blank=True, help_text='Mobile number used to pay')

    # Fee waiver (Phase 3 — indigent)
    is_waived        = models.BooleanField(default=False)
    waiver_reason    = models.TextField(blank=True)

    # Timestamps
    created_at       = models.DateTimeField(auto_now_add=True)
    initiated_at     = models.DateTimeField(null=True, blank=True)
    confirmed_at     = models.DateTimeField(null=True, blank=True)

    # Raw MUSU webhook payload — stored for audit
    musu_raw_payload = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f'Payment for {self.case} — {self.status} (GMD {self.amount_due})'

    @property
    def is_confirmed(self):
        return self.status == PaymentStatus.CONFIRMED

    @property
    def has_discrepancy(self):
        if self.amount_paid is None:
            return False
        return self.amount_paid != self.amount_due

    def calculate_amount_due(self):
        """Sum fees of all CourtForms attached to the case."""
        from django.db.models import Sum
        total = self.case.selected_forms.aggregate(total=Sum('form__fee_amount'))['total']
        return total or 0


class PaymentReceipt(models.Model):
    """Immutable receipt generated on payment confirmation."""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment     = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    issued_at   = models.DateTimeField(auto_now_add=True)
    # PDF receipt stored in S3
    pdf_file    = models.FileField(upload_to='receipts/', null=True, blank=True)

    class Meta:
        db_table = 'payment_receipts'

    def __str__(self):
        return f'Receipt {self.receipt_number}'
