from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.bookings.admin import BookingAdmin
from apps.bookings.models import Booking
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingAdminTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Booking Admin Events")
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin_user = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )
        start = timezone.now() + timedelta(days=2)
        cls.event = Event.objects.create(
            title="Admin Booking Event",
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
            sold_count=1,
        )

    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def make_booking(self, **overrides):
        data = {
            "user": self.user,
            "ticket_type": self.ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": self.ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def test_booking_admin_registered(self):
        self.assertIsInstance(admin.site._registry[Booking], BookingAdmin)

    def test_readonly_fields_include_expected_fields(self):
        booking_admin = admin.site._registry[Booking]

        for field_name in (
            "id",
            "user",
            "ticket_type",
            "price_at_purchase",
            "qr_code",
            "pdf_ticket",
            "is_used",
            "used_at",
            "created_at",
            "updated_at",
        ):
            self.assertIn(field_name, booking_admin.readonly_fields)

    def test_list_display_includes_expected_fields(self):
        booking_admin = admin.site._registry[Booking]

        for field_name in (
            "user",
            "ticket_type",
            "status",
            "price_at_purchase",
            "is_used",
            "has_qr_code",
            "has_pdf_ticket",
            "created_at",
        ):
            self.assertIn(field_name, booking_admin.list_display)

    def test_list_filter_includes_expected_fields(self):
        booking_admin = admin.site._registry[Booking]

        for field_name in ("status", "is_used", "created_at"):
            self.assertIn(field_name, booking_admin.list_filter)

    def test_expected_actions_exist(self):
        booking_admin = admin.site._registry[Booking]

        self.assertIn("cancel_bookings", booking_admin.actions)
        self.assertIn("mark_bookings_used", booking_admin.actions)
        self.assertIn("regenerate_qr_codes", booking_admin.actions)
        self.assertIn("regenerate_pdf_tickets", booking_admin.actions)
        self.assertEqual(booking_admin.date_hierarchy, "created_at")
        self.assertEqual(booking_admin.ordering, ("-created_at",))

    def test_cancel_action_uses_booking_service_effects(self):
        booking_admin = admin.site._registry[Booking]
        booking = self.make_booking()

        booking_admin.cancel_bookings(
            self.request(),
            Booking.objects.filter(id=booking.id),
        )

        booking.refresh_from_db()
        self.ticket_type.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELED)
        self.assertEqual(self.ticket_type.sold_count, 0)

    def test_mark_bookings_used_action_uses_validation_service(self):
        booking_admin = admin.site._registry[Booking]
        booking = self.make_booking()

        booking_admin.mark_bookings_used(
            self.request(),
            Booking.objects.filter(id=booking.id),
        )

        booking.refresh_from_db()
        self.assertTrue(booking.is_used)
        self.assertIsNotNone(booking.used_at)

    def test_regenerate_qr_codes_action_generates_qr(self):
        booking_admin = admin.site._registry[Booking]
        booking = self.make_booking()
        booking.qr_code.save("existing_qr.png", ContentFile(b"existing"), save=True)
        existing_name = booking.qr_code.name

        booking_admin.regenerate_qr_codes(
            self.request(),
            Booking.objects.filter(id=booking.id),
        )

        booking.refresh_from_db()
        self.assertTrue(booking.qr_code)
        self.assertNotEqual(booking.qr_code.name, existing_name)

    def test_regenerate_pdf_tickets_action_generates_pdf(self):
        booking_admin = admin.site._registry[Booking]
        booking = self.make_booking()
        booking.pdf_ticket.save(
            "existing_ticket.pdf",
            ContentFile(b"%PDF existing"),
            save=True,
        )
        existing_name = booking.pdf_ticket.name

        booking_admin.regenerate_pdf_tickets(
            self.request(),
            Booking.objects.filter(id=booking.id),
        )

        booking.refresh_from_db()
        self.assertTrue(booking.pdf_ticket)
        self.assertNotEqual(booking.pdf_ticket.name, existing_name)

    def test_has_pdf_ticket_reflects_file_presence(self):
        booking_admin = admin.site._registry[Booking]
        booking = self.make_booking()

        self.assertFalse(booking_admin.has_pdf_ticket(booking))
        booking_admin.regenerate_pdf_tickets(
            self.request(),
            Booking.objects.filter(id=booking.id),
        )
        booking.refresh_from_db()

        self.assertTrue(booking_admin.has_pdf_ticket(booking))
