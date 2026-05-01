from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Booking Serializer Events")
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        start = timezone.now() + timedelta(days=2)
        cls.event = Event.objects.create(
            title="Serializer Event",
            description="Event",
            category=cls.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.ticket_type = TicketType.objects.create(
            event=cls.event,
            name="Standard",
            price=Decimal("10.00"),
            quantity=10,
        )
        cls.booking = Booking.objects.create(
            user=cls.user,
            ticket_type=cls.ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=cls.ticket_type.price,
        )

    def test_booking_serializer_includes_qr_pdf_and_usage_fields(self):
        data = BookingSerializer(self.booking).data

        self.assertIn("qr_code", data)
        self.assertIn("pdf_ticket", data)
        self.assertIn("is_used", data)
        self.assertIn("used_at", data)

    def test_qr_pdf_and_usage_fields_are_read_only(self):
        serializer = BookingSerializer()

        self.assertTrue(serializer.fields["qr_code"].read_only)
        self.assertTrue(serializer.fields["pdf_ticket"].read_only)
        self.assertTrue(serializer.fields["is_used"].read_only)
        self.assertTrue(serializer.fields["used_at"].read_only)

    def test_server_owned_fields_are_read_only(self):
        serializer = BookingSerializer()

        for field_name in (
            "user",
            "ticket_type",
            "status",
            "price_at_purchase",
            "qr_code",
            "pdf_ticket",
            "is_used",
            "used_at",
        ):
            self.assertTrue(serializer.fields[field_name].read_only)
