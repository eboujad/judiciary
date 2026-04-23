from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from core.permissions import IsLawyerOrInternal, IsSystemAdmin
from apps.cases.models import Case, CaseStatus
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer


class DocumentUploadView(APIView):
    """
    POST /documents/cases/<case_id>/upload/
    Lawyer uploads documents to a DRAFT case.
    Computes SHA-256 on the server side — client cannot spoof it.
    """
    parser_classes     = [MultiPartParser, FormParser]
    permission_classes = [IsLawyerOrInternal]

    def post(self, request, case_id):
        case = get_object_or_404(Case, id=case_id)

        # Only allow uploads to cases that are still editable
        editable_statuses = [
            CaseStatus.DRAFT,
            CaseStatus.REJECTED,   # lawyer correcting documents
            CaseStatus.RESUBMITTED,
        ]
        if case.status not in editable_statuses:
            return Response(
                {'detail': f'Cannot upload documents to a case with status "{case.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lawyers can only upload to their own firm's cases
        if request.user.role == 'lawyer':
            if case.submitted_by.firm != request.user.lawyer_profile.firm:
                return Response(
                    {'detail': 'You do not have permission to upload to this case.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = DocumentUploadSerializer(
            data=request.data,
            context={'request': request, 'case': case},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        return Response(
            DocumentSerializer(document, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentListView(generics.ListAPIView):
    """GET /documents/cases/<case_id>/ — list all documents for a case."""
    serializer_class   = DocumentSerializer
    permission_classes = [IsLawyerOrInternal]

    def get_queryset(self):
        case = get_object_or_404(Case, id=self.kwargs['case_id'])
        return Document.objects.filter(case=case, is_active=True).order_by('uploaded_at')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


class DocumentVerifyView(APIView):
    """
    GET /documents/<doc_id>/verify/
    Re-computes SHA-256 and returns integrity status.
    Available to internal staff and system admins.
    """
    permission_classes = [IsLawyerOrInternal]

    def get(self, request, doc_id):
        document = get_object_or_404(Document, id=doc_id, is_active=True)
        intact   = document.verify_integrity()
        return Response({
            'document_id':  str(document.id),
            'filename':     document.filename,
            'stored_hash':  document.sha256_hash,
            'intact':       intact,
            'status':       'OK' if intact else 'TAMPERED',
        })


class DocumentDeleteView(APIView):
    """
    DELETE /documents/<doc_id>/
    Soft-delete only. Lawyers can remove from DRAFT cases; admins can always.
    """
    permission_classes = [IsLawyerOrInternal]

    def delete(self, request, doc_id):
        document = get_object_or_404(Document, id=doc_id, is_active=True)
        case     = document.case

        if request.user.role == 'lawyer':
            if case.status != CaseStatus.DRAFT or case.submitted_by.firm != request.user.lawyer_profile.firm:
                return Response(
                    {'detail': 'You cannot delete this document.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        document.is_active = False
        document.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)
