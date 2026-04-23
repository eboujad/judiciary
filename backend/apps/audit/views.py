from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from core.permissions import IsSystemAdmin, IsInternalStaff
from .models import AuditLog


class AuditLogSerializer:
    pass  # defined inline below


from rest_framework import serializers

class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)

    class Meta:
        model  = AuditLog
        fields = [
            'id', 'actor_email', 'actor_role', 'action',
            'content_type', 'object_id', 'note', 'severity',
            'ip_address', 'created_at',
        ]


class AuditLogListView(generics.ListAPIView):
    """
    GET /audit/logs/
    Staff: see logs for cases they can access.
    Admin: full log.
    Supports filtering by content_type, object_id, severity, action.
    """
    serializer_class   = AuditLogSerializer
    permission_classes = [IsInternalStaff]
    filter_backends    = [DjangoFilterBackend, OrderingFilter]
    filterset_fields   = ['content_type', 'object_id', 'severity', 'action', 'actor_role']
    ordering_fields    = ['created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        return AuditLog.objects.select_related('actor').all()


class CaseAuditLogView(generics.ListAPIView):
    """GET /audit/cases/<case_id>/ — full timeline for a specific case."""
    serializer_class   = AuditLogSerializer
    permission_classes = [IsInternalStaff]

    def get_queryset(self):
        case_id = self.kwargs['case_id']
        return AuditLog.objects.filter(
            content_type='case', object_id=str(case_id)
        ).select_related('actor').order_by('created_at')
