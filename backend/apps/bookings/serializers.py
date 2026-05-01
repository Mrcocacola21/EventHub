from rest_framework import serializers

from apps.tickets.models import TicketType
from apps.users.serializers import UserShortSerializer

from .models import Booking
from .services import BookingService


class BookingTicketTypeDetailSerializer(serializers.ModelSerializer):
    event = serializers.SerializerMethodField()

    class Meta:
        model = TicketType
        fields = ("id", "name", "price", "event")

    def get_event(self, obj):
        return {
            "id": obj.event_id,
            "title": obj.event.title,
        }


class BookingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_detail = UserShortSerializer(source="user", read_only=True)
    ticket_type = serializers.PrimaryKeyRelatedField(read_only=True)
    ticket_type_detail = BookingTicketTypeDetailSerializer(
        source="ticket_type",
        read_only=True,
    )
    event = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "user",
            "user_detail",
            "ticket_type",
            "ticket_type_detail",
            "event",
            "status",
            "price_at_purchase",
            "is_used",
            "used_at",
            "qr_code",
            "pdf_ticket",
            "expires_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_event(self, obj):
        event = obj.event
        return {
            "id": event.id,
            "title": event.title,
        }


class BookingCreateSerializer(serializers.Serializer):
    ticket_type_id = serializers.IntegerField()

    def validate_ticket_type_id(self, value):
        if not TicketType.objects.filter(id=value).exists():
            raise serializers.ValidationError("Ticket type does not exist.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        return BookingService.create_booking(
            user=request.user,
            ticket_type_id=validated_data["ticket_type_id"],
        )
