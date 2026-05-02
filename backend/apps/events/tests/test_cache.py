from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase, APITransactionTestCase

from apps.events.cache import EventCacheService, PopularTournamentsService
from apps.events.models import Event, EventCategory

User = get_user_model()

LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "event-cache-tests",
    }
}


@override_settings(CACHES=LOCMEM_CACHES)
class EventCacheApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Cache Events")
        cls.other_category = EventCategory.objects.create(name="Other Cache Events")
        cls.regular_user = User.objects.create_user(
            email="cache-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="cache-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin = User.objects.create_user(
            email="cache-admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )

    def setUp(self):
        cache.clear()

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Cached Event",
            "description": "Cached event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def result_titles(self, response):
        results = response.data.get("results", response.data)
        return [item["title"] for item in results]

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_anonymous_events_list_uses_cached_response(self):
        event = self.make_event(title="Cached List Event")
        url = reverse("event-list")

        first_response = self.client.get(url)
        Event.objects.filter(id=event.id).update(title="Changed Without Invalidate")
        second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn("Cached List Event", self.result_titles(second_response))
        self.assertNotIn("Changed Without Invalidate", self.result_titles(second_response))

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_different_query_params_produce_different_cache_keys(self):
        factory = APIRequestFactory()
        first_request = Request(
            factory.get("/api/events/", {"category": self.category.id})
        )
        second_request = Request(
            factory.get("/api/events/", {"category": self.other_category.id})
        )

        first_key = EventCacheService.make_events_list_key(first_request)
        second_key = EventCacheService.make_events_list_key(second_request)

        self.assertNotEqual(first_key, second_key)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_organizer_list_bypasses_public_cache(self):
        self.make_event(title="Public Cached Event")
        draft = self.make_event(
            title="Organizer Draft",
            organizer=self.organizer,
            status=Event.Status.DRAFT,
        )
        url = reverse("event-list")

        anonymous_response = self.client.get(url)
        self.client.force_authenticate(self.organizer)
        organizer_response = self.client.get(url)

        self.assertIn("Public Cached Event", self.result_titles(anonymous_response))
        self.assertIn(draft.title, self.result_titles(organizer_response))

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_draft_event_never_appears_from_anonymous_cache(self):
        draft = self.make_event(title="Private Draft", status=Event.Status.DRAFT)

        response = self.client.get(reverse("event-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(draft.title, self.result_titles(response))

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_published_event_detail_uses_cached_response(self):
        event = self.make_event(title="Cached Detail Event")
        url = reverse("event-detail", args=[event.id])

        first_response = self.client.get(url)
        Event.objects.filter(id=event.id).update(title="Changed Detail")
        second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data["title"], "Cached Detail Event")

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_draft_event_detail_is_not_cached_for_public_requests(self):
        event = self.make_event(title="Draft Detail", status=Event.Status.DRAFT)
        url = reverse("event-detail", args=[event.id])

        response = self.client.get(url)
        cache_key = EventCacheService.make_event_detail_key(event.id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIsNone(cache.get(cache_key))

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_organizer_detail_bypasses_public_cache(self):
        event = self.make_event(title="Public Detail")
        url = reverse("event-detail", args=[event.id])

        self.client.get(url)
        Event.objects.filter(id=event.id).update(title="Organizer Fresh Detail")
        self.client.force_authenticate(self.organizer)
        organizer_response = self.client.get(url)

        self.assertEqual(organizer_response.status_code, status.HTTP_200_OK)
        self.assertEqual(organizer_response.data["title"], "Organizer Fresh Detail")

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_popular_tournaments_fallback_returns_empty_list(self):
        self.assertEqual(PopularTournamentsService.get_popular(limit=10), [])


@override_settings(CACHES=LOCMEM_CACHES)
class EventCacheInvalidationTransactionTests(APITransactionTestCase):
    def setUp(self):
        cache.clear()
        self.category = EventCategory.objects.create(name="Cache Invalidation Events")
        self.organizer = User.objects.create_user(
            email="cache-invalidation-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Invalidated Event",
            "description": "Invalidated event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_event_update_bumps_cache_version(self):
        event = self.make_event(status=Event.Status.PUBLISHED)
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        response = self.client.patch(
            reverse("event-detail", args=[event.id]),
            {"title": "Updated Cache Version"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_event_publish_cancel_and_finish_bump_cache_version(self):
        event = self.make_event()
        self.client.force_authenticate(self.organizer)
        before = EventCacheService.get_events_cache_version()

        publish_response = self.client.post(reverse("event-publish", args=[event.id]))
        cancel_response = self.client.post(reverse("event-cancel", args=[event.id]))
        finish_response = self.client.post(reverse("event-finish", args=[event.id]))

        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(finish_response.status_code, status.HTTP_200_OK)
        self.assertGreater(EventCacheService.get_events_cache_version(), before)
