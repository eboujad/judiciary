from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    UserSerializer, UserCreateSerializer,
    ChangePasswordSerializer, JudiciaryTokenSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    """POST /auth/login/ — returns access + refresh tokens with user profile."""
    serializer_class = JudiciaryTokenSerializer


class LogoutView(APIView):
    """POST /auth/logout/ — blacklists the refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'detail': 'Successfully logged out.'})
        except Exception:
            return Response(
                {'detail': 'Invalid or missing token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PublicRegisterView(generics.CreateAPIView):
    """POST /auth/register/ — self-registration for public users only."""
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        from apps.users.models import UserRole
        serializer.save(role=UserRole.PUBLIC_USER)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /auth/me/ — current user profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST /auth/change-password/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': 'Incorrect password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated successfully.'})


class AdminUserListView(generics.ListCreateAPIView):
    """GET/POST /auth/users/ — System admin: list and create staff users."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from core.permissions import IsSystemAdmin
        # Only admins can list all users; enforce in permission_classes
        return User.objects.all().order_by('-created_at')

    def get_permissions(self):
        from core.permissions import IsSystemAdmin
        return [IsSystemAdmin()]

    def perform_create(self, serializer):
        from apps.users.models import UserRole
        from rest_framework.exceptions import ValidationError
        STAFF_ROLES = {
            UserRole.ACCOUNTS_DEPT, UserRole.REGISTRAR, UserRole.CHIEF_JUSTICE,
            UserRole.JUDGE, UserRole.JUDGE_CLERK, UserRole.INTERPRETER,
        }
        role = self.request.data.get('role', '')
        if role not in STAFF_ROLES:
            raise ValidationError({'role': f'Invalid or unpermitted role: "{role}"'})
        serializer.save(role=role)
