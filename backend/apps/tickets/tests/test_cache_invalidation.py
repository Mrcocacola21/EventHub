from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from apps.events.cache import EventCacheService
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ticket-cache-invalidation-tests",
    }
}


@override_settings(CACHES=LOCMEM_CACHES)
class TicketTypeCacheInvalidationTests(APITransactionTestCase):
    def setUp(self):
        cache.clear()
        self.category = EventCategory.objects.create(name="Ticket Cache Events")
        self.organizer = User.objects.create_user(
            email="ticket-cache-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        start = timezone.now() + timedelta(days=2)
        self.event = Event.objects.create(
            title="Ticket Cache Event",
            description="Ticket cache event",
            category=self.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )

    def payload(self, **overrides):
        data = {
            "name": "Standard",
            "description": "Ticket",
            "price": "10.00",
            "quantity": 100,
        }
        data.update(overrides)
        return data

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_creating_ticket_type_bumps_events_cache_version(self):
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.post(
            reverse("event-ticket-types-list", kwargs={"event_id": self.event.id}),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_updating_ticket_type_bumps_events_cache_version(self):
        ticket_type = self.make_ticket_type()
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.patch(
            reverse("ticket-type-detail", kwargs={"pk": ticket_type.id}),
            {"price": "12.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_deleting_ticket_type_bumps_events_cache_version(self):
        ticket_type = self.make_ticket_type()
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.delete(
            reverse("ticket-type-detail", kwargs={"pk": ticket_type.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_deactivating_ticket_type_bumps_events_cache_version(self):
        ticket_type = self.make_ticket_type()
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.patch(
            reverse("ticket-type-detail", kwargs={"pk": ticket_type.id}),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)
