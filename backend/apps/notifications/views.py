from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Notifications"],
        summary="List current user's notifications",
        parameters=[
            OpenApiParameter("is_read", bool, OpenApiParameter.QUERY),
            OpenApiParameter("type", str, OpenApiParameter.QUERY),
        ],
    ),
)
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()

        queryset = Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            normalized = is_read.strip().lower()
            if normalized in {"true", "1", "yes"}:
                queryset = queryset.filter(is_read=True)
            elif normalized in {"false", "0", "no"}:
                queryset = queryset.filter(is_read=False)

        notification_type = self.request.query_params.get("type")
        if notification_type:
            queryset = queryset.filter(type=notification_type)

        return queryset

    @extend_schema(
        tags=["Notifications"],
        summary="Mark notification as read",
        request=None,
        responses=NotificationSerializer,
    )
    @action(detail=True, methods=["post"])
    def read(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @extend_schema(
        tags=["Notifications"],
        summary="Mark all notifications as read",
        request=None,
        responses=inline_serializer(
            name="NotificationsReadAllResponse",
            fields={"updated_count": serializers.IntegerField()},
        ),
        examples=[
            OpenApiExample(
                "Read all response",
                value={"updated_count": 3},
                response_only=True,
            ),
        ],
    )
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request, *args, **kwargs):
        read_at = timezone.now()
        updated_count = (
            self.get_queryset()
            .filter(is_read=False)
            .update(is_read=True, read_at=read_at, updated_at=read_at)
        )
        return Response({"updated_count": updated_count})
