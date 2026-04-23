"""
Role-based permission classes for the Judiciary E-Filing API.
Every view explicitly declares which roles can access it.
"""
from rest_framework.permissions import BasePermission
from apps.users.models import UserRole


class HasRole(BasePermission):
    """Base class — subclasses declare `allowed_roles`."""
    allowed_roles: list[str] = []

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.allowed_roles
        )


class IsSystemAdmin(HasRole):
    allowed_roles = [UserRole.SYSTEM_ADMIN]


class IsAccountsDept(HasRole):
    allowed_roles = [UserRole.ACCOUNTS_DEPT, UserRole.SYSTEM_ADMIN]


class IsRegistrar(HasRole):
    allowed_roles = [UserRole.REGISTRAR, UserRole.SYSTEM_ADMIN]


class IsChiefJustice(HasRole):
    allowed_roles = [UserRole.CHIEF_JUSTICE, UserRole.SYSTEM_ADMIN]


class IsJudge(HasRole):
    allowed_roles = [UserRole.JUDGE, UserRole.CHIEF_JUSTICE, UserRole.SYSTEM_ADMIN]


class IsJudgeClerk(HasRole):
    allowed_roles = [UserRole.JUDGE_CLERK, UserRole.SYSTEM_ADMIN]


class IsLawyer(HasRole):
    allowed_roles = [UserRole.LAWYER, UserRole.SYSTEM_ADMIN]


class IsPublicUser(HasRole):
    allowed_roles = [UserRole.PUBLIC_USER, UserRole.LAWYER, UserRole.SYSTEM_ADMIN]


class IsInternalStaff(HasRole):
    """Accounts, Registrar, Chief Justice, Admin."""
    allowed_roles = [
        UserRole.ACCOUNTS_DEPT,
        UserRole.REGISTRAR,
        UserRole.CHIEF_JUSTICE,
        UserRole.JUDGE,
        UserRole.JUDGE_CLERK,
        UserRole.SYSTEM_ADMIN,
    ]


class IsLawyerOrInternal(BasePermission):
    """Lawyers can access their own cases; staff can access all."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in [
            UserRole.LAWYER,
            UserRole.ACCOUNTS_DEPT,
            UserRole.REGISTRAR,
            UserRole.CHIEF_JUSTICE,
            UserRole.JUDGE,
            UserRole.JUDGE_CLERK,
            UserRole.SYSTEM_ADMIN,
        ]

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.LAWYER:
            # Lawyers can only see cases they submitted (or their firm submitted)
            from apps.cases.models import Case
            if isinstance(obj, Case):
                return obj.submitted_by.firm == request.user.lawyer_profile.firm
        return True
