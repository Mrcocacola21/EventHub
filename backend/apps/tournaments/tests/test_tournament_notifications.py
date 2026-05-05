from unittest.mock import patch

from django.test import TestCase

from apps.notifications.models import Notification
from apps.tournaments.models import Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class TournamentNotificationTests(TournamentTestMixin, TestCase):
    @patch("apps.notifications.services.NotificationService.send_realtime_notification")
    def test_start_tournament_notifies_participants(self, mocked_realtime):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)
        self.make_participant(tournament=tournament, user=self.second_user)

        with self.captureOnCommitCallbacks(execute=True):
            TournamentService.start_tournament(tournament, started_by=self.organizer)

        self.assertEqual(
            Notification.objects.filter(
                type=Notification.Type.TOURNAMENT_STARTED,
                entity_type="Tournament",
                entity_id=str(tournament.id),
            ).count(),
            2,
        )
        self.assertEqual(mocked_realtime.call_count, 2)

    @patch("apps.notifications.services.NotificationService.send_realtime_notification")
    def test_match_result_and_final_create_notifications(self, mocked_realtime):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        participant_one = self.make_participant(tournament=tournament, user=self.user)
        participant_two = self.make_participant(
            tournament=tournament,
            user=self.second_user,
        )
        with self.captureOnCommitCallbacks(execute=True):
            TournamentService.start_tournament(tournament, started_by=self.organizer)
        match = tournament.matches.get()

        with self.captureOnCommitCallbacks(execute=True):
            TournamentService.submit_match_result(
                match,
                participant_one,
                submitted_by=self.organizer,
            )

        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.MATCH_RESULT_UPDATED,
                entity_type="Match",
                entity_id=str(match.id),
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.second_user,
                type=Notification.Type.MATCH_RESULT_UPDATED,
                entity_type="Match",
                entity_id=str(match.id),
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.TOURNAMENT_FINISHED,
                entity_type="Tournament",
                entity_id=str(tournament.id),
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=participant_two.user,
                type=Notification.Type.TOURNAMENT_FINISHED,
            ).exists()
        )
        self.assertGreaterEqual(mocked_realtime.call_count, 5)
