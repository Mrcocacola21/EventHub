from rest_framework.permissions import BasePermission


def is_organizer_or_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_organizer or user.is_admin_role or user.is_superuser)
    )


class IsOrganizerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_organizer_or_admin(request.user)


class IsEventOrganizerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.is_admin_role:
            return True

        return user.is_organizer and obj.organizer_id == user.id
