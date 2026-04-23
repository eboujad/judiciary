"""
Case views — implements the full Phase 1 workflow:
  Lawyer creates → pays → Accounts reviews → Registrar registers/rejects
"""
import logging
from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from core.permissions import IsLawyer, IsAccountsDept, IsRegistrar, IsLawyerOrInternal
from .models import Case, CaseStatus, CourtForm, SubmissionNote
from .serializers import (
    CaseListSerializer, CaseDetailSerializer, CaseCreateSerializer,
    CourtFormSerializer, AccountsReviewSerializer, RegistrarReviewSerializer,
)

logger = logging.getLogger(__name__)


class CourtFormListView(generics.ListAPIView):
    """GET /cases/forms/?court=high — fee schedule for a given court."""
    serializer_class   = CourtFormSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset           = CourtForm.objects.filter(is_active=True)
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['court', 'case_type']


class CaseListCreateView(generics.ListCreateAPIView):
    """
    GET  /cases/      — Lawyer: my cases. Staff: filtered by role.
    POST /cases/      — Lawyer: create new case draft.
    """
    permission_classes = [IsLawyerOrInternal]
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = ['status', 'court', 'case_type']
    search_fields      = ['title', 'case_number', 'opposing_party_name']
    ordering_fields    = ['created_at', 'submitted_at', 'status']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CaseCreateSerializer
        return CaseListSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = Case.objects.select_related('submitted_by__user', 'submitted_by__firm')
        if user.role == 'lawyer':
            # Lawyers see only their firm's cases
            return qs.filter(submitted_by__firm=user.lawyer_profile.firm)
        return qs.all()  # Staff see all


class CaseDetailView(generics.RetrieveAPIView):
    """GET /cases/<id>/"""
    serializer_class   = CaseDetailSerializer
    permission_classes = [IsLawyerOrInternal]
    lookup_field       = 'id'

    def get_queryset(self):
        user = self.request.user
        qs   = Case.objects.prefetch_related(
            'selected_forms__form', 'submission_notes__author',
            'documents', 'payment',
        ).select_related('submitted_by__user', 'submitted_by__firm')
        if user.role == 'lawyer':
            return qs.filter(submitted_by__firm=user.lawyer_profile.firm)
        return qs.all()


class CaseSubmitView(APIView):
    """
    POST /cases/<id>/submit/
    Lawyer submits a DRAFT case for payment.
    Transition: DRAFT → PENDING_ACCOUNTS (after payment confirmed).
    The frontend initiates MUSU payment first; this endpoint is called by
    the payment callback to advance the case.
    """
    permission_classes = [IsLawyer]

    def post(self, request, id):
        case = get_object_or_404(Case, id=id, submitted_by__user=request.user)
        if case.status != CaseStatus.DRAFT:
            return Response(
                {'detail': 'Only DRAFT cases can be submitted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Payment must be confirmed
        try:
            payment = case.payment
        except Exception:
            return Response(
                {'detail': 'No payment record found. Initiate payment first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payment.status != 'confirmed':
            return Response(
                {'detail': 'Payment must be confirmed before submitting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            case.submitted_at = timezone.now()
            case.save(update_fields=['submitted_at'])
            case.transition_to(CaseStatus.PENDING_ACCOUNTS, actor=request.user)

        # Trigger notification task
        from apps.notifications.tasks import notify_case_submitted
        notify_case_submitted.delay(str(case.id))

        return Response(CaseDetailSerializer(case).data)


# ── Accounts Department ───────────────────────────────────────────────────

class AccountsQueueView(generics.ListAPIView):
    """GET /cases/accounts/queue/ — cases awaiting Accounts review."""
    serializer_class   = CaseListSerializer
    permission_classes = [IsAccountsDept]

    def get_queryset(self):
        return Case.objects.filter(
            status__in=[CaseStatus.PENDING_ACCOUNTS, CaseStatus.RESUBMITTED]
        ).select_related('submitted_by__user', 'submitted_by__firm').order_by('submitted_at')


class AccountsReviewView(APIView):
    """POST /cases/<id>/accounts/review/ — Accounts forward or flag."""
    permission_classes = [IsAccountsDept]

    def post(self, request, id):
        case       = get_object_or_404(Case, id=id, status__in=[
            CaseStatus.PENDING_ACCOUNTS, CaseStatus.RESUBMITTED
        ])
        serializer = AccountsReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data       = serializer.validated_data

        with transaction.atomic():
            if data['action'] == 'forward':
                new_status  = CaseStatus.PENDING_REGISTRAR
                note_action = SubmissionNote.Action.FORWARDED
            else:  # flag
                new_status  = CaseStatus.REJECTED
                note_action = SubmissionNote.Action.FLAGGED

            SubmissionNote.objects.create(
                case       = case,
                author     = request.user,
                staff_role = SubmissionNote.StaffRole.ACCOUNTS,
                note       = data['note'],
                action     = note_action,
            )
            case.transition_to(new_status, actor=request.user, note=data['note'])

        from apps.notifications.tasks import notify_case_status_changed
        notify_case_status_changed.delay(str(case.id))

        return Response(CaseDetailSerializer(case).data)


# ── Registrar ─────────────────────────────────────────────────────────────

class RegistrarQueueView(generics.ListAPIView):
    """GET /cases/registrar/queue/ — cases forwarded by Accounts."""
    serializer_class   = CaseListSerializer
    permission_classes = [IsRegistrar]

    def get_queryset(self):
        return Case.objects.filter(
            status=CaseStatus.PENDING_REGISTRAR
        ).select_related('submitted_by__user', 'submitted_by__firm').order_by('submitted_at')


class RegistrarReviewView(APIView):
    """POST /cases/<id>/registrar/review/ — Registrar register or reject."""
    permission_classes = [IsRegistrar]

    def post(self, request, id):
        case       = get_object_or_404(Case, id=id, status=CaseStatus.PENDING_REGISTRAR)
        serializer = RegistrarReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data       = serializer.validated_data

        with transaction.atomic():
            if data['action'] == 'register':
                new_status  = CaseStatus.REGISTERED
                note_action = SubmissionNote.Action.REGISTERED

                # Generate official case number
                case_number = case.generate_case_number()
                case.case_number  = case_number
                case.registered_at = timezone.now()
                case.save(update_fields=['case_number', 'registered_at'])

            else:  # reject
                new_status  = CaseStatus.REJECTED
                note_action = SubmissionNote.Action.REJECTED

            SubmissionNote.objects.create(
                case       = case,
                author     = request.user,
                staff_role = SubmissionNote.StaffRole.REGISTRAR,
                note       = data['note'],
                action     = note_action,
            )
            case.transition_to(new_status, actor=request.user, note=data['note'])

        from apps.notifications.tasks import notify_case_status_changed
        notify_case_status_changed.delay(str(case.id))

        return Response(CaseDetailSerializer(case).data)


class CaseResubmitView(APIView):
    """POST /cases/<id>/resubmit/ — Lawyer resubmits after rejection."""
    permission_classes = [IsLawyer]

    def post(self, request, id):
        case = get_object_or_404(
            Case, id=id, submitted_by__user=request.user,
            status=CaseStatus.REJECTED,
        )
        with transaction.atomic():
            case.transition_to(CaseStatus.RESUBMITTED, actor=request.user)
            # Then immediately move to PENDING_ACCOUNTS
            case.transition_to(CaseStatus.PENDING_ACCOUNTS, actor=request.user)

        from apps.notifications.tasks import notify_case_resubmitted
        notify_case_resubmitted.delay(str(case.id))

        return Response(CaseDetailSerializer(case).data)
