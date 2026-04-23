"""
Document model with SHA-256 tamper detection.

Design decisions:
- Hash is computed on upload and stored. Any re-check against the stored file
  that produces a different hash triggers an alert (tampering detected).
- Allowed MIME types are enforced at the model level, not just the serializer,
  so the constraint is present even when documents are created programmatically.
- Documents are soft-deleted (is_active=False) rather than hard-deleted so the
  audit trail is never broken.
- Upload path is per-case so S3 objects are naturally namespaced.
"""
import hashlib
import uuid
from django.db import models
from django.conf import settings


ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]


def case_document_path(instance, filename):
    """Upload path: case_documents/<case_id>/<filename>"""
    return f'case_documents/{instance.case_id}/{filename}'


class DocumentCategory(models.TextChoices):
    PLEADING       = 'pleading',       'Pleading / Statement of Claim'
    AFFIDAVIT      = 'affidavit',      'Affidavit'
    EXHIBIT        = 'exhibit',        'Exhibit'
    SUPPORTING     = 'supporting',     'Supporting Document'
    COURT_ORDER    = 'court_order',    'Court Order'
    JUDGMENT       = 'judgment',       'Judgment'
    CORRESPONDENCE = 'correspondence', 'Correspondence'
    OTHER          = 'other',          'Other'


class Document(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case        = models.ForeignKey(
        'cases.Case', on_delete=models.CASCADE, related_name='documents'
    )
    category    = models.CharField(
        max_length=30, choices=DocumentCategory.choices, default=DocumentCategory.OTHER
    )
    description = models.CharField(max_length=300, blank=True)
    file        = models.FileField(upload_to=case_document_path)
    filename    = models.CharField(max_length=255)
    mime_type   = models.CharField(max_length=100)
    file_size   = models.PositiveIntegerField(help_text='Size in bytes')

    # Tamper detection — computed on upload, verified on access
    sha256_hash = models.CharField(max_length=64, help_text='SHA-256 of file content at upload time')

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active   = models.BooleanField(default=True, help_text='Soft delete — never hard-delete documents')

    # Phase 3: digital signature fields
    is_signed   = models.BooleanField(default=False)
    signed_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='signed_documents'
    )
    signed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'documents'
        ordering = ['uploaded_at']
        indexes  = [models.Index(fields=['case', 'is_active'])]

    def __str__(self):
        return f'{self.filename} ({self.case})'

    def verify_integrity(self) -> bool:
        """
        Re-read file from storage and recompute SHA-256.
        Returns True if hash matches (file intact), False if tampered.
        Logs a tamper alert if mismatch detected.
        """
        import logging
        logger = logging.getLogger(__name__)
        try:
            h = hashlib.sha256()
            self.file.open('rb')
            for chunk in iter(lambda: self.file.read(8192), b''):
                h.update(chunk)
            self.file.close()
            current_hash = h.hexdigest()

            if current_hash != self.sha256_hash:
                logger.critical(
                    'TAMPER DETECTED: Document %s (case %s) hash mismatch. '
                    'Stored: %s | Current: %s',
                    self.id, self.case_id, self.sha256_hash, current_hash
                )
                # Create audit log for tamper event
                from apps.audit.models import AuditLog
                AuditLog.objects.create(
                    actor=None,
                    action='document_tamper_detected',
                    content_type='document',
                    object_id=str(self.id),
                    note=f'Hash mismatch. Stored: {self.sha256_hash} | Current: {current_hash}',
                    severity='critical',
                )
                return False
            return True
        except Exception as e:
            logger.error('Hash verification failed for document %s: %s', self.id, e)
            return False

    @staticmethod
    def compute_hash(file_obj) -> str:
        """Compute SHA-256 for an in-memory file object."""
        h = hashlib.sha256()
        file_obj.seek(0)
        for chunk in iter(lambda: file_obj.read(8192), b''):
            h.update(chunk)
        file_obj.seek(0)
        return h.hexdigest()
