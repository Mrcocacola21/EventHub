from rest_framework.permissions import BasePermission


class IsBookingOwnerOrAdminOrEventOrganizer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.is_admin_role:
            return True

        if obj.user_id == user.id:
            return True

        event = obj.ticket_type.event
        return user.is_organizer and event.organizer_id == user.id


class CanUseBookingTicket(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.is_superuser or user.is_admin_role:
            return True

        event = obj.ticket_type.event
        return user.is_organizer and event.organizer_id == user.id
