from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.tasks import expire_pending_bookings
from apps.common.tests.factories import BookingFactory, TicketTypeFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.transactions
def test_sequential_overselling_keeps_sold_count_consistent(
    temp_media_root,
    mock_celery_delay,
):
    ticket_type = TicketTypeFactory(quantity=1, sold_count=0)

    BookingService.create_booking(UserFactory(), ticket_type.id)

    with pytest.raises(ValidationError):
        BookingService.create_booking(UserFactory(), ticket_type.id)

    ticket_type.refresh_from_db()
    assert ticket_type.sold_count == 1
    assert Booking.objects.filter(ticket_type=ticket_type).count() == 1


@pytest.mark.django_db
@pytest.mark.transactions
def test_invalid_cancel_does_not_change_sold_count():
    ticket_type = TicketTypeFactory(quantity=3, sold_count=1)
    booking = BookingFactory(
        ticket_type=ticket_type,
        status=Booking.Status.PAID,
        is_used=True,
    )

    with pytest.raises(ValidationError):
        BookingService.cancel_booking(booking, booking.user)

    ticket_type.refresh_from_db()
    booking.refresh_from_db()
    assert ticket_type.sold_count == 1
    assert booking.status == Booking.Status.PAID


@pytest.mark.django_db
@pytest.mark.transactions
@pytest.mark.celery
def test_expired_pending_booking_expires_and_paid_booking_does_not():
    ticket_type = TicketTypeFactory(quantity=5, sold_count=2)
    pending_booking = BookingFactory(
        ticket_type=ticket_type,
        status=Booking.Status.PENDING,
        expires_at=timezone.now() - timedelta(minutes=5),
    )
    paid_booking = BookingFactory(
        ticket_type=ticket_type,
        status=Booking.Status.PAID,
        expires_at=timezone.now() - timedelta(minutes=5),
    )

    expired_count = expire_pending_bookings()

    pending_booking.refresh_from_db()
    paid_booking.refresh_from_db()
    ticket_type.refresh_from_db()
    assert expired_count == 1
    assert pending_booking.status == Booking.Status.EXPIRED
    assert paid_booking.status == Booking.Status.PAID
    assert ticket_type.sold_count == 1
