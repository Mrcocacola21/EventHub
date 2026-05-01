from rest_framework.permissions import BasePermission

from apps.events.models import Event


class IsEventOrganizerOrAdminForTicketType(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_admin_role:
            return True

        if not user.is_organizer:
            return False

        if getattr(view, "action", None) == "create":
            event_id = view.kwargs.get("event_id")
            return Event.objects.filter(
                id=event_id,
                organizer=user,
            ).exists()

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.is_admin_role:
            return True

        return user.is_organizer and obj.event.organizer_id == user.id
