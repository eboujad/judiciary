from rest_framework import serializers
from .models import Payment, PaymentReceipt


class PaymentSerializer(serializers.ModelSerializer):
    has_discrepancy = serializers.ReadOnlyField()
    receipt_number  = serializers.SerializerMethodField()

    class Meta:
        model  = Payment
        fields = [
            'id', 'amount_due', 'amount_paid', 'status',
            'musu_reference', 'musu_transaction_id', 'payer_phone',
            'is_waived', 'has_discrepancy',
            'created_at', 'initiated_at', 'confirmed_at',
            'receipt_number',
        ]
        read_only_fields = fields

    def get_receipt_number(self, obj):
        try:
            return obj.receipt.receipt_number
        except Exception:
            return None


class PaymentInitiateSerializer(serializers.Serializer):
    payer_phone = serializers.CharField(
        max_length=20,
        help_text='Mobile number to charge (E.164: +220XXXXXXX)',
    )

    def validate_payer_phone(self, value):
        import re
        if not re.match(r'^\+\d{7,15}$', value):
            raise serializers.ValidationError(
                'Phone must be in E.164 format, e.g. +2207001234'
            )
        return value


class MockConfirmSerializer(serializers.Serializer):
    """Dev-only: manually confirm a mock payment by MUSU reference or case_id."""
    reference = serializers.CharField(required=False)
    case_id   = serializers.UUIDField(required=False)

    def validate(self, data):
        if not data.get('reference') and not data.get('case_id'):
            raise serializers.ValidationError(
                'Provide either "reference" (MUSU ref) or "case_id".'
            )
        return data
