from rest_framework.permissions import BasePermission


def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.is_admin_role)
    )


def is_event_organizer(user, event):
    return bool(
        user
        and user.is_authenticated
        and user.is_organizer
        and event.organizer_id == user.id
    )


class IsReviewOwnerOrEventOrganizerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin_user(user):
            return True

        if not user or not user.is_authenticated:
            return False

        if obj.user_id == user.id:
            return True

        return is_event_organizer(user, obj.event)


class CanCreateReview(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
