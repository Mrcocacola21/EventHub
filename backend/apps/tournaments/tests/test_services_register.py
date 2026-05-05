from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.events.models import Event
from apps.tournaments.models import Participant, Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class TournamentRegisterServiceTests(TournamentTestMixin, APITestCase):
    def test_user_can_register_when_registration_open(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)

        participant = TournamentService.register_participant(tournament, self.user)

        self.assertEqual(participant.tournament_id, tournament.id)
        self.assertEqual(participant.user_id, self.user.id)
        self.assertEqual(participant.status, Participant.Status.REGISTERED)
        self.assertEqual(participant.seed, 1)

    def test_duplicate_registration_is_denied(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        TournamentService.register_participant(tournament, self.user)

        with self.assertRaises(ValidationError):
            TournamentService.register_participant(tournament, self.user)

    def test_max_participants_is_enforced(self):
        tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
            max_participants=2,
        )
        TournamentService.register_participant(tournament, self.user)
        TournamentService.register_participant(tournament, self.second_user)

        with self.assertRaises(ValidationError):
            TournamentService.register_participant(tournament, self.third_user)

    def test_registration_deadline_is_enforced(self):
        tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
            registration_deadline=timezone.now() - timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            TournamentService.register_participant(tournament, self.user)

    def test_invalid_statuses_are_denied(self):
        for tournament_status in (
            Tournament.Status.DRAFT,
            Tournament.Status.IN_PROGRESS,
            Tournament.Status.FINISHED,
            Tournament.Status.CANCELED,
        ):
            tournament = self.make_tournament(
                title=f"Tournament {tournament_status}",
                status=tournament_status,
            )
            with self.subTest(status=tournament_status):
                with self.assertRaises(ValidationError):
                    TournamentService.register_participant(tournament, self.user)

    def test_registration_requires_published_event(self):
        event = self.make_event(status=Event.Status.DRAFT)
        tournament = Tournament.objects.create(
            event=event,
            title="Draft Event Tournament",
            status=Tournament.Status.REGISTRATION_OPEN,
        )

        with self.assertRaises(ValidationError):
            TournamentService.register_participant(tournament, self.user)

    def test_seed_auto_increments_from_existing_participants(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user, seed=4)

        participant = TournamentService.register_participant(
            tournament,
            self.second_user,
        )

        self.assertEqual(participant.seed, 5)
