from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.events.tasks import send_event_reminders
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

User = get_user_model()


class EventReminderTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Reminder Events")
        cls.user = User.objects.create_user(
            email="reminder-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="reminder-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(hours=12)
        data = {
            "title": "Reminder Event",
            "description": "Reminder event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.make_event(),
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
            "sold_count": 1,
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

    def test_send_event_reminders_sends_email_for_paid_booking_within_window(self):
        booking = self.make_booking()

        sent_count = send_event_reminders()

        booking.refresh_from_db()
        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(booking.ticket_type.event.title, mail.outbox[0].subject)
        self.assertIn(str(booking.id), mail.outbox[0].body)
        self.assertIsNotNone(booking.reminder_sent_at)
        self.assertTrue(
            Notification.objects.filter(
                user=booking.user,
                type=Notification.Type.EVENT_REMINDER,
                entity_type="Booking",
                entity_id=str(booking.id),
            ).exists()
        )

    def test_send_event_reminders_does_not_send_for_event_outside_window(self):
        event = self.make_event(
            title="Later Event",
            start_datetime=timezone.now() + timedelta(days=2),
            end_datetime=timezone.now() + timedelta(days=2, hours=2),
        )
        ticket_type = self.make_ticket_type(event=event)
        booking = self.make_booking(ticket_type=ticket_type)

        sent_count = send_event_reminders()

        booking.refresh_from_db()
        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(booking.reminder_sent_at)

    def test_send_event_reminders_does_not_send_for_canceled_event(self):
        event = self.make_event(
            title="Canceled Event",
            status=Event.Status.CANCELED,
        )
        ticket_type = self.make_ticket_type(event=event)
        booking = self.make_booking(ticket_type=ticket_type)

        sent_count = send_event_reminders()

        booking.refresh_from_db()
        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(booking.reminder_sent_at)

    def test_send_event_reminders_does_not_send_for_canceled_or_expired_booking(self):
        canceled = self.make_booking(status=Booking.Status.CANCELED)
        expired = self.make_booking(
            ticket_type=self.make_ticket_type(name="Expired"),
            status=Booking.Status.EXPIRED,
        )

        sent_count = send_event_reminders()

        canceled.refresh_from_db()
        expired.refresh_from_db()
        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(canceled.reminder_sent_at)
        self.assertIsNone(expired.reminder_sent_at)

    def test_send_event_reminders_does_not_send_duplicate_reminder(self):
        booking = self.make_booking(reminder_sent_at=timezone.now())

        sent_count = send_event_reminders()

        booking.refresh_from_db()
        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNotNone(booking.reminder_sent_at)
        self.assertFalse(
            Notification.objects.filter(
                type=Notification.Type.EVENT_REMINDER,
                entity_id=str(booking.id),
            ).exists()
        )

    def test_send_event_reminders_returns_correct_count(self):
        first = self.make_booking()
        second = self.make_booking(ticket_type=self.make_ticket_type(name="VIP"))

        sent_count = send_event_reminders()

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(sent_count, 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIsNotNone(first.reminder_sent_at)
        self.assertIsNotNone(second.reminder_sent_at)
