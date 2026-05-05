from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.cache import EventCacheService
from apps.events.models import Event

from .models import Review
from .permissions import (
    IsReviewOwnerOrEventOrganizerOrAdmin,
    is_admin_user,
    is_event_organizer,
)
from .serializers import (
    ReviewCreateSerializer,
    ReviewSerializer,
    ReviewUpdateSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Reviews"],
        summary="List event reviews",
        responses=ReviewSerializer(many=True),
    ),
    post=extend_schema(
        tags=["Reviews"],
        summary="Create event review",
        description=(
            "Rating must be 1-5. User must have a paid booking for the event. "
            "Only one review per user/event is allowed."
        ),
        request=ReviewCreateSerializer,
        responses=ReviewSerializer,
        examples=[
            OpenApiExample(
                "Create review",
                value={"rating": 5, "comment": "Great event!"},
                request_only=True,
            ),
        ],
    ),
)
class EventReviewListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_event(self):
        if getattr(self, "swagger_fake_view", False):
            return None
        if not hasattr(self, "_event"):
            self._event = get_object_or_404(Event, id=self.kwargs["event_id"])
        return self._event

    def get_queryset(self):
        event = self.get_event()
        if event is None:
            return Review.objects.none()
        queryset = Review.objects.select_related(
            "user",
            "event",
            "event__organizer",
            "event__category",
        ).filter(event=event)
        user = self.request.user
        if is_admin_user(user) or is_event_organizer(user, event):
            return queryset
        return queryset.filter(is_published=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["event"] = self.get_event()
        return context

    def perform_create(self, serializer):
        review = serializer.save()
        AuditService.log_action(
            action=AuditLog.Action.REVIEW_CREATED,
            entity_type="Review",
            entity_id=review.id,
            request=self.request,
            metadata=_review_metadata(review),
        )

        from apps.notifications.services import NotificationService

        transaction.on_commit(lambda: NotificationService.notify_review_created(review))
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self.created_review = review

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            ReviewSerializer(self.created_review).data,
            status=response.status_code,
            headers=response.headers,
        )


@extend_schema_view(
    get=extend_schema(tags=["Reviews"], summary="Get review"),
    patch=extend_schema(
        tags=["Reviews"],
        summary="Update or moderate review",
        description=(
            "Owners can update rating/comment. Admins and event organizers can "
            "moderate is_published."
        ),
    ),
    delete=extend_schema(tags=["Reviews"], summary="Delete review"),
)
class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ReviewUpdateSerializer
        return ReviewSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsReviewOwnerOrEventOrganizerOrAdmin()]

    def get_queryset(self):
        queryset = Review.objects.select_related(
            "user",
            "event",
            "event__organizer",
            "event__category",
        )
        user = self.request.user
        if is_admin_user(user):
            return queryset
        if user and user.is_authenticated:
            visibility_filter = Q(is_published=True) | Q(user=user)
            if getattr(user, "is_organizer", False):
                visibility_filter |= Q(event__organizer=user)
            return queryset.filter(
                visibility_filter
            )
        return queryset.filter(is_published=True)

    def patch(self, request, *args, **kwargs):
        review = self.get_object()
        self.check_object_permissions(request, review)
        data = self._filtered_update_data(review)
        serializer = self.get_serializer(review, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        old_published = review.is_published
        updated_review = serializer.save()

        action = AuditLog.Action.REVIEW_UPDATED
        if old_published is False and updated_review.is_published is True:
            action = AuditLog.Action.REVIEW_PUBLISHED
        elif old_published is True and updated_review.is_published is False:
            action = AuditLog.Action.REVIEW_UNPUBLISHED

        AuditService.log_action(
            action=action,
            entity_type="Review",
            entity_id=updated_review.id,
            request=request,
            metadata=_review_metadata(updated_review),
        )
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        return Response(ReviewSerializer(updated_review).data)

    def perform_destroy(self, instance):
        metadata = _review_metadata(instance)
        review_id = instance.id
        instance.delete()
        AuditService.log_action(
            action=AuditLog.Action.REVIEW_DELETED,
            entity_type="Review",
            entity_id=review_id,
            request=self.request,
            metadata=metadata,
        )
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def _filtered_update_data(self, review):
        user = self.request.user
        data = self.request.data.copy()
        for field_name in ("user", "event"):
            data.pop(field_name, None)

        if is_admin_user(user):
            return data

        if is_event_organizer(user, review.event) and review.user_id != user.id:
            return {
                "is_published": data["is_published"],
            } if "is_published" in data else {}

        data.pop("is_published", None)
        return data


def _review_metadata(review):
    return {
        "review_id": review.id,
        "event_id": review.event_id,
        "rating": review.rating,
        "user_id": review.user_id,
        "is_published": review.is_published,
    }
