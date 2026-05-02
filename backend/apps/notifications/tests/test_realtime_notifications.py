from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.tickets.models import TicketType

IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

User = get_user_model()


class FakeChannelLayer:
    def __init__(self):
        self.sent_messages = []

    async def group_send(self, group, message):
        self.sent_messages.append((group, message))


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class RealtimeNotificationServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Realtime Events")
        cls.user = User.objects.create_user(
            email="realtime-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="realtime-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Realtime Event",
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

    def test_create_notification_sends_group_message_to_user(self):
        channel_layer = FakeChannelLayer()

        with patch(
            "apps.notifications.services.get_channel_layer",
            return_value=channel_layer,
        ):
            notification = NotificationService.create_notification(
                user=self.user,
                type=Notification.Type.SYSTEM,
                title="System",
                message="System message",
                entity_type="System",
                entity_id=1,
                metadata={"source": "test"},
            )

        group, message = channel_layer.sent_messages[0]
        payload = message["payload"]
        self.assertEqual(group, f"user_notifications_{self.user.id}")
        self.assertEqual(message["type"], "notification.event")
        self.assertEqual(payload["type"], "notification")
        self.assertEqual(payload["notification"]["id"], notification.id)
        self.assertEqual(payload["notification"]["type"], Notification.Type.SYSTEM)
        self.assertEqual(payload["notification"]["title"], "System")
        self.assertEqual(payload["notification"]["message"], "System message")
        self.assertFalse(payload["notification"]["is_read"])
        self.assertEqual(payload["notification"]["metadata"], {"source": "test"})

    def test_booking_created_notification_sends_realtime_event(self):
        channel_layer = FakeChannelLayer()
        booking = self.make_booking()

        with patch(
            "apps.notifications.services.get_channel_layer",
            return_value=channel_layer,
        ):
            notification = NotificationService.notify_booking_created(booking)

        group, message = channel_layer.sent_messages[0]
        self.assertEqual(group, f"user_notifications_{self.user.id}")
        self.assertEqual(
            message["payload"]["notification"]["type"],
            Notification.Type.BOOKING_CREATED,
        )
        self.assertEqual(message["payload"]["notification"]["id"], notification.id)

    def test_booking_used_notification_sends_realtime_event(self):
        channel_layer = FakeChannelLayer()
        booking = self.make_booking(is_used=True, used_at=timezone.now())

        with patch(
            "apps.notifications.services.get_channel_layer",
            return_value=channel_layer,
        ):
            notification = NotificationService.notify_booking_used(booking)

        group, message = channel_layer.sent_messages[0]
        self.assertEqual(group, f"user_notifications_{self.user.id}")
        self.assertEqual(
            message["payload"]["notification"]["type"],
            Notification.Type.BOOKING_USED,
        )
        self.assertEqual(message["payload"]["notification"]["id"], notification.id)

    def test_realtime_send_failure_does_not_break_notification_creation(self):
        class FailingChannelLayer:
            async def group_send(self, group, message):
                raise RuntimeError("channel layer unavailable")

        with self.assertLogs("apps.notifications.services", level="ERROR"), patch(
            "apps.notifications.services.get_channel_layer",
            return_value=FailingChannelLayer(),
        ):
            notification = NotificationService.create_notification(
                user=self.user,
                type=Notification.Type.SYSTEM,
                title="System",
                message="System message",
            )

        self.assertIsNotNone(notification)
        self.assertTrue(Notification.objects.filter(id=notification.id).exists())
