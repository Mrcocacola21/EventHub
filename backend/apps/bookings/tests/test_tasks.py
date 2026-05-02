from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.tasks import (
    expire_pending_bookings,
    send_booking_confirmation_email,
)
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingTaskTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Booking Task Events")
        cls.user = User.objects.create_user(
            email="task-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="task-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        start = timezone.now() + timedelta(days=2)
        cls.event = Event.objects.create(
            title="Task Event",
            description="Task event",
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

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None) or self.make_ticket_type()
        data = {
            "user": self.user,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def test_send_booking_confirmation_email_sends_email(self):
        booking = self.make_booking()

        result = send_booking_confirmation_email(booking.id)

        self.assertEqual(result, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.event.title, mail.outbox[0].subject)
        self.assertIn(str(booking.id), mail.outbox[0].body)
        self.assertIn(self.event.title, mail.outbox[0].body)
        self.assertIn(self.user.email, mail.outbox[0].body)

    def test_send_booking_confirmation_email_missing_booking_returns_not_found(self):
        with patch("apps.bookings.tasks.logger.warning"):
            result = send_booking_confirmation_email(999999)

        self.assertEqual(result, "not_found")
        self.assertEqual(len(mail.outbox), 0)

    def test_create_booking_schedules_confirmation_email_on_commit(self):
        ticket_type = self.make_ticket_type()

        with patch(
            "apps.bookings.tasks.send_booking_confirmation_email.delay",
        ) as delay_mock:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                booking = BookingService.create_booking(self.user, ticket_type.id)

        self.assertGreaterEqual(len(callbacks), 1)
        delay_mock.assert_called_once_with(booking.id)

    def test_expire_pending_bookings_expires_pending_expired_booking(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.PENDING,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        expired_count = expire_pending_bookings()

        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertEqual(ticket_type.sold_count, 0)

    def test_expire_pending_bookings_keeps_not_expired_pending_booking(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.PENDING,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        expired_count = expire_pending_bookings()

        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(expired_count, 0)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(ticket_type.sold_count, 1)

    def test_expire_pending_bookings_does_not_expire_paid_booking(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        expired_count = expire_pending_bookings()

        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(expired_count, 0)
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertEqual(ticket_type.sold_count, 1)

    def test_expire_pending_bookings_does_not_change_canceled_booking(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.CANCELED,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        expired_count = expire_pending_bookings()

        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(expired_count, 0)
        self.assertEqual(booking.status, Booking.Status.CANCELED)
        self.assertEqual(ticket_type.sold_count, 1)

    def test_expire_pending_bookings_never_decreases_sold_count_below_zero(self):
        ticket_type = self.make_ticket_type(sold_count=0)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.PENDING,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        expired_count = expire_pending_bookings()

        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertEqual(ticket_type.sold_count, 0)
