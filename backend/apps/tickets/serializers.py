from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.events.models import Event

from .models import TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)
    is_sales_period_active = serializers.BooleanField(read_only=True)
    is_available_for_purchase = serializers.BooleanField(read_only=True)

    class Meta:
        model = TicketType
        fields = (
            "id",
            "event",
            "name",
            "description",
            "price",
            "quantity",
            "sold_count",
            "available_quantity",
            "sales_start",
            "sales_end",
            "is_active",
            "is_sold_out",
            "is_sales_period_active",
            "is_available_for_purchase",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "event",
            "sold_count",
            "available_quantity",
            "is_sold_out",
            "is_sales_period_active",
            "is_available_for_purchase",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        event = self.context.get("event") or getattr(self.instance, "event", None)

        if not event:
            raise serializers.ValidationError({"event": "Event is required."})

        if not user or not user.is_authenticated:
            raise serializers.ValidationError(
                {"event": "Authentication is required."}
            )

        is_admin = user.is_superuser or user.is_admin_role
        is_event_organizer = user.is_organizer and event.organizer_id == user.id
        if not (is_admin or is_event_organizer):
            raise serializers.ValidationError(
                {"event": "You cannot manage ticket types for this event."}
            )

        if self.instance is None and event.status in (
            Event.Status.CANCELED,
            Event.Status.FINISHED,
        ):
            raise serializers.ValidationError(
                {
                    "event": (
                        "Ticket types cannot be created for canceled or "
                        "finished events."
                    )
                }
            )

        ticket_type = self.instance or TicketType(event=event)
        ticket_type.event = event
        ticket_type.price = attrs.get(
            "price",
            getattr(self.instance, "price", None),
        )
        ticket_type.quantity = attrs.get(
            "quantity",
            getattr(self.instance, "quantity", None),
        )
        ticket_type.sold_count = getattr(self.instance, "sold_count", 0)
        ticket_type.sales_start = attrs.get(
            "sales_start",
            getattr(self.instance, "sales_start", None),
        )
        ticket_type.sales_end = attrs.get(
            "sales_end",
            getattr(self.instance, "sales_end", None),
        )
        ticket_type.is_active = attrs.get(
            "is_active",
            getattr(self.instance, "is_active", True),
        )

        try:
            ticket_type.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs

    def create(self, validated_data):
        validated_data.pop("event", None)
        validated_data.pop("sold_count", None)
        return TicketType.objects.create(
            event=self.context["event"],
            **validated_data,
        )

    def update(self, instance, validated_data):
        validated_data.pop("event", None)
        validated_data.pop("sold_count", None)
        return super().update(instance, validated_data)
