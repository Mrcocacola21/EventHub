from datetime import timedelta

import pytest
from django.utils import timezone

from apps.bookings.models import Booking
from apps.common.tests.factories import (
    BookingFactory,
    FinishedEventFactory,
    NotificationFactory,
    OrganizerFactory,
    PublishedEventFactory,
    TicketTypeFactory,
    UserFactory,
)
from apps.events.models import Event


def _results(data):
    return data.get("results", data)


@pytest.mark.django_db
@pytest.mark.api
def test_auth_register_and_login(api_client):
    register_payload = {
        "email": "pytest-user@example.com",
        "username": "pytest-user",
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
    }

    register_response = api_client.post(
        "/api/auth/register/",
        register_payload,
        format="json",
    )
    login_response = api_client.post(
        "/api/auth/login/",
        {
            "email": register_payload["email"],
            "password": register_payload["password"],
        },
        format="json",
    )

    assert register_response.status_code == 201
    assert "access" in register_response.data
    assert "refresh" in register_response.data
    assert login_response.status_code == 200
    assert "access" in login_response.data


@pytest.mark.django_db
@pytest.mark.api
def test_events_public_list_and_organizer_create(api_client, authenticated_client):
    public_event = PublishedEventFactory()
    draft_event = PublishedEventFactory(status=Event.Status.DRAFT)
    organizer = OrganizerFactory()
    category = public_event.category

    list_response = api_client.get("/api/events/")
    user_create_response = authenticated_client(UserFactory()).post(
        "/api/events/",
        {
            "title": "User Event",
            "description": "Forbidden",
            "category": category.id,
            "location": "Kyiv",
            "start_datetime": (timezone.now() + timedelta(days=20)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=20, hours=2)).isoformat(),
        },
        format="json",
    )
    organizer_client = authenticated_client(organizer)
    create_response = organizer_client.post(
        "/api/events/",
        {
            "title": "Organizer Event",
            "description": "Created with pytest",
            "category": category.id,
            "location": "Kyiv",
            "start_datetime": (timezone.now() + timedelta(days=21)).isoformat(),
            "end_datetime": (timezone.now() + timedelta(days=21, hours=2)).isoformat(),
            "max_participants": 50,
        },
        format="json",
    )

    returned_ids = {item["id"] for item in _results(list_response.data)}
    assert list_response.status_code == 200
    assert public_event.id in returned_ids
    assert draft_event.id not in returned_ids
    assert user_create_response.status_code == 403
    assert create_response.status_code == 201


@pytest.mark.django_db
@pytest.mark.api
def test_ticket_type_permissions(api_client, authenticated_client):
    event = PublishedEventFactory()

    list_response = api_client.get(f"/api/events/{event.id}/tickets/")
    user_create_response = authenticated_client(UserFactory()).post(
        f"/api/events/{event.id}/tickets/",
        {
            "name": "VIP",
            "price": "50.00",
            "quantity": 5,
            "is_active": True,
        },
        format="json",
    )
    organizer_create_response = authenticated_client(event.organizer).post(
        f"/api/events/{event.id}/tickets/",
        {
            "name": "Standard",
            "price": "25.00",
            "quantity": 10,
            "is_active": True,
        },
        format="json",
    )

    assert list_response.status_code == 200
    assert user_create_response.status_code == 403
    assert organizer_create_response.status_code == 201


@pytest.mark.django_db
@pytest.mark.api
def test_booking_api_creates_booking_and_prevents_sold_out(
    authenticated_client,
    temp_media_root,
    mock_celery_delay,
):
    ticket_type = TicketTypeFactory(quantity=1, sold_count=0)
    client = authenticated_client(UserFactory())

    first_response = client.post(
        "/api/bookings/",
        {"ticket_type_id": ticket_type.id},
        format="json",
    )
    second_response = client.post(
        "/api/bookings/",
        {"ticket_type_id": ticket_type.id},
        format="json",
    )

    ticket_type.refresh_from_db()
    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert ticket_type.sold_count == 1
    assert Booking.objects.filter(ticket_type=ticket_type).count() == 1


@pytest.mark.django_db
@pytest.mark.api
def test_notifications_api_returns_only_current_user_notifications(authenticated_client):
    user = UserFactory()
    own_notification = NotificationFactory(user=user)
    NotificationFactory(user=UserFactory())

    response = authenticated_client(user).get("/api/notifications/")

    notification_ids = {item["id"] for item in _results(response.data)}
    assert response.status_code == 200
    assert own_notification.id in notification_ids
    assert len(notification_ids) == 1


@pytest.mark.django_db
@pytest.mark.api
def test_paid_attendee_can_create_review_for_finished_event(authenticated_client):
    user = UserFactory()
    event = FinishedEventFactory()
    ticket_type = TicketTypeFactory(event=event, is_active=False)
    BookingFactory(user=user, ticket_type=ticket_type, status=Booking.Status.PAID)

    response = authenticated_client(user).post(
        f"/api/events/{event.id}/reviews/",
        {"rating": 5, "comment": "Great event!"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["rating"] == 5
