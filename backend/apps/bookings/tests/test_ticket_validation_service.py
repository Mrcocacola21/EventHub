from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bookings.models import Booking
from apps.bookings.qr import QRCodeService
from apps.bookings.services import TicketValidationService
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

User = get_user_model()


class TicketValidationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Validation Events")
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
        )
        cls.another_user = User.objects.create_user(
            email="another@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.other_organizer = User.objects.create_user(
            email="other-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )
        cls.superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )
        cls.event = cls.make_event(
            title="Published Event",
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.canceled_event = cls.make_event(
            title="Canceled Event",
            organizer=cls.organizer,
            status=Event.Status.CANCELED,
        )

    @classmethod
    def make_event(cls, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Event",
            "description": "Event description",
            "category": cls.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": cls.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
            "sold_count": 1,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None)
        if ticket_type is None:
            ticket_type = self.make_ticket_type()
        data = {
            "user": self.owner,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def test_event_organizer_can_use_booking(self):
        booking = self.make_booking()

        used_booking = TicketValidationService.use_booking(
            booking.id,
            self.organizer,
        )

        self.assertTrue(used_booking.is_used)
        self.assertIsNotNone(used_booking.used_at)

    def test_use_booking_creates_notification_on_commit(self):
        booking = self.make_booking()

        with self.captureOnCommitCallbacks(execute=True):
            TicketValidationService.use_booking(booking.id, self.organizer)

        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                type=Notification.Type.BOOKING_USED,
                entity_type="Booking",
                entity_id=str(booking.id),
            ).exists()
        )

    def test_admin_and_superuser_can_use_any_booking(self):
        admin_booking = self.make_booking()
        superuser_booking = self.make_booking(
            ticket_type=self.make_ticket_type(name="VIP")
        )

        admin_used = TicketValidationService.use_booking(
            admin_booking.id,
            self.admin,
        )
        superuser_used = TicketValidationService.use_booking(
            superuser_booking.id,
            self.superuser,
        )

        self.assertTrue(admin_used.is_used)
        self.assertTrue(superuser_used.is_used)

    def test_ticket_owner_cannot_use_own_ticket(self):
        booking = self.make_booking()

        with self.assertRaises(PermissionDenied):
            TicketValidationService.use_booking(booking.id, self.owner)

    def test_another_user_cannot_use_booking(self):
        booking = self.make_booking()

        with self.assertRaises(PermissionDenied):
            TicketValidationService.use_booking(booking.id, self.another_user)

    def test_another_organizer_cannot_use_booking_for_other_event(self):
        booking = self.make_booking()

        with self.assertRaises(PermissionDenied):
            TicketValidationService.use_booking(booking.id, self.other_organizer)

    def test_cannot_use_already_used_booking(self):
        booking = self.make_booking(is_used=True, used_at=timezone.now())

        with self.assertRaises(ValidationError):
            TicketValidationService.use_booking(booking.id, self.organizer)

    def test_cannot_use_canceled_or_expired_booking(self):
        canceled = self.make_booking(status=Booking.Status.CANCELED)
        expired = self.make_booking(
            ticket_type=self.make_ticket_type(name="Expired"),
            status=Booking.Status.EXPIRED,
        )

        with self.assertRaises(ValidationError):
            TicketValidationService.use_booking(canceled.id, self.organizer)
        with self.assertRaises(ValidationError):
            TicketValidationService.use_booking(expired.id, self.organizer)

    def test_cannot_use_booking_for_canceled_event(self):
        ticket_type = self.make_ticket_type(
            event=self.canceled_event,
            name="Canceled Event Ticket",
        )
        booking = self.make_booking(ticket_type=ticket_type)

        with self.assertRaises(ValidationError):
            TicketValidationService.use_booking(booking.id, self.organizer)

    def test_second_use_attempt_raises_and_keeps_first_used_at(self):
        booking = self.make_booking()
        TicketValidationService.use_booking(booking.id, self.organizer)
        booking.refresh_from_db()
        first_used_at = booking.used_at

        with self.assertRaises(ValidationError):
            TicketValidationService.use_booking(booking.id, self.organizer)

        booking.refresh_from_db()
        self.assertEqual(booking.used_at, first_used_at)

    def test_use_booking_by_token_uses_signed_payload(self):
        booking = self.make_booking()
        token = QRCodeService.build_token(booking)

        used_booking = TicketValidationService.use_booking_by_token(
            token,
            self.organizer,
        )

        self.assertTrue(used_booking.is_used)
