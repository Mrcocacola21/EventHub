from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.tournaments.models import Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class TournamentAuditTests(TournamentTestMixin, APITestCase):
    def test_register_start_result_and_finish_are_logged(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)

        participant_one = TournamentService.register_participant(
            tournament,
            self.user,
            added_by=self.user,
        )
        participant_two = TournamentService.register_participant(
            tournament,
            self.second_user,
            added_by=self.second_user,
        )
        TournamentService.start_tournament(tournament, started_by=self.organizer)
        match = tournament.matches.get()
        TournamentService.submit_match_result(
            match,
            participant_one,
            submitted_by=self.organizer,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_PARTICIPANT_REGISTERED,
                entity_id=str(tournament.id),
                metadata__participant_id=participant_one.id,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_STARTED,
                entity_id=str(tournament.id),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.MATCH_RESULT_SUBMITTED,
                entity_id=str(match.id),
                metadata__winner_id=participant_one.id,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_FINISHED,
                entity_id=str(tournament.id),
                metadata__winner_id=participant_one.id,
            ).exists()
        )
        self.assertFalse(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_FINISHED,
                metadata__winner_id=participant_two.id,
            ).exists()
        )
