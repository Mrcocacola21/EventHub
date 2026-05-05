from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.common.tests.factories import (
    AdminUserFactory,
    BookingFactory,
    OrganizerFactory,
    PublishedEventFactory,
    TicketTypeFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    def _authenticate(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _authenticate


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def organizer(db):
    return OrganizerFactory()


@pytest.fixture
def admin_user(db):
    return AdminUserFactory()


@pytest.fixture
def published_event(db):
    return PublishedEventFactory()


@pytest.fixture
def ticket_type(db):
    return TicketTypeFactory()


@pytest.fixture
def booking(db):
    return BookingFactory()


@pytest.fixture
def temp_media_root(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_celery_delay():
    with patch("apps.bookings.tasks.send_booking_confirmation_email.delay") as mocked:
        yield mocked
