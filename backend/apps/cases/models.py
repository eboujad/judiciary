"""
Case models — the core of the judiciary e-filing system.

State machine (Phase 1):
    DRAFT
      ↓  payment confirmed
    PENDING_ACCOUNTS
      ↓  Accounts forwards
    PENDING_REGISTRAR
      ↓
    REGISTERED  ──or──  REJECTED
                            ↓  lawyer corrects & resubmits
                        RESUBMITTED
                            ↓
                        PENDING_ACCOUNTS  (re-enters queue)

Design decisions:
- Case ID uses UUID internally; a human-readable case_number (e.g. GJ-2024-HC-00001)
  is generated on registration to avoid exposing sequential IDs.
- Court tier is stored as a CharField against a fixed choices list — keeps it
  simple for Phase 1 without a separate Court model.
- CourtForm (fee schedule) is seeded via a fixture so it can change without a migration.
"""
import uuid
from django.conf import settings
from django.db import models


class CourtTier(models.TextChoices):
    CADI       = 'cadi',       'Cadi Court'
    MAGISTRATE = 'magistrate', 'Magistrates Court'
    HIGH       = 'high',       'High Court'
    APPEAL     = 'appeal',     'Court of Appeal'
    SUPREME    = 'supreme',    'Supreme Court'


class CaseType(models.TextChoices):
    # Criminal
    CRIMINAL_COMPLAINT = 'criminal_complaint', 'Criminal Complaint'
    BAIL_APPLICATION   = 'bail_application',   'Bail Application'
    # Civil
    CIVIL_CLAIM        = 'civil_claim',        'Civil Claim'
    DEBT_RECOVERY      = 'debt_recovery',      'Debt Recovery'
    # Family
    DIVORCE            = 'divorce',            'Divorce'
    CUSTODY            = 'custody',            'Child Custody'
    # Land
    LAND_DISPUTE       = 'land_dispute',       'Land Dispute'
    # Constitutional
    CONSTITUTIONAL     = 'constitutional',     'Constitutional Matter'
    # Islamic personal law (Cadi Courts)
    ISLAMIC_FAMILY     = 'islamic_family',     'Islamic Family Matter'
    # Other
    OTHER              = 'other',              'Other'


class CaseStatus(models.TextChoices):
    DRAFT              = 'draft',              'Draft'
    PENDING_ACCOUNTS   = 'pending_accounts',   'Pending Accounts Review'
    PENDING_REGISTRAR  = 'pending_registrar',  'Pending Registrar Review'
    REGISTERED         = 'registered',         'Registered'
    REJECTED           = 'rejected',           'Rejected'
    RESUBMITTED        = 'resubmitted',        'Resubmitted'
    # Phase 2+
    ASSIGNED           = 'assigned',           'Assigned to Judge'
    HEARING_SCHEDULED  = 'hearing_scheduled',  'Hearing Scheduled'
    ACTIVE             = 'active',             'Active / In Hearing'
    JUDGMENT_PENDING   = 'judgment_pending',   'Judgment Pending'
    JUDGMENT_DELIVERED = 'judgment_delivered', 'Judgment Delivered'
    APPEAL_FILED       = 'appeal_filed',       'Appeal Filed'
    CLOSED             = 'closed',             'Closed'
    ARCHIVED           = 'archived',           'Archived'


# Valid state transitions — enforced in the state machine
ALLOWED_TRANSITIONS = {
    CaseStatus.DRAFT:             [CaseStatus.PENDING_ACCOUNTS],
    CaseStatus.PENDING_ACCOUNTS:  [CaseStatus.PENDING_REGISTRAR, CaseStatus.REJECTED],
    CaseStatus.PENDING_REGISTRAR: [CaseStatus.REGISTERED, CaseStatus.REJECTED],
    CaseStatus.REJECTED:          [CaseStatus.RESUBMITTED],
    CaseStatus.RESUBMITTED:       [CaseStatus.PENDING_ACCOUNTS],
    CaseStatus.REGISTERED:        [CaseStatus.ASSIGNED],
    CaseStatus.ASSIGNED:          [CaseStatus.HEARING_SCHEDULED],
    CaseStatus.HEARING_SCHEDULED: [CaseStatus.ACTIVE],
    CaseStatus.ACTIVE:            [CaseStatus.JUDGMENT_PENDING, CaseStatus.HEARING_SCHEDULED],
    CaseStatus.JUDGMENT_PENDING:  [CaseStatus.JUDGMENT_DELIVERED],
    CaseStatus.JUDGMENT_DELIVERED:[CaseStatus.APPEAL_FILED, CaseStatus.CLOSED],
    CaseStatus.APPEAL_FILED:      [CaseStatus.CLOSED],
    CaseStatus.CLOSED:            [CaseStatus.ARCHIVED],
}


