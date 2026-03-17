from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsAdminOrOwner(BasePermission):
    """Allow access only to users with role admin or owner."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.OWNER)
        )


class IsOwner(BasePermission):
    """Allow access only to users with role owner."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.OWNER
        )
