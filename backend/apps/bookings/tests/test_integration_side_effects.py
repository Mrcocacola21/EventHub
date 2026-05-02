from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.bookings.models import Booking
from apps.bookings.services import BookingService, TicketValidationService
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.cache import EventCacheService
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

User = get_user_model()

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "booking-subsystem-integration-cache",
    }
}

IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


@override_settings(CACHES=LOCMEM_CACHES, CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class BookingSubsystemIntegrationTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Subsystem Events")
        cls.user = User.objects.create_user(
            email="subsystem-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="subsystem-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def setUp(self):
        self.event = self.make_event()
        self.ticket_type = self.make_ticket_type(event=self.event)

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Subsystem Event",
            "description": "Subsystem event",
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
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
            "sold_count": 0,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def test_create_booking_preserves_all_side_effects_after_commit(self):
        before_cache_version = EventCacheService.get_events_cache_version()

        with patch(
            "apps.bookings.tasks.send_booking_confirmation_email.delay",
        ) as delay_mock:
            with self.captureOnCommitCallbacks(execute=True):
                booking = BookingService.create_booking(
                    user=self.user,
                    ticket_type_id=self.ticket_type.id,
                )

        self.ticket_type.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(Booking.objects.filter(id=booking.id).count(), 1)
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertEqual(self.ticket_type.sold_count, 1)
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.pdf_ticket)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.BOOKING_CREATED,
                entity_type="Booking",
                entity_id=str(booking.id),
                user=self.user,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.BOOKING_CREATED,
                entity_type="Booking",
                entity_id=str(booking.id),
            ).exists()
        )
        delay_mock.assert_called_once_with(booking.id)
        self.assertGreater(
            EventCacheService.get_events_cache_version(),
            before_cache_version,
        )

    def test_use_booking_preserves_audit_and_notification_side_effects(self):
        booking = Booking.objects.create(
            user=self.user,
            ticket_type=self.ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=self.ticket_type.price,
        )
        self.ticket_type.sold_count = 1
        self.ticket_type.save(update_fields=["sold_count", "updated_at"])

        with self.captureOnCommitCallbacks(execute=True):
            used_booking = TicketValidationService.use_booking(
                booking_id=booking.id,
                checked_by_user=self.organizer,
            )

        used_booking.refresh_from_db()
        self.assertTrue(used_booking.is_used)
        self.assertIsNotNone(used_booking.used_at)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.BOOKING_USED,
                entity_type="Booking",
                entity_id=str(booking.id),
                user=self.organizer,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.BOOKING_USED,
                entity_type="Booking",
                entity_id=str(booking.id),
            ).exists()
        )

    def test_event_cancel_preserves_audit_notification_and_cache_invalidation(self):
        booking = Booking.objects.create(
            user=self.user,
            ticket_type=self.ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=self.ticket_type.price,
        )
        self.ticket_type.sold_count = 1
        self.ticket_type.save(update_fields=["sold_count", "updated_at"])
        before_cache_version = EventCacheService.get_events_cache_version()

        self.event.cancel()
        from apps.audit.services import AuditService
        from apps.notifications.services import NotificationService

        AuditService.log_event_canceled(self.event, user=self.organizer)
        NotificationService.notify_event_canceled(self.event)
        EventCacheService.invalidate_events_cache()

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.CANCELED)
        self.assertFalse(self.event.is_published)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.EVENT_CANCELED,
                entity_type="Event",
                entity_id=str(self.event.id),
                user=self.organizer,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.EVENT_CANCELED,
                entity_type="Event",
                entity_id=str(self.event.id),
            ).exists()
        )
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertGreater(
            EventCacheService.get_events_cache_version(),
            before_cache_version,
        )
