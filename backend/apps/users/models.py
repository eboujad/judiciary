"""
Custom User model with judiciary role system.

Design decisions:
- Single User table with a `role` field rather than multiple proxy models.
  This keeps auth simple and avoids JOIN complexity for permission checks.
- Role-specific profile data (LawFirm, judge specialisation, etc.) lives in
  related tables so the User model stays lean.
- Phone number stored separately from email to support SMS-first workflows.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    SYSTEM_ADMIN    = 'system_admin',    'System Administrator'
    ACCOUNTS_DEPT   = 'accounts_dept',   'Accounts Department'
    REGISTRAR       = 'registrar',       'Registrar'
    CHIEF_JUSTICE   = 'chief_justice',   'Chief Justice / President of Appeal'
    JUDGE           = 'judge',           'Judge'
    JUDGE_CLERK     = 'judge_clerk',     'Judge Clerk'
    LAWYER          = 'lawyer',          'Lawyer / Legal Counsel'
    PUBLIC_USER     = 'public_user',     'Public User / Citizen'
    RESPONDENT      = 'respondent',      'Opposing Party / Respondent'
    WITNESS         = 'witness',         'Witness / Expert Witness'
    INTERPRETER     = 'interpreter',     'Court Interpreter'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.SYSTEM_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email       = models.EmailField(unique=True)
    phone       = models.CharField(max_length=20, blank=True)  # E.164 format: +220XXXXXXX
    first_name  = models.CharField(max_length=100)
    last_name   = models.CharField(max_length=100)
    role        = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.PUBLIC_USER)

    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)  # can access /admin/
    is_verified = models.BooleanField(default=False)  # email/ID verified

    # 2FA — OTP via SMS or TOTP app
    two_fa_enabled  = models.BooleanField(default=False)
    two_fa_method   = models.CharField(
        max_length=10,
        choices=[('sms', 'SMS'), ('totp', 'Authenticator App')],
        blank=True,
    )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.role})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_lawyer_role(self):
        return self.role == UserRole.LAWYER

    @property
    def is_internal_staff(self):
        return self.role in [
            UserRole.ACCOUNTS_DEPT,
            UserRole.REGISTRAR,
            UserRole.CHIEF_JUSTICE,
            UserRole.JUDGE,
            UserRole.JUDGE_CLERK,
            UserRole.SYSTEM_ADMIN,
        ]


class PasswordResetToken(models.Model):
    """Short-lived token for password reset flow."""
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token       = models.UUIDField(default=uuid.uuid4, unique=True)
    used        = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    class Meta:
        db_table = 'password_reset_tokens'
