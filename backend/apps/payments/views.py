"""
Payment views.

Flow:
  1. POST /payments/cases/<case_id>/initiate/
     → Creates Payment record, calls MUSU, returns payment_url
  2. User pays on MUSU mobile app / USSD
  3. MUSU POSTs to /payments/callback/  (webhook — HMAC verified)
     → Confirms payment, advances case to PENDING_ACCOUNTS
  4. DEV ONLY: POST /payments/mock-confirm/ for local testing
"""
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from core.permissions import IsLawyer
from apps.cases.models import Case, CaseStatus
from .models import Payment, PaymentStatus, PaymentReceipt
from .serializers import PaymentSerializer, PaymentInitiateSerializer, MockConfirmSerializer
from .musu_client import musu_client

logger = logging.getLogger(__name__)


def _generate_receipt_number() -> str:
    from django.utils import timezone
    import random
    year = timezone.now().year
    seq  = random.randint(100000, 999999)
    return f'REC-{year}-{seq}'


def _confirm_payment(payment: Payment, amount_paid: Decimal,
                     transaction_id: str, raw_payload: dict):
    """
    Shared logic for confirming a payment — called by webhook and mock endpoint.
    Advances the case to PENDING_ACCOUNTS inside a transaction.
    """
    with transaction.atomic():
        payment.status             = PaymentStatus.CONFIRMED
        payment.amount_paid        = amount_paid
        payment.musu_transaction_id = transaction_id
        payment.confirmed_at       = timezone.now()
        payment.musu_raw_payload   = raw_payload
        payment.save()

        # Generate receipt
        PaymentReceipt.objects.get_or_create(
            payment=payment,
            defaults={'receipt_number': _generate_receipt_number()},
        )

        # Advance case status
        case = payment.case
        if case.status == CaseStatus.DRAFT:
            case.submitted_at = timezone.now()
            case.save(update_fields=['submitted_at'])
            case.transition_to(
                CaseStatus.PENDING_ACCOUNTS,
                actor=None,
                note=f'Payment confirmed — MUSU ref {payment.musu_reference}',
            )

    # Trigger notification (outside transaction)
    from apps.notifications.tasks import notify_payment_confirmed
    notify_payment_confirmed.delay(str(payment.id))


