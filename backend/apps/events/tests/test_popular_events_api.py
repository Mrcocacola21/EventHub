from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.events.cache import EventCacheService
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "popular-events-cache-tests",
    }
}


@override_settings(CACHES=LOCMEM_CACHES)
class PopularEventsApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Popular Events")
        cls.user = User.objects.create_user(
            email="popular-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="popular-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def setUp(self):
        cache.clear()

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Popular Event",
            "description": "Popular event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_ticket_type(self, event, **overrides):
        data = {
            "event": event,
            "name": f"Standard {event.id}",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, ticket_type, **overrides):
        data = {
            "user": self.user,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_popular_events_sorted_by_booking_count_desc(self):
        first = self.make_event(title="One Booking")
        second = self.make_event(title="Two Bookings")
        first_ticket = self.make_ticket_type(first)
        second_ticket = self.make_ticket_type(second)
        self.make_booking(first_ticket)
        self.make_booking(second_ticket)
        self.make_booking(second_ticket)

        response = self.client.get(reverse("event-popular"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], second.id)
        self.assertEqual(response.data[0]["booking_count"], 2)
        self.assertEqual(response.data[1]["id"], first.id)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_popular_events_respects_limit_and_caps_to_50(self):
        for index in range(55):
            event = self.make_event(title=f"Popular {index}")
            self.make_ticket_type(event)

        limited_response = self.client.get(reverse("event-popular"), {"limit": 2})
        capped_response = self.client.get(reverse("event-popular"), {"limit": 999})

        self.assertEqual(len(limited_response.data), 2)
        self.assertEqual(len(capped_response.data), 50)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_popular_events_include_only_published_events(self):
        published = self.make_event(title="Published Popular")
        draft = self.make_event(title="Draft Popular", status=Event.Status.DRAFT)
        published_ticket = self.make_ticket_type(published)
        draft_ticket = self.make_ticket_type(draft)
        self.make_booking(published_ticket)
        self.make_booking(draft_ticket)

        response = self.client.get(reverse("event-popular"))

        ids = [item["id"] for item in response.data]
        self.assertIn(published.id, ids)
        self.assertNotIn(draft.id, ids)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_popular_events_result_is_cached(self):
        event = self.make_event(title="Cached Popular")
        ticket_type = self.make_ticket_type(event)
        self.make_booking(ticket_type)

        first_response = self.client.get(reverse("event-popular"))
        Event.objects.filter(id=event.id).update(title="Changed Popular")
        second_response = self.client.get(reverse("event-popular"))

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data[0]["title"], "Cached Popular")


@override_settings(CACHES=LOCMEM_CACHES)
class PopularEventsInvalidationTests(APITransactionTestCase):
    def setUp(self):
        cache.clear()
        self.category = EventCategory.objects.create(name="Popular Invalidation")
        self.user = User.objects.create_user(
            email="popular-invalidation-user@example.com",
            password="StrongPass123!",
        )
        self.organizer = User.objects.create_user(
            email="popular-invalidation-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Popular Invalidation Event",
            "description": "Popular invalidation event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_ticket_type(self, event, **overrides):
        data = {
            "event": event,
            "name": f"Standard {event.id}",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_booking_create_and_cancel_invalidate_popular_events_cache(self):
        event = self.make_event()
        ticket_type = self.make_ticket_type(event)
        before = EventCacheService.get_events_cache_version()

        with patch("apps.bookings.tasks.send_booking_confirmation_email.delay"):
            booking = BookingService.create_booking(self.user, ticket_type.id)
        after_create = EventCacheService.get_events_cache_version()
        BookingService.cancel_booking(booking, self.user)
        after_cancel = EventCacheService.get_events_cache_version()

        self.assertGreater(after_create, before)
        self.assertGreater(after_cancel, after_create)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_event_cancel_invalidates_popular_events_cache(self):
        event = self.make_event()
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.post(reverse("event-cancel", args=[event.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)