class CourtForm(models.Model):
    """
    Fee schedule — one row per form type per court.
    Seeded from fixtures; only admin can modify.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    court       = models.CharField(max_length=20, choices=CourtTier.choices)
    case_type   = models.CharField(max_length=50, choices=CaseType.choices, blank=True)
    name        = models.CharField(max_length=200, help_text='e.g. Originating Summons — High Court')
    description = models.TextField(blank=True)
    fee_amount  = models.DecimalField(max_digits=10, decimal_places=2, help_text='Fee in GMD')
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'court_forms'
        ordering = ['court', 'name']
        unique_together = [['court', 'name']]

    def __str__(self):
        return f'{self.name} — {self.get_court_display()} (GMD {self.fee_amount})'


class Case(models.Model):
    """
    Central case record. All other Phase 1 entities attach to this.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Human-readable number assigned on REGISTRATION (not on creation)
    case_number = models.CharField(max_length=30, unique=True, null=True, blank=True,
                                   help_text='e.g. GJ-2024-HC-00001 — set by Registrar on registration')

    title       = models.CharField(max_length=300, help_text='e.g. Ndure v. Ceesay')
    court       = models.CharField(max_length=20, choices=CourtTier.choices)
    case_type   = models.CharField(max_length=50, choices=CaseType.choices)
    status      = models.CharField(max_length=30, choices=CaseStatus.choices, default=CaseStatus.DRAFT)

    submitted_by    = models.ForeignKey(
        'firms.Lawyer', on_delete=models.PROTECT, related_name='cases'
    )
    # Phase 2: assigned_judge = models.ForeignKey(User, ...)

    # Metadata
    description         = models.TextField(blank=True, help_text='Brief facts of the case')
    opposing_party_name = models.CharField(max_length=200, blank=True)
    relief_sought       = models.TextField(blank=True)

    # Tracking
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    submitted_at    = models.DateTimeField(null=True, blank=True, help_text='When moved to PENDING_ACCOUNTS')
    registered_at   = models.DateTimeField(null=True, blank=True, help_text='When officially registered')

    # Sealed case flag (Phase 3 — child custody, state security, etc.)
    is_sealed       = models.BooleanField(default=False)

    class Meta:
        db_table = 'cases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['court']),
            models.Index(fields=['submitted_by']),
            models.Index(fields=['case_number']),
        ]

    def __str__(self):
        ref = self.case_number or str(self.id)[:8]
        return f'{self.title} [{ref}]'

    def transition_to(self, new_status: str, actor, note: str = ''):
        """
        Enforces state machine transitions. Raises ValueError on invalid moves.
        Always creates an AuditLog entry.
        """
        current = self.status
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition case from '{current}' to '{new_status}'. "
                f"Allowed: {[s for s in allowed]}"
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

        from apps.audit.models import AuditLog
        AuditLog.objects.create(
            actor=actor,
            action=f'status_changed:{current}→{new_status}',
            content_type='case',
            object_id=str(self.id),
            note=note,
        )

    def generate_case_number(self):
        """
        Generates GJ-YYYY-{COURT}-{SEQUENCE}.
        Called by the Registrar when officially registering a case.
        """
        from django.utils import timezone
        court_code = {
            'cadi': 'CA', 'magistrate': 'MC',
            'high': 'HC', 'appeal': 'AP', 'supreme': 'SC',
        }.get(self.court, 'XX')
        year = timezone.now().year
        # select_for_update prevents duplicate sequence numbers under concurrent registrations
        count = Case.objects.select_for_update().filter(
            court=self.court,
            registered_at__year=year,
            case_number__isnull=False,
        ).count() + 1
        return f'GJ-{year}-{court_code}-{count:05d}'


class CaseForm(models.Model):
    """Forms selected for a case — determines total fee."""
    case    = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='selected_forms')
    form    = models.ForeignKey(CourtForm, on_delete=models.PROTECT)

    class Meta:
        db_table = 'case_forms'
        unique_together = [['case', 'form']]

    def __str__(self):
        return f'{self.case} → {self.form.name}'


class SubmissionNote(models.Model):
    """
    Written by Accounts or Registrar when reviewing a case.
    Immutable once created — these are the official record.
    """
    class StaffRole(models.TextChoices):
        ACCOUNTS   = 'accounts',   'Accounts Department'
        REGISTRAR  = 'registrar',  'Registrar'

    class Action(models.TextChoices):
        FORWARDED   = 'forwarded',   'Forwarded to Registrar'
        REGISTERED  = 'registered',  'Case Registered'
        REJECTED    = 'rejected',    'Case Rejected'
        FLAGGED     = 'flagged',     'Flagged for Correction'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case        = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='submission_notes')
    author      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    staff_role  = models.CharField(max_length=20, choices=StaffRole.choices)
    note        = models.TextField()
    action      = models.CharField(max_length=20, choices=Action.choices)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'submission_notes'
        ordering  = ['created_at']

    def __str__(self):
        return f'{self.staff_role} note on {self.case} — {self.action}'
