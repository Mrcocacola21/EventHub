from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tournaments.models import Participant, Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class MatchResultApiTests(TournamentTestMixin, APITestCase):
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
        ]
        TournamentService.start_tournament(self.tournament)
        self.match = self.tournament.matches.get()

    def test_result_endpoint_permissions(self):
        url = reverse("match-result", args=[self.match.id])

        self.client.force_authenticate(self.user)
        regular = self.client.post(url, {"winner_id": self.participants[0].id})

        self.client.force_authenticate(self.other_organizer)
        other = self.client.post(url, {"winner_id": self.participants[0].id})

        self.client.force_authenticate(self.organizer)
        owner = self.client.post(url, {"winner_id": self.participants[0].id})

        self.assertEqual(regular.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(other.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(owner.status_code, status.HTTP_200_OK)

    def test_admin_can_submit_final_result_and_finish_tournament(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(
            reverse("match-result", args=[self.match.id]),
            {"winner_id": self.participants[0].id},
            format="json",
        )

        self.tournament.refresh_from_db()
        winner = Participant.objects.get(id=self.participants[0].id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.tournament.status, Tournament.Status.FINISHED)
        self.assertEqual(winner.status, Participant.Status.WINNER)

    def test_invalid_winner_and_repeated_submit_are_rejected(self):
        other = self.make_participant(
            tournament=self.make_tournament(title="Other"),
            user=self.third_user,
        )
        self.client.force_authenticate(self.organizer)
        url = reverse("match-result", args=[self.match.id])

        invalid = self.client.post(url, {"winner_id": other.id}, format="json")
        valid = self.client.post(
            url,
            {"winner_id": self.participants[0].id},
            format="json",
        )
        repeated = self.client.post(
            url,
            {"winner_id": self.participants[0].id},
            format="json",
        )

        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST)
