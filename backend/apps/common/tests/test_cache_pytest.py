import pytest
from django.conf import settings

from apps.bookings.services import BookingService
from apps.common.tests.factories import PublishedEventFactory, TicketTypeFactory, UserFactory
from apps.events.cache import EventCacheService
from apps.events.models import Event


@pytest.mark.cache
def test_test_settings_use_locmem_cache():
    assert (
        settings.CACHES["default"]["BACKEND"]
        == "django.core.cache.backends.locmem.LocMemCache"
    )


@pytest.mark.django_db
@pytest.mark.cache
def test_public_event_list_cache_does_not_leak_draft_events(api_client, clear_cache):
    published_event = PublishedEventFactory()
    draft_event = PublishedEventFactory(status=Event.Status.DRAFT)

    first_response = api_client.get("/api/events/")
    second_response = api_client.get("/api/events/")

    first_ids = {item["id"] for item in first_response.data.get("results", first_response.data)}
    second_ids = {item["id"] for item in second_response.data.get("results", second_response.data)}
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert published_event.id in first_ids
    assert draft_event.id not in first_ids
    assert first_ids == second_ids


@pytest.mark.django_db
@pytest.mark.cache
def test_booking_create_bumps_events_cache_version(
    clear_cache,
    temp_media_root,
    mock_celery_delay,
):
    ticket_type = TicketTypeFactory(quantity=2, sold_count=0)
    before_version = EventCacheService.get_events_cache_version()

    BookingService.create_booking(UserFactory(), ticket_type.id)

    after_version = EventCacheService.get_events_cache_version()
    assert after_version > before_version