class PaymentInitiateView(APIView):
    """
    POST /payments/cases/<case_id>/initiate/
    Creates/retrieves Payment, calculates fee, calls MUSU.
    """
    permission_classes = [IsLawyer]

    def post(self, request, case_id):
        case = get_object_or_404(
            Case, id=case_id,
            submitted_by__user=request.user,
            status=CaseStatus.DRAFT,
        )

        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payer_phone = serializer.validated_data['payer_phone']

        # Idempotent — reuse existing pending payment
        payment, created = Payment.objects.get_or_create(
            case=case,
            defaults={'amount_due': 0},
        )

        # (Re)calculate fee in case forms changed
        amount_due = payment.calculate_amount_due()
        if amount_due == 0:
            return Response(
                {'detail': 'No court forms selected. Add forms before initiating payment.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.amount_due  = amount_due
        payment.payer_phone = payer_phone
        payment.status      = PaymentStatus.INITIATED
        payment.initiated_at = timezone.now()
        payment.save()

        # Build callback URL
        callback_url = request.build_absolute_uri('/api/v1/payments/callback/')

        try:
            result = musu_client.initiate_payment(
                case_id=str(case.id),
                amount=amount_due,
                payer_phone=payer_phone,
                callback_url=callback_url,
                description=f'Court filing fee — {case.title[:60]}',
            )
        except Exception as e:
            logger.error('MUSU initiation failed for case %s: %s', case.id, e)
            payment.status = PaymentStatus.FAILED
            payment.save(update_fields=['status'])
            return Response(
                {'detail': 'Payment gateway temporarily unavailable. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        payment.musu_reference = result['reference']
        payment.save(update_fields=['musu_reference', 'status', 'initiated_at',
                                    'amount_due', 'payer_phone'])

        return Response({
            'payment':     PaymentSerializer(payment).data,
            'payment_url': result.get('payment_url'),
        })


@method_decorator(csrf_exempt, name='dispatch')
class MUSUCallbackView(APIView):
    """
    POST /payments/callback/
    MUSU webhook — called by MUSU on payment completion.
    This endpoint is PUBLIC (no JWT) but HMAC-signature verified.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        # Verify MUSU signature
        signature = request.headers.get('X-MUSU-Signature', '')
        raw_body  = request.body

        if not musu_client.verify_webhook_signature(raw_body, signature):
            logger.warning('MUSU webhook: invalid signature')
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({'detail': 'Invalid JSON.'}, status=status.HTTP_400_BAD_REQUEST)

        reference      = payload.get('reference')
        musu_status    = payload.get('status')
        transaction_id = payload.get('transaction_id', '')
        raw_amount     = payload.get('amount_paid')
        amount_paid    = Decimal(str(raw_amount)) if raw_amount is not None else None

        if not reference:
            return Response({'detail': 'Missing reference.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_related('case').get(musu_reference=reference)
        except Payment.DoesNotExist:
            logger.error('MUSU callback: unknown reference %s', reference)
            return Response({'detail': 'Unknown reference.'}, status=status.HTTP_404_NOT_FOUND)

        # Idempotent — ignore duplicate confirmations
        if payment.status == PaymentStatus.CONFIRMED:
            return Response({'detail': 'Already confirmed.'})

        if musu_status == 'confirmed':
            _confirm_payment(
                payment=payment,
                amount_paid=amount_paid if amount_paid is not None else payment.amount_due,
                transaction_id=transaction_id,
                raw_payload=payload,
            )
            logger.info('Payment confirmed via webhook: %s', reference)
        elif musu_status == 'failed':
            payment.status = PaymentStatus.FAILED
            payment.musu_raw_payload = payload
            payment.save(update_fields=['status', 'musu_raw_payload'])
            logger.info('Payment failed via webhook: %s', reference)

        return Response({'detail': 'Received.'})


class MockPaymentConfirmView(APIView):
    """
    POST /payments/mock-confirm/
    DEV ONLY — instantly confirms a payment for local testing.
    Disabled in production.
    """
    permission_classes = [IsLawyer]

    def post(self, request):
        if not settings.DEBUG:
            return Response(
                {'detail': 'Mock confirm is only available in development.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MockConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference = serializer.validated_data.get('reference')
        case_id   = serializer.validated_data.get('case_id')

        if reference:
            payment = get_object_or_404(
                Payment,
                musu_reference=reference,
                case__submitted_by__user=request.user,
            )
        else:
            payment = get_object_or_404(
                Payment,
                case__id=case_id,
                case__submitted_by__user=request.user,
            )

        if payment.status == PaymentStatus.CONFIRMED:
            return Response({'detail': 'Already confirmed.', 'payment': PaymentSerializer(payment).data})

        ref = reference or payment.musu_reference or 'MOCK-REF'
        _confirm_payment(
            payment=payment,
            amount_paid=payment.amount_due,
            transaction_id=f'MOCK-TXN-{ref}',
            raw_payload={'mock': True, 'reference': ref},
        )

        payment.refresh_from_db()
        return Response({
            'detail': 'Payment confirmed (mock).',
            'payment': PaymentSerializer(payment).data,
            'case_status': payment.case.status,
        })


class PaymentStatusView(APIView):
    """GET /payments/cases/<case_id>/ — current payment info for a case."""
    permission_classes = [IsLawyer]

    def get(self, request, case_id):
        case = get_object_or_404(Case, id=case_id, submitted_by__user=request.user)
        try:
            payment = case.payment
        except Payment.DoesNotExist:
            return Response({'detail': 'No payment found for this case.'}, status=404)
        return Response(PaymentSerializer(payment).data)
