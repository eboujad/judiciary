from django.contrib import admin
from .models import Payment, PaymentReceipt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ['case', 'amount_due', 'amount_paid', 'status', 'musu_reference', 'confirmed_at']
    list_filter   = ['status', 'is_waived']
    search_fields = ['musu_reference', 'musu_transaction_id', 'case__case_number', 'payer_phone']
    readonly_fields = ['id', 'created_at', 'initiated_at', 'confirmed_at', 'musu_raw_payload']


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display  = ['receipt_number', 'payment', 'issued_at']
    readonly_fields = ['id', 'issued_at']
