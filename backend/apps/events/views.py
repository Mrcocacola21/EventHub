from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Event, EventCategory
from .permissions import IsEventOrganizerOrAdmin, IsOrganizerOrAdmin
from .serializers import (
    EventCategorySerializer,
    EventListSerializer,
    EventSerializer,
)


class EventCategoryViewSet(viewsets.ModelViewSet):
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name",)
    ordering = ("name",)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsOrganizerOrAdmin()]


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ("category", "status", "is_published", "location")
    search_fields = ("title", "description", "location")
    ordering_fields = ("start_datetime", "end_datetime", "created_at", "title")
    ordering = ("start_datetime",)

    def get_queryset(self):
        queryset = Event.objects.select_related("category", "organizer")
        user = self.request.user
        published_filter = Q(status=Event.Status.PUBLISHED, is_published=True)

        if user and user.is_authenticated:
            if user.is_superuser or user.is_admin_role:
                return queryset

            if user.is_organizer:
                return queryset.filter(published_filter | Q(organizer=user))

        return queryset.filter(published_filter)

    def get_serializer_class(self):
        if self.action == "list":
            return EventListSerializer
        return EventSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        if self.action == "create":
            return [IsOrganizerOrAdmin()]
        return [IsEventOrganizerOrAdmin()]

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        event = self.get_object()
        event.publish()
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        event = self.get_object()
        event.cancel()
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finish(self, request, *args, **kwargs):
        event = self.get_object()
        event.finish()
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)
