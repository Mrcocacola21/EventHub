from django.db import transaction
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.audit.services import AuditService

from .cache import EventCacheService
from .models import Event, EventCategory
from .permissions import IsEventOrganizerOrAdmin, IsOrganizerOrAdmin
from .serializers import (
    EventCategorySerializer,
    EventListSerializer,
    PopularEventSerializer,
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
        if self.action in ("list", "retrieve", "popular"):
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
        if self.action == "popular":
            return PopularEventSerializer
        if self.action == "list":
            return EventListSerializer
        return EventSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "popular"):
            return [AllowAny()]
        if self.action == "create":
            return [IsOrganizerOrAdmin()]
        return [IsEventOrganizerOrAdmin()]

    def perform_create(self, serializer):
        event = serializer.save()
        AuditService.log_event_created(event, request=self.request)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def perform_update(self, serializer):
        event = serializer.save()
        AuditService.log_event_updated(event, request=self.request)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def list(self, request, *args, **kwargs):
        if self._can_use_public_cache(request):
            cache_key = EventCacheService.make_events_list_key(request)
            cached_data = EventCacheService.get_cached_response(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            response = super().list(request, *args, **kwargs)
            EventCacheService.set_cached_response(
                cache_key,
                response.data,
                EventCacheService.EVENTS_LIST_CACHE_TTL,
            )
            return response

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        event = self.get_object()
        if self._can_use_public_cache(request) and self._is_public_event(event):
            cache_key = EventCacheService.make_event_detail_key(event.id)
            cached_data = EventCacheService.get_cached_response(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            serializer = self.get_serializer(event)
            EventCacheService.set_cached_response(
                cache_key,
                serializer.data,
                EventCacheService.EVENT_DETAIL_CACHE_TTL,
            )
            return Response(serializer.data)

        serializer = self.get_serializer(event)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def popular(self, request, *args, **kwargs):
        limit = self._get_popular_limit(request)
        cache_key = EventCacheService.make_popular_events_key(limit)
        cached_data = EventCacheService.get_cached_response(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        queryset = (
            Event.objects.select_related("category", "organizer")
            .filter(status=Event.Status.PUBLISHED, is_published=True)
            .annotate(booking_count=Count("ticket_types__bookings"))
            .order_by("-booking_count", "start_datetime", "id")[:limit]
        )
        serializer = self.get_serializer(queryset, many=True)
        EventCacheService.set_cached_response(
            cache_key,
            serializer.data,
            EventCacheService.POPULAR_EVENTS_CACHE_TTL,
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        event = self.get_object()
        event.publish()
        AuditService.log_event_published(event, request=request)
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        event = self.get_object()
        previous_status = event.status
        event.cancel()
        AuditService.log_event_canceled(event, request=request)
        if previous_status != Event.Status.CANCELED:
            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_event_canceled(event),
            )
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finish(self, request, *args, **kwargs):
        event = self.get_object()
        event.finish()
        AuditService.log_event_finished(event, request=request)
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        serializer = self.get_serializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _can_use_public_cache(request):
        if request.method != "GET":
            return False

        user = request.user
        if not user or not user.is_authenticated:
            return True

        return not (user.is_superuser or user.is_admin_role or user.is_organizer)

    @staticmethod
    def _is_public_event(event):
        return event.status == Event.Status.PUBLISHED and event.is_published

    @staticmethod
    def _get_popular_limit(request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        return max(1, min(limit, 50))
