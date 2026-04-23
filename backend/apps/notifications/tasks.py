"""
Celery tasks for sending notifications.
All notification sends are async — the web request returns immediately,
and the Celery worker dispatches the actual SMS/email.
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Notification, NotificationChannel, NotificationStatus

logger = logging.getLogger(__name__)


def _send_sms(phone: str, body: str) -> bool:
    """Send SMS via Twilio (or console in dev)."""
    sms_backend = getattr(settings, 'SMS_BACKEND', 'console')

    if sms_backend == 'console':
        logger.info('[SMS → %s]: %s', phone, body)
        return True

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=phone)
        return True
    except Exception as e:
        logger.error('SMS send failed to %s: %s', phone, e)
        return False


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via SendGrid (or Django console backend in dev)."""
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error('Email send failed to %s: %s', to_email, e)
        return False


def _create_and_send(recipient, channel, subject, body, content_type='', object_id=''):
    """Create Notification record and attempt send."""
    notif = Notification.objects.create(
        recipient=recipient, channel=channel,
        subject=subject, body=body,
        content_type=content_type, object_id=str(object_id),
    )
    success = False
    try:
        if channel == NotificationChannel.SMS and recipient.phone:
            success = _send_sms(recipient.phone, body)
        elif channel == NotificationChannel.EMAIL and recipient.email:
            success = _send_email(recipient.email, subject, body)
    except Exception as e:
        notif.error_msg = str(e)

    notif.status   = NotificationStatus.SENT if success else NotificationStatus.FAILED
    notif.sent_at  = timezone.now() if success else None
    notif.save(update_fields=['status', 'sent_at', 'error_msg'])
    return success


# ── Task definitions ──────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_case_submitted(self, case_id: str):
    """Notify lawyer that their case has been received by Accounts."""
    try:
        from apps.cases.models import Case
        case   = Case.objects.select_related('submitted_by__user').get(id=case_id)
        lawyer = case.submitted_by.user
        ref    = case.case_number or str(case.id)[:8].upper()

        sms_body = (
            f'Gambia Judiciary: Your case "{case.title[:40]}" '
            f'has been received and is pending Accounts review. Ref: {ref}'
        )
        email_body = (
            f'Dear {lawyer.full_name},\n\n'
            f'Your case "{case.title}" has been successfully submitted.\n'
            f'Reference: {ref}\n'
            f'Status: Pending Accounts Department review.\n\n'
            f'You will be notified of any updates.\n\nGambia Judiciary E-Filing System'
        )
        _create_and_send(lawyer, NotificationChannel.SMS, '', sms_body, 'case', case_id)
        _create_and_send(lawyer, NotificationChannel.EMAIL, f'Case Submitted — {ref}', email_body, 'case', case_id)
    except Exception as exc:
        logger.error('notify_case_submitted failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_case_status_changed(self, case_id: str):
    """Notify lawyer of case status change (forwarded, registered, rejected)."""
    try:
        from apps.cases.models import Case
        case   = Case.objects.select_related('submitted_by__user').prefetch_related('submission_notes').get(id=case_id)
        lawyer = case.submitted_by.user
        ref    = case.case_number or str(case.id)[:8].upper()
        status = case.get_status_display()

        # Get latest note for context
        latest_note = case.submission_notes.order_by('-created_at').first()
        note_text   = f'\nNote: {latest_note.note}' if latest_note else ''

        sms_body = (
            f'Gambia Judiciary: Case {ref} status changed to "{status}".{note_text[:100]}'
        )
        email_body = (
            f'Dear {lawyer.full_name},\n\n'
            f'Your case "{case.title}" (Ref: {ref}) status has changed.\n'
            f'New status: {status}{note_text}\n\n'
            f'Log in to the portal to view details.\n\nGambia Judiciary E-Filing System'
        )
        _create_and_send(lawyer, NotificationChannel.SMS, '', sms_body, 'case', case_id)
        _create_and_send(lawyer, NotificationChannel.EMAIL, f'Case Update — {ref}', email_body, 'case', case_id)
    except Exception as exc:
        logger.error('notify_case_status_changed failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_payment_confirmed(self, payment_id: str):
    """Notify lawyer that their payment was confirmed."""
    try:
        from apps.payments.models import Payment
        payment = Payment.objects.select_related('case__submitted_by__user', 'receipt').get(id=payment_id)
        lawyer  = payment.case.submitted_by.user
        receipt = getattr(payment, 'receipt', None)

        sms_body = (
            f'Gambia Judiciary: Payment of GMD {payment.amount_paid} confirmed. '
            f'Receipt: {receipt.receipt_number if receipt else "N/A"}. '
            f'Case: {payment.case.title[:30]}'
        )
        email_body = (
            f'Dear {lawyer.full_name},\n\n'
            f'Payment Confirmation\n'
            f'Case: {payment.case.title}\n'
            f'Amount: GMD {payment.amount_paid}\n'
            f'MUSU Reference: {payment.musu_reference}\n'
            f'Receipt No: {receipt.receipt_number if receipt else "N/A"}\n\n'
            f'Your case is now pending Accounts Department review.\n\n'
            f'Gambia Judiciary E-Filing System'
        )
        _create_and_send(lawyer, NotificationChannel.SMS, '', sms_body, 'payment', payment_id)
        _create_and_send(lawyer, NotificationChannel.EMAIL, 'Payment Confirmed', email_body, 'payment', payment_id)
    except Exception as exc:
        logger.error('notify_payment_confirmed failed: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_case_resubmitted(self, case_id: str):
    """Notify Accounts staff that a rejected case has been resubmitted."""
    try:
        from apps.cases.models import Case
        from apps.users.models import User, UserRole
        case          = Case.objects.select_related('submitted_by__user').get(id=case_id)
        accounts_staff = User.objects.filter(role=UserRole.ACCOUNTS_DEPT, is_active=True)
        ref            = str(case.id)[:8].upper()

        for staff in accounts_staff:
            body = (
                f'Gambia Judiciary: Case "{case.title[:40]}" (Ref: {ref}) '
                f'has been resubmitted and is in your queue.'
            )
            _create_and_send(staff, NotificationChannel.EMAIL,
                             f'Case Resubmitted — {ref}', body, 'case', case_id)
    except Exception as exc:
        logger.error('notify_case_resubmitted failed: %s', exc)
        raise self.retry(exc=exc)
