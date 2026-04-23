from rest_framework import serializers
from .models import Document, ALLOWED_MIME_TYPES


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)
    file_url         = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = [
            'id', 'category', 'description', 'filename', 'mime_type',
            'file_size', 'sha256_hash', 'uploaded_by_name', 'uploaded_at',
            'is_signed', 'signed_at', 'file_url', 'is_active',
        ]
        read_only_fields = [
            'id', 'filename', 'mime_type', 'file_size', 'sha256_hash',
            'uploaded_at', 'is_signed', 'signed_at', 'file_url',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model  = Document
        fields = ['file', 'category', 'description']

    def validate_file(self, value):
        # MIME type check
        mime = getattr(value, 'content_type', '')
        if mime not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                f'File type "{mime}" is not allowed. '
                f'Accepted types: PDF, JPEG, PNG, TIFF, DOC, DOCX.'
            )
        # 50MB limit
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError('File size must not exceed 50MB.')
        return value

    def create(self, validated_data):
        file_obj  = validated_data['file']
        sha256    = Document.compute_hash(file_obj)
        case      = self.context['case']
        uploader  = self.context['request'].user
        return Document.objects.create(
            case        = case,
            file        = file_obj,
            filename    = file_obj.name,
            mime_type   = getattr(file_obj, 'content_type', 'application/octet-stream'),
            file_size   = file_obj.size,
            sha256_hash = sha256,
            uploaded_by = uploader,
            category    = validated_data.get('category', 'other'),
            description = validated_data.get('description', ''),
        )
