from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import Booking
from apps.bookings.qr import QRCodeService
from apps.bookings.services import BookingService
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class QRCodeServiceTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="QR Events")
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
            title="QR Event",
            description="Event",
            category=cls.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self):
        ticket_type = self.make_ticket_type()
        return Booking.objects.create(
            user=self.user,
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=ticket_type.price,
        )

    def test_generate_for_booking_creates_qr_code_file(self):
        booking = self.make_booking()

        QRCodeService.generate_for_booking(booking)

        booking.refresh_from_db()
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.qr_code.name.endswith(".png"))
        booking.qr_code.open("rb")
        try:
            self.assertGreater(len(booking.qr_code.read()), 0)
        finally:
            booking.qr_code.close()

    def test_second_generate_without_force_does_not_replace_existing_qr(self):
        booking = self.make_booking()
        booking.qr_code.save("existing_qr.png", ContentFile(b"existing"), save=True)
        existing_name = booking.qr_code.name

        QRCodeService.generate_for_booking(booking)

        booking.refresh_from_db()
        self.assertEqual(booking.qr_code.name, existing_name)

    def test_force_regenerates_qr_code(self):
        booking = self.make_booking()
        booking.qr_code.save("existing_qr.png", ContentFile(b"existing"), save=True)
        existing_name = booking.qr_code.name

        QRCodeService.generate_for_booking(booking, force=True)

        booking.refresh_from_db()
        self.assertNotEqual(booking.qr_code.name, existing_name)
        self.assertTrue(booking.qr_code.name.endswith(".png"))

    def test_signed_token_can_be_parsed(self):
        booking = self.make_booking()
        token = QRCodeService.build_token(booking)

        payload = QRCodeService.parse_token(token)

        self.assertEqual(payload["booking_id"], booking.id)
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["ticket_type_id"], booking.ticket_type_id)

    def test_invalid_token_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QRCodeService.parse_token("invalid-token")

    def test_booking_service_generates_qr_code_after_purchase(self):
        ticket_type = self.make_ticket_type()

        booking = BookingService.create_booking(self.user, ticket_type.id)

        ticket_type.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertTrue(booking.qr_code)
        self.assertEqual(ticket_type.sold_count, 1)
