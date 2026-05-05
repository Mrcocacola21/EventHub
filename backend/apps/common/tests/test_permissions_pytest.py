import pytest

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.common.tests.factories import (
    BookingFactory,
    NotificationFactory,
    OrganizerFactory,
    PublishedEventFactory,
    TicketTypeFactory,
    UserFactory,
)


@pytest.mark.django_db
@pytest.mark.permissions
def test_organizer_cannot_edit_another_organizer_event(authenticated_client):
    event = PublishedEventFactory()
    another_organizer = OrganizerFactory()

    response = authenticated_client(another_organizer).patch(
        f"/api/events/{event.id}/",
        {"title": "Forbidden update"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.permissions
def test_admin_can_update_protected_event(authenticated_client, admin_user):
    event = PublishedEventFactory()

    response = authenticated_client(admin_user).patch(
        f"/api/events/{event.id}/",
        {"title": "Admin update"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["title"] == "Admin update"


@pytest.mark.django_db
@pytest.mark.permissions
def test_booking_owner_can_download_pdf_but_cannot_use_ticket(
    authenticated_client,
    temp_media_root,
    mock_celery_delay,
):
    booking = BookingService.create_booking(
        UserFactory(),
        TicketTypeFactory().id,
    )
    owner_client = authenticated_client(booking.user)

    download_response = owner_client.get(f"/api/bookings/{booking.id}/download-pdf/")
    use_response = owner_client.post(f"/api/bookings/{booking.id}/use/")

    assert download_response.status_code == 200
    assert use_response.status_code == 403


@pytest.mark.django_db
@pytest.mark.permissions
def test_event_organizer_can_use_ticket_but_other_organizer_cannot(authenticated_client):
    booking = BookingFactory(status=Booking.Status.PAID)
    event_organizer = booking.ticket_type.event.organizer
    other_organizer = OrganizerFactory()

    forbidden_response = authenticated_client(other_organizer).post(
        f"/api/bookings/{booking.id}/use/",
    )
    allowed_response = authenticated_client(event_organizer).post(
        f"/api/bookings/{booking.id}/use/",
    )

    assert forbidden_response.status_code == 403
    assert allowed_response.status_code == 200


@pytest.mark.django_db
@pytest.mark.permissions
def test_user_sees_only_own_notifications(authenticated_client):
    user = UserFactory()
    own_notification = NotificationFactory(user=user)
    other_notification = NotificationFactory(user=UserFactory())

    response = authenticated_client(user).get("/api/notifications/")
    ids = {item["id"] for item in response.data.get("results", response.data)}

    assert response.status_code == 200
    assert own_notification.id in ids
    assert other_notification.id not in ids
