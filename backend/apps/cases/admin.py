from django.contrib import admin
from .models import Case, CourtForm, CaseForm, SubmissionNote


class CaseFormInline(admin.TabularInline):
    model  = CaseForm
    extra  = 0
    fields = ['form']
    readonly_fields = ['form']


class SubmissionNoteInline(admin.TabularInline):
    model  = SubmissionNote
    extra  = 0
    readonly_fields = ['author', 'staff_role', 'note', 'action', 'created_at']
    can_delete = False


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display  = ['case_number', 'title', 'court', 'case_type', 'status', 'submitted_by', 'created_at']
    list_filter   = ['status', 'court', 'case_type', 'is_sealed']
    search_fields = ['case_number', 'title', 'opposing_party_name']
    readonly_fields = ['id', 'case_number', 'created_at', 'updated_at', 'submitted_at', 'registered_at']
    inlines       = [CaseFormInline, SubmissionNoteInline]
    ordering      = ['-created_at']


@admin.register(CourtForm)
class CourtFormAdmin(admin.ModelAdmin):
    list_display  = ['name', 'court', 'case_type', 'fee_amount', 'is_active']
    list_filter   = ['court', 'case_type', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['fee_amount', 'is_active']


@admin.register(SubmissionNote)
class SubmissionNoteAdmin(admin.ModelAdmin):
    list_display  = ['case', 'staff_role', 'action', 'author', 'created_at']
    list_filter   = ['staff_role', 'action']
    readonly_fields = ['id', 'created_at']
