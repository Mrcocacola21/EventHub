from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.events.models import Event

from .models import TicketType
from .permissions import IsEventOrganizerOrAdminForTicketType
from .serializers import TicketTypeSerializer


class TicketTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TicketTypeSerializer
    permission_classes = (AllowAny,)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_event(self):
        if not hasattr(self, "_event"):
            self._event = get_object_or_404(
                Event.objects.select_related("organizer", "category"),
                id=self.kwargs["event_id"],
            )
        return self._event

    def get_queryset(self):
        queryset = TicketType.objects.select_related(
            "event",
            "event__organizer",
            "event__category",
        )

        if self.action in ("partial_update", "update", "destroy"):
            return queryset

        event_id = self.kwargs.get("event_id")
        if event_id is not None:
            queryset = queryset.filter(event_id=event_id)

        user = self.request.user
        public_filter = Q(
            is_active=True,
            event__status=Event.Status.PUBLISHED,
            event__is_published=True,
        )

        if user and user.is_authenticated:
            if user.is_superuser or user.is_admin_role:
                return queryset

            if user.is_organizer:
                return queryset.filter(public_filter | Q(event__organizer=user))

        return queryset.filter(public_filter)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsEventOrganizerOrAdminForTicketType()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.kwargs.get("event_id") is not None:
            context["event"] = self.get_event()
        return context

    def destroy(self, request, *args, **kwargs):
        ticket_type = self.get_object()
        if ticket_type.sold_count > 0:
            return Response(
                {
                    "detail": (
                        "Ticket type cannot be deleted after tickets have "
                        "been sold."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)
