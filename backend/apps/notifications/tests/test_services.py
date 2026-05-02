from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.tickets.models import TicketType

User = get_user_model()


class NotificationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Notification Events")
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Notification Event",
            "description": "Event",
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

    def test_create_notification_creates_notification_for_user(self):
        notification = NotificationService.create_notification(
            user=self.user,
            type=Notification.Type.SYSTEM,
            title="System",
            message="System message",
            entity_type="Event",
            entity_id=123,
            metadata={"source": "test"},
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.entity_id, "123")
        self.assertEqual(notification.metadata, {"source": "test"})

    def test_create_notification_returns_none_without_user(self):
        with self.assertLogs("apps.notifications.services", level="WARNING"):
            notification = NotificationService.create_notification(
                user=None,
                type=Notification.Type.SYSTEM,
                title="System",
                message="System message",
            )

        self.assertIsNone(notification)

    def test_notify_booking_created(self):
        booking = self.make_booking()

        notification = NotificationService.notify_booking_created(booking)

        self.assertEqual(notification.type, Notification.Type.BOOKING_CREATED)
        self.assertEqual(notification.user, booking.user)
        self.assertEqual(notification.entity_type, "Booking")
        self.assertEqual(notification.entity_id, str(booking.id))
        self.assertEqual(notification.metadata["booking_id"], booking.id)
        self.assertEqual(notification.metadata["event_id"], booking.event.id)
        self.assertEqual(notification.metadata["ticket_type_id"], booking.ticket_type_id)

    def test_notify_booking_canceled(self):
        booking = self.make_booking(status=Booking.Status.CANCELED)

        notification = NotificationService.notify_booking_canceled(booking)

        self.assertEqual(notification.type, Notification.Type.BOOKING_CANCELED)
        self.assertEqual(notification.user, booking.user)

    def test_notify_booking_used(self):
        booking = self.make_booking(is_used=True, used_at=timezone.now())

        notification = NotificationService.notify_booking_used(booking)

        self.assertEqual(notification.type, Notification.Type.BOOKING_USED)
        self.assertEqual(notification.user, booking.user)
        self.assertIn(booking.event.title, notification.message)

    def test_notify_event_canceled_notifies_paid_booking_users_once(self):
        event = self.make_event(title="Canceled Event")
        first_ticket = self.make_ticket_type(event=event, name="Standard")
        second_ticket = self.make_ticket_type(event=event, name="VIP")
        self.make_booking(user=self.user, ticket_type=first_ticket)
        self.make_booking(user=self.user, ticket_type=second_ticket)
        self.make_booking(user=self.other_user, ticket_type=first_ticket)

        notifications = NotificationService.notify_event_canceled(event)

        self.assertEqual(len(notifications), 2)
        self.assertEqual(
            Notification.objects.filter(
                type=Notification.Type.EVENT_CANCELED,
                entity_type="Event",
                entity_id=str(event.id),
            ).count(),
            2,
        )

    def test_notify_event_canceled_skips_canceled_and_expired_bookings(self):
        event = self.make_event(title="Skipped Event")
        ticket_type = self.make_ticket_type(event=event)
        self.make_booking(ticket_type=ticket_type, status=Booking.Status.CANCELED)
        self.make_booking(
            user=self.other_user,
            ticket_type=ticket_type,
            status=Booking.Status.EXPIRED,
        )

        notifications = NotificationService.notify_event_canceled(event)

        self.assertEqual(notifications, [])
        self.assertFalse(Notification.objects.exists())

    def test_notify_event_reminder(self):
        booking = self.make_booking()

        notification = NotificationService.notify_event_reminder(booking)

        self.assertEqual(notification.type, Notification.Type.EVENT_REMINDER)
        self.assertEqual(notification.user, booking.user)
        self.assertEqual(notification.entity_type, "Booking")
        self.assertEqual(notification.entity_id, str(booking.id))
