from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.events.models import Event
from apps.users.serializers import UserShortSerializer

from .models import Review


class ReviewEventDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ("id", "title", "slug")


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_detail = UserShortSerializer(source="user", read_only=True)
    event = serializers.PrimaryKeyRelatedField(read_only=True)
    event_detail = ReviewEventDetailSerializer(source="event", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "user",
            "user_detail",
            "event",
            "event_detail",
            "rating",
            "comment",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "user_detail",
            "event",
            "event_detail",
            "is_published",
            "created_at",
            "updated_at",
        )


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("rating", "comment")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context["request"]
        event = self.context["event"]
        review = Review(
            user=request.user,
            event=event,
            rating=attrs.get("rating"),
            comment=attrs.get("comment", ""),
        )

        try:
            review.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs

    def create(self, validated_data):
        return Review.objects.create(
            user=self.context["request"].user,
            event=self.context["event"],
            **validated_data,
        )


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ("rating", "comment", "is_published")
        extra_kwargs = {
            "rating": {"required": False},
            "comment": {"required": False},
            "is_published": {"required": False},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        review = self.instance
        updated_review = Review(
            id=review.id,
            user=review.user,
            event=review.event,
            rating=attrs.get("rating", review.rating),
            comment=attrs.get("comment", review.comment),
            is_published=attrs.get("is_published", review.is_published),
        )
        updated_review.created_at = review.created_at

        try:
            updated_review.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs
