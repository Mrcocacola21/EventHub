from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.pdf import PDFTicketService
from apps.bookings.services import BookingService
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class PDFTicketServiceTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="PDF Events")
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
            title="PDF Event",
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

    def read_file_bytes(self, field_file):
        field_file.open("rb")
        try:
            return field_file.read()
        finally:
            field_file.close()

    def test_generate_pdf_for_booking(self):
        booking = self.make_booking()

        PDFTicketService.generate_for_booking(booking)

        booking.refresh_from_db()
        data = self.read_file_bytes(booking.pdf_ticket)
        self.assertTrue(booking.pdf_ticket)
        self.assertTrue(booking.pdf_ticket.name.endswith(".pdf"))
        self.assertGreater(len(data), 0)
        self.assertTrue(data.startswith(b"%PDF"))

    def test_generate_pdf_uses_existing_file_without_force(self):
        booking = self.make_booking()
        booking.pdf_ticket.save(
            "existing_ticket.pdf",
            ContentFile(b"%PDF existing"),
            save=True,
        )
        existing_name = booking.pdf_ticket.name

        PDFTicketService.generate_for_booking(booking)

        booking.refresh_from_db()
        self.assertEqual(booking.pdf_ticket.name, existing_name)

    def test_generate_pdf_force_regenerates_file(self):
        booking = self.make_booking()
        booking.pdf_ticket.save(
            "existing_ticket.pdf",
            ContentFile(b"%PDF existing"),
            save=True,
        )
        existing_name = booking.pdf_ticket.name

        PDFTicketService.generate_for_booking(booking, force=True)

        booking.refresh_from_db()
        self.assertNotEqual(booking.pdf_ticket.name, existing_name)
        self.assertTrue(booking.pdf_ticket.name.endswith(".pdf"))
        self.assertTrue(self.read_file_bytes(booking.pdf_ticket).startswith(b"%PDF"))

    def test_generate_pdf_generates_qr_if_missing(self):
        booking = self.make_booking()

        PDFTicketService.generate_for_booking(booking)

        booking.refresh_from_db()
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.pdf_ticket)

    def test_booking_service_generates_pdf_after_purchase(self):
        ticket_type = self.make_ticket_type()

        booking = BookingService.create_booking(self.user, ticket_type.id)

        ticket_type.refresh_from_db()
        booking.refresh_from_db()
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.pdf_ticket)
        self.assertEqual(ticket_type.sold_count, 1)
