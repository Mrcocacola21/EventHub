from unittest.mock import patch

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.bookings.models import Booking
from apps.bookings.services import BookingService, TicketValidationService
from apps.common.tests.factories import (
    BookingFactory,
    ParticipantFactory,
    RegistrationOpenTournamentFactory,
    TicketTypeFactory,
    UserFactory,
)
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.tournaments.models import Participant
from apps.tournaments.services import TournamentService


@pytest.mark.django_db
@pytest.mark.service
def test_booking_service_create_booking_increments_sold_count(
    temp_media_root,
    mock_celery_delay,
):
    ticket_type = TicketTypeFactory(quantity=2, sold_count=0)
    booking = BookingService.create_booking(UserFactory(), ticket_type.id)

    ticket_type.refresh_from_db()
    assert booking.status == Booking.Status.PAID
    assert ticket_type.sold_count == 1
    assert booking.qr_code
    assert booking.pdf_ticket


@pytest.mark.django_db
@pytest.mark.service
def test_booking_service_prevents_overselling(temp_media_root, mock_celery_delay):
    ticket_type = TicketTypeFactory(quantity=1, sold_count=0)

    BookingService.create_booking(UserFactory(), ticket_type.id)

    with pytest.raises(ValidationError):
        BookingService.create_booking(UserFactory(), ticket_type.id)

    ticket_type.refresh_from_db()
    assert ticket_type.sold_count == 1


@pytest.mark.django_db
@pytest.mark.service
def test_booking_cancel_decreases_sold_count():
    ticket_type = TicketTypeFactory(quantity=2, sold_count=1)
    booking = BookingFactory(ticket_type=ticket_type, status=Booking.Status.PAID)

    canceled = BookingService.cancel_booking(booking, booking.user)

    ticket_type.refresh_from_db()
    assert canceled.status == Booking.Status.CANCELED
    assert ticket_type.sold_count == 0


@pytest.mark.django_db
@pytest.mark.service
def test_ticket_validation_service_rules():
    booking = BookingFactory(status=Booking.Status.PAID)
    organizer = booking.ticket_type.event.organizer

    with pytest.raises(PermissionDenied):
        TicketValidationService.use_booking(booking.id, booking.user)

    used_booking = TicketValidationService.use_booking(booking.id, organizer)
    assert used_booking.is_used is True

    with pytest.raises(ValidationError):
        TicketValidationService.use_booking(booking.id, organizer)


@pytest.mark.django_db
@pytest.mark.service
def test_tournament_service_bracket_and_final_result():
    tournament = RegistrationOpenTournamentFactory()
    participants = [
        ParticipantFactory(tournament=tournament, seed=index + 1)
        for index in range(4)
    ]

    TournamentService.start_tournament(tournament, started_by=tournament.event.organizer)
    tournament.refresh_from_db()
    semifinal = tournament.matches.get(round=1, position=1)
    TournamentService.submit_match_result(
        semifinal,
        semifinal.player1,
        submitted_by=tournament.event.organizer,
    )
    second_semifinal = tournament.matches.get(round=1, position=2)
    TournamentService.submit_match_result(
        second_semifinal,
        second_semifinal.player1,
        submitted_by=tournament.event.organizer,
    )
    final = tournament.matches.get(round=2, position=1)
    final.refresh_from_db()
    TournamentService.submit_match_result(
        final,
        final.player1,
        submitted_by=tournament.event.organizer,
    )

    tournament.refresh_from_db()
    final.player1.refresh_from_db()
    assert tournament.status == tournament.Status.FINISHED
    assert tournament.matches.count() == 3
    assert final.player1.status == Participant.Status.WINNER
    assert {participant.id for participant in participants}


@pytest.mark.django_db
@pytest.mark.service
def test_notification_and_audit_services_create_records():
    user = UserFactory()
    notification = NotificationService.create_notification(
        user=user,
        type=Notification.Type.SYSTEM,
        title="System",
        message="Test notification",
        metadata={"source": "pytest"},
    )
    audit_log = AuditService.log_action(
        action=AuditLog.Action.USER_REGISTERED,
        entity_type="User",
        entity_id=user.id,
        user=user,
        metadata={"source": "pytest"},
    )

    assert notification.user_id == user.id
    assert notification.metadata["source"] == "pytest"
    assert audit_log.user_id == user.id
    assert audit_log.entity_id == str(user.id)


@pytest.mark.django_db
@pytest.mark.service
def test_audit_service_failure_does_not_raise():
    with patch(
        "apps.audit.services.AuditLog.objects.create",
        side_effect=RuntimeError("audit down"),
    ):
        result = AuditService.log_action(action="TEST", entity_type="Thing")

    assert result is None
