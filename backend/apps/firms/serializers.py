from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import LawFirm, Lawyer

User = get_user_model()


class LawFirmSerializer(serializers.ModelSerializer):
    lawyer_count = serializers.ReadOnlyField()
    admin_email  = serializers.SerializerMethodField()

    class Meta:
        model  = LawFirm
        fields = [
            'id', 'name', 'bar_number', 'address', 'phone', 'email',
            'status', 'lawyer_count', 'admin_email', 'created_at', 'approved_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'approved_at']

    def get_admin_email(self, obj):
        return obj.admin_user.email if obj.admin_user else None


class LawFirmCreateSerializer(serializers.ModelSerializer):
    """Used by System Admin to register a new law firm."""
    admin_email      = serializers.EmailField(write_only=True)
    admin_first_name = serializers.CharField(write_only=True)
    admin_last_name  = serializers.CharField(write_only=True)
    admin_phone      = serializers.CharField(write_only=True, required=False, default='')
    admin_password   = serializers.CharField(write_only=True)

    class Meta:
        model  = LawFirm
        fields = [
            'name', 'bar_number', 'address', 'phone', 'email',
            'admin_email', 'admin_first_name', 'admin_last_name',
            'admin_phone', 'admin_password',
        ]

    def validate_bar_number(self, value):
        if LawFirm.objects.filter(bar_number=value).exists():
            raise serializers.ValidationError('A firm with this bar number already exists.')
        return value

    def create(self, validated_data):
        from apps.users.models import UserRole
        admin_data = {
            'email':      validated_data.pop('admin_email'),
            'first_name': validated_data.pop('admin_first_name'),
            'last_name':  validated_data.pop('admin_last_name'),
            'phone':      validated_data.pop('admin_phone'),
            'password':   validated_data.pop('admin_password'),
            'role':       UserRole.LAWYER,
        }
        admin_user = User.objects.create_user(**admin_data)
        firm = LawFirm.objects.create(admin_user=admin_user, **validated_data)
        return firm


class LawyerSerializer(serializers.ModelSerializer):
    email      = serializers.EmailField(source='user.email', read_only=True)
    full_name  = serializers.CharField(source='user.full_name', read_only=True)
    phone      = serializers.CharField(source='user.phone', read_only=True)
    firm_name  = serializers.CharField(source='firm.name', read_only=True)

    class Meta:
        model  = Lawyer
        fields = [
            'id', 'email', 'full_name', 'phone', 'bar_number',
            'firm_name', 'specialisation', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LawyerCreateSerializer(serializers.ModelSerializer):
    """Firm admin creates a lawyer sub-account."""
    email      = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name  = serializers.CharField(write_only=True)
    phone      = serializers.CharField(write_only=True, required=False, default='')
    password   = serializers.CharField(write_only=True)

    class Meta:
        model  = Lawyer
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'password',
            'bar_number', 'specialisation',
        ]

    def validate_bar_number(self, value):
        if Lawyer.objects.filter(bar_number=value).exists():
            raise serializers.ValidationError('A lawyer with this bar number already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def create(self, validated_data):
        from apps.users.models import UserRole
        user = User.objects.create_user(
            email=validated_data.pop('email'),
            first_name=validated_data.pop('first_name'),
            last_name=validated_data.pop('last_name'),
            phone=validated_data.pop('phone', ''),
            password=validated_data.pop('password'),
            role=UserRole.LAWYER,
        )
        firm = self.context['firm']
        return Lawyer.objects.create(user=user, firm=firm, **validated_data)
