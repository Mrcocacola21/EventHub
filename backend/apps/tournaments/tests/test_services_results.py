from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.tournaments.models import Match, Participant, Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class TournamentResultServiceTests(TournamentTestMixin, APITestCase):
    def setUp(self):
        self.tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.participants = [
            self.make_participant(tournament=self.tournament, user=self.user, seed=1),
            self.make_participant(
                tournament=self.tournament,
                user=self.second_user,
                seed=2,
            ),
            self.make_participant(
                tournament=self.tournament,
                user=self.third_user,
                seed=3,
            ),
            self.make_participant(
                tournament=self.tournament,
                user=self.organizer,
                seed=4,
            ),
        ]
        TournamentService.start_tournament(self.tournament)

    def test_submit_result_finishes_match_and_promotes_winner(self):
        semifinal = self.tournament.matches.get(round=1, position=1)
        final = self.tournament.matches.get(round=2, position=1)

        updated_match = TournamentService.submit_match_result(
            semifinal,
            semifinal.player1,
        )

        final.refresh_from_db()
        loser = semifinal.player2
        loser.refresh_from_db()
        self.assertEqual(updated_match.status, Match.Status.FINISHED)
        self.assertIsNotNone(updated_match.finished_at)
        self.assertEqual(final.player1_id, semifinal.player1_id)
        self.assertEqual(loser.status, Participant.Status.ELIMINATED)

    def test_winner_must_be_match_player(self):
        semifinal = self.tournament.matches.get(round=1, position=1)
        other_tournament = self.make_tournament(
            title="Other",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        other_participant = self.make_participant(
            tournament=other_tournament,
            user=self.admin_user,
        )

        with self.assertRaises(ValidationError):
            TournamentService.submit_match_result(semifinal, other_participant)

    def test_cannot_submit_finished_match_twice(self):
        semifinal = self.tournament.matches.get(round=1, position=1)
        TournamentService.submit_match_result(semifinal, semifinal.player1)

        with self.assertRaises(ValidationError):
            TournamentService.submit_match_result(semifinal, semifinal.player1)

    def test_final_result_finishes_tournament(self):
        semifinal_one = self.tournament.matches.get(round=1, position=1)
        semifinal_two = self.tournament.matches.get(round=1, position=2)
        winner_one = semifinal_one.player1
        winner_two = semifinal_two.player1
        TournamentService.submit_match_result(semifinal_one, winner_one)
        TournamentService.submit_match_result(semifinal_two, winner_two)
        final = self.tournament.matches.get(round=2, position=1)

        TournamentService.submit_match_result(final, winner_one)

        self.tournament.refresh_from_db()
        winner_one.refresh_from_db()
        winner_two.refresh_from_db()
        self.assertEqual(self.tournament.status, Tournament.Status.FINISHED)
        self.assertEqual(winner_one.status, Participant.Status.WINNER)
        self.assertEqual(winner_two.status, Participant.Status.ELIMINATED)

    def test_result_requires_in_progress_tournament(self):
        semifinal = self.tournament.matches.get(round=1, position=1)
        self.tournament.status = Tournament.Status.CANCELED
        self.tournament.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ValidationError):
            TournamentService.submit_match_result(semifinal, semifinal.player1)
