from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.serializers import UserShortSerializer

from .models import Event, EventCategory


class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class EventSerializer(serializers.ModelSerializer):
    category_detail = EventCategorySerializer(source="category", read_only=True)
    organizer = serializers.PrimaryKeyRelatedField(read_only=True)
    organizer_detail = UserShortSerializer(source="organizer", read_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "category",
            "category_detail",
            "location",
            "start_datetime",
            "end_datetime",
            "organizer",
            "organizer_detail",
            "max_participants",
            "status",
            "is_published",
            "cover_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organizer",
            "organizer_detail",
            "status",
            "is_published",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if self.instance is None:
            if not user or not user.is_authenticated:
                raise serializers.ValidationError(
                    {"organizer": "Authentication is required to create events."}
                )
            organizer = user
        else:
            organizer = self.instance.organizer

        event = self.instance or Event()
        event.start_datetime = attrs.get(
            "start_datetime",
            getattr(self.instance, "start_datetime", None),
        )
        event.end_datetime = attrs.get(
            "end_datetime",
            getattr(self.instance, "end_datetime", None),
        )
        event.max_participants = attrs.get(
            "max_participants",
            getattr(self.instance, "max_participants", None),
        )
        event.organizer = organizer

        try:
            event.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data.pop("organizer", None)
        validated_data.pop("status", None)
        validated_data.pop("is_published", None)

        return Event.objects.create(organizer=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("organizer", None)
        validated_data.pop("status", None)
        validated_data.pop("is_published", None)
        return super().update(instance, validated_data)


class EventListSerializer(serializers.ModelSerializer):
    category_detail = EventCategorySerializer(source="category", read_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "slug",
            "category_detail",
            "location",
            "start_datetime",
            "end_datetime",
            "status",
            "is_published",
            "cover_image",
        )
