from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display   = ['filename', 'case', 'category', 'mime_type', 'file_size', 'uploaded_by', 'uploaded_at', 'is_active']
    list_filter    = ['category', 'mime_type', 'is_active', 'is_signed']
    search_fields  = ['filename', 'case__case_number', 'case__title']
    readonly_fields = ['id', 'sha256_hash', 'uploaded_at', 'file_size', 'mime_type']
    actions        = ['verify_integrity']

    def verify_integrity(self, request, queryset):
        tampered = []
        for doc in queryset:
            if not doc.verify_integrity():
                tampered.append(doc.filename)
        if tampered:
            self.message_user(request, f'TAMPERED: {", ".join(tampered)}', level='ERROR')
        else:
            self.message_user(request, f'All {queryset.count()} document(s) intact.')
    verify_integrity.short_description = 'Verify SHA-256 integrity'
