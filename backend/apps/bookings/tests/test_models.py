from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Booking Events")
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
            title="Published Event",
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

    def make_booking(self, **overrides):
        data = {
            "user": self.user,
            "ticket_type": self.ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": self.ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def test_str_returns_user_ticket_type_and_status(self):
        booking = self.make_booking()

        self.assertEqual(str(booking), "user@example.com - Standard - PAID")

    def test_event_property_returns_ticket_type_event(self):
        booking = self.make_booking()

        self.assertEqual(booking.event, self.event)

    def test_can_be_canceled_true_for_paid_and_not_used(self):
        booking = self.make_booking()

        self.assertTrue(booking.can_be_canceled)

    def test_can_be_canceled_false_for_used_booking(self):
        booking = self.make_booking(is_used=True)

        self.assertFalse(booking.can_be_canceled)

    def test_can_be_canceled_false_for_canceled_or_expired_booking(self):
        canceled = self.make_booking(status=Booking.Status.CANCELED)
        expired = self.make_booking(status=Booking.Status.EXPIRED)

        self.assertFalse(canceled.can_be_canceled)
        self.assertFalse(expired.can_be_canceled)

    def test_can_be_used_true_for_paid_and_not_used(self):
        booking = self.make_booking()

        self.assertTrue(booking.can_be_used)

    def test_can_be_used_false_for_canceled_expired_or_used_booking(self):
        canceled = self.make_booking(status=Booking.Status.CANCELED)
        expired = self.make_booking(status=Booking.Status.EXPIRED)
        used = self.make_booking(is_used=True)

        self.assertFalse(canceled.can_be_used)
        self.assertFalse(expired.can_be_used)
        self.assertFalse(used.can_be_used)
