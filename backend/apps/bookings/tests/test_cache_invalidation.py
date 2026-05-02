from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.cache import EventCacheService
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "booking-cache-invalidation-tests",
    }
}


@override_settings(CACHES=LOCMEM_CACHES)
class BookingCacheInvalidationTests(TempMediaRootMixin, TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.category = EventCategory.objects.create(name="Booking Cache Events")
        self.user = User.objects.create_user(
            email="booking-cache-user@example.com",
            password="StrongPass123!",
        )
        self.organizer = User.objects.create_user(
            email="booking-cache-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        start = timezone.now() + timedelta(days=2)
        self.event = Event.objects.create(
            title="Booking Cache Event",
            description="Booking cache event",
            category=self.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None) or self.make_ticket_type()
        ticket_type.sold_count = max(ticket_type.sold_count, 1)
        ticket_type.save(update_fields=["sold_count", "updated_at"])
        data = {
            "user": self.user,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_create_booking_invalidates_popular_events_cache(self):
        ticket_type = self.make_ticket_type()
        before = EventCacheService.get_events_cache_version()

        with patch("apps.bookings.tasks.send_booking_confirmation_email.delay"):
            BookingService.create_booking(self.user, ticket_type.id)

        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_cancel_booking_invalidates_popular_events_cache(self):
        booking = self.make_booking()
        before = EventCacheService.get_events_cache_version()

        BookingService.cancel_booking(booking, self.user)

        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_expire_pending_booking_invalidates_popular_events_cache(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(
            ticket_type=ticket_type,
            status=Booking.Status.PENDING,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        before = EventCacheService.get_events_cache_version()

        BookingService.expire_booking(booking.id)

        self.assertGreater(EventCacheService.get_events_cache_version(), before)
