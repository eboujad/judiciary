from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.users.models import UserRole
from core.permissions import IsSystemAdmin, IsLawyer
from .models import LawFirm, Lawyer, FirmStatus
from .serializers import (
    LawFirmSerializer, LawFirmCreateSerializer,
    LawyerSerializer, LawyerCreateSerializer,
)


class FirmListCreateView(generics.ListCreateAPIView):
    """
    GET  /firms/          — System admin: list all firms
    POST /firms/          — System admin: register new firm + admin user
    """
    queryset         = LawFirm.objects.all().order_by('-created_at')
    permission_classes = [IsSystemAdmin]

    def get_serializer_class(self):
        return LawFirmCreateSerializer if self.request.method == 'POST' else LawFirmSerializer


class FirmDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /firms/<id>/"""
    queryset           = LawFirm.objects.all()
    serializer_class   = LawFirmSerializer
    permission_classes = [IsSystemAdmin]
    lookup_field       = 'id'


class FirmApproveView(APIView):
    """POST /firms/<id>/approve/ — Admin approves firm registration."""
    permission_classes = [IsSystemAdmin]

    def post(self, request, id):
        firm = get_object_or_404(LawFirm, id=id)
        if firm.status != FirmStatus.PENDING:
            return Response(
                {'detail': f'Firm is already {firm.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.utils import timezone
        firm.status      = FirmStatus.ACTIVE
        firm.approved_at = timezone.now()
        firm.approved_by = request.user
        firm.save(update_fields=['status', 'approved_at', 'approved_by'])
        return Response(LawFirmSerializer(firm).data)


class FirmLawyersView(generics.ListCreateAPIView):
    """
    GET  /firms/<firm_id>/lawyers/ — list lawyers in a firm
    POST /firms/<firm_id>/lawyers/ — firm admin creates a new lawyer sub-account
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_firm(self):
        if not hasattr(self, '_firm'):
            self._firm = get_object_or_404(LawFirm, id=self.kwargs['firm_id'])
        return self._firm

    def get_queryset(self):
        return Lawyer.objects.filter(firm=self.get_firm()).select_related('user')

    def get_serializer_class(self):
        return LawyerCreateSerializer if self.request.method == 'POST' else LawyerSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['firm'] = self.get_firm()
        return ctx

    def check_permissions(self, request):
        super().check_permissions(request)
        firm = self.get_firm()
        # Firm admin can manage their own lawyers; system admin can manage any
        if request.user.role not in [UserRole.SYSTEM_ADMIN]:
            if not hasattr(request.user, 'managed_firm') or request.user.managed_firm != firm:
                self.permission_denied(request, message='You do not manage this firm.')


class MyFirmView(generics.RetrieveAPIView):
    """GET /firms/mine/ — Lawyer sees their own firm."""
    serializer_class   = LawFirmSerializer
    permission_classes = [IsLawyer]

    def get_object(self):
        return get_object_or_404(LawFirm, lawyers__user=self.request.user)
