from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
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

    @action(detail=True, methods=["post"])
    def read(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request, *args, **kwargs):
        read_at = timezone.now()
        updated_count = (
            self.get_queryset()
            .filter(is_read=False)
            .update(is_read=True, read_at=read_at, updated_at=read_at)
        )
        return Response({"updated_count": updated_count})
