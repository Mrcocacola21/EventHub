from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "message",
            "is_read",
            "read_at",
            "entity_type",
            "entity_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
