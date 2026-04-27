from rest_framework import serializers
from .models import Case, CaseForm, CourtForm, SubmissionNote, CaseStatus


class CourtFormSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CourtForm
        fields = ['id', 'court', 'case_type', 'name', 'description', 'fee_amount']


class CaseFormSerializer(serializers.ModelSerializer):
    form = CourtFormSerializer(read_only=True)

    class Meta:
        model  = CaseForm
        fields = ['id', 'form']


class SubmissionNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)

    class Meta:
        model  = SubmissionNote
        fields = [
            'id', 'staff_role', 'note', 'action',
            'author_name', 'author_role', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'author_name', 'author_role']


class CaseListSerializer(serializers.ModelSerializer):
    """Compact representation for queue lists."""
    submitted_by_name = serializers.CharField(source='submitted_by.user.full_name', read_only=True)
    firm_name         = serializers.CharField(source='submitted_by.firm.name', read_only=True)
    total_fee         = serializers.SerializerMethodField()
    payment_status    = serializers.SerializerMethodField()

    class Meta:
        model  = Case
        fields = [
            'id', 'case_number', 'title', 'court', 'case_type', 'status',
            'submitted_by_name', 'firm_name', 'total_fee', 'payment_status',
            'created_at', 'submitted_at',
        ]

    def get_total_fee(self, obj):
        try:
            return str(obj.payment.amount_due)
        except AttributeError:
            return None

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except AttributeError:
            return None


class CaseDetailSerializer(serializers.ModelSerializer):
    """Full representation including timeline, forms, notes."""
    submitted_by_name = serializers.CharField(source='submitted_by.user.full_name', read_only=True)
    firm_name         = serializers.CharField(source='submitted_by.firm.name', read_only=True)
    selected_forms    = CaseFormSerializer(many=True, read_only=True)
    submission_notes  = SubmissionNoteSerializer(many=True, read_only=True)
    documents         = serializers.SerializerMethodField()
    payment           = serializers.SerializerMethodField()

    class Meta:
        model  = Case
        fields = [
            'id', 'case_number', 'title', 'court', 'case_type', 'status',
            'description', 'opposing_party_name', 'relief_sought',
            'submitted_by_name', 'firm_name',
            'is_sealed',
            'selected_forms', 'submission_notes', 'documents', 'payment',
            'created_at', 'submitted_at', 'registered_at', 'updated_at',
        ]

    def get_documents(self, obj):
        from apps.documents.serializers import DocumentSerializer
        return DocumentSerializer(obj.documents.all(), many=True).data

    def get_payment(self, obj):
        from apps.payments.serializers import PaymentSerializer
        try:
            return PaymentSerializer(obj.payment).data
        except Exception:
            return None


class CaseCreateSerializer(serializers.ModelSerializer):
    form_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True,
        help_text='List of CourtForm IDs to attach to this case',
    )
    # Read-only fields included in the creation response
    id         = serializers.UUIDField(read_only=True)
    status     = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model  = Case
        fields = [
            'id', 'title', 'court', 'case_type', 'description',
            'opposing_party_name', 'relief_sought', 'form_ids',
            'status', 'created_at',
        ]

    def validate_form_ids(self, value):
        if not value:
            raise serializers.ValidationError('At least one court form must be selected.')
        forms = CourtForm.objects.filter(id__in=value, is_active=True)
        if forms.count() != len(value):
            raise serializers.ValidationError('One or more form IDs are invalid or inactive.')
        return value

    def validate(self, data):
        # Ensure all selected forms are for the chosen court
        form_ids = data.get('form_ids', [])
        court    = data.get('court')
        if form_ids and court:
            mismatched = CourtForm.objects.filter(
                id__in=form_ids, is_active=True
            ).exclude(court=court)
            if mismatched.exists():
                raise serializers.ValidationError(
                    {'form_ids': 'All selected forms must belong to the chosen court tier.'}
                )
        return data

    def create(self, validated_data):
        form_ids = validated_data.pop('form_ids')
        lawyer   = self.context['request'].user.lawyer_profile
        case     = Case.objects.create(submitted_by=lawyer, **validated_data)
        forms    = CourtForm.objects.filter(id__in=form_ids)
        CaseForm.objects.bulk_create([CaseForm(case=case, form=f) for f in forms])
        return case


class AccountsReviewSerializer(serializers.Serializer):
    """Payload Accounts staff sends when forwarding a case."""
    note   = serializers.CharField(min_length=10)
    action = serializers.ChoiceField(choices=['forward', 'flag'])


class RegistrarReviewSerializer(serializers.Serializer):
    """Payload Registrar sends when registering or rejecting."""
    note   = serializers.CharField(min_length=10)
    action = serializers.ChoiceField(choices=['register', 'reject'])
