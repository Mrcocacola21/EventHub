from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event
from apps.tournaments.models import Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class BracketApiTests(TournamentTestMixin, APITestCase):
    def test_public_tournament_bracket_is_visible_and_sorted(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user, seed=1)
        self.make_participant(tournament=tournament, user=self.second_user, seed=2)
        self.make_participant(tournament=tournament, user=self.third_user, seed=3)
        self.make_participant(tournament=tournament, user=self.organizer, seed=4)
        TournamentService.start_tournament(tournament)

        response = self.client.get(reverse("tournament-bracket", args=[tournament.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tournament"]["id"], tournament.id)
        self.assertEqual([round_data["round"] for round_data in response.data["rounds"]], [1, 2])
        self.assertEqual(
            [match["position"] for match in response.data["rounds"][0]["matches"]],
            [1, 2],
        )

    def test_private_bracket_only_visible_to_owner_or_admin(self):
        draft_event = self.make_event(status=Event.Status.DRAFT)
        tournament = Tournament.objects.create(event=draft_event, title="Private")

        anonymous = self.client.get(reverse("tournament-bracket", args=[tournament.id]))

        self.client.force_authenticate(self.other_organizer)
        other = self.client.get(reverse("tournament-bracket", args=[tournament.id]))

        self.client.force_authenticate(self.organizer)
        owner = self.client.get(reverse("tournament-bracket", args=[tournament.id]))

        self.assertEqual(anonymous.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(other.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(owner.status_code, status.HTTP_200_OK)
