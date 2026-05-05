from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event
from apps.tournaments.models import Match, Tournament

from .utils import TournamentTestMixin


class MatchApiTests(TournamentTestMixin, APITestCase):
    def results(self, response):
        return response.data.get("results", response.data)

    def test_public_can_list_matches_for_public_tournament(self):
        tournament = self.make_tournament()
        match = Match.objects.create(tournament=tournament, round=1, position=1)

        response = self.client.get(reverse("tournament-matches", args=[tournament.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in self.results(response)]
        self.assertIn(match.id, ids)

    def test_organizer_can_list_own_private_matches(self):
        draft_event = self.make_event(status=Event.Status.DRAFT)
        tournament = Tournament.objects.create(event=draft_event, title="Private")
        match = Match.objects.create(tournament=tournament, round=1, position=1)
        self.client.force_authenticate(self.organizer)

        response = self.client.get(reverse("tournament-matches", args=[tournament.id]))

        ids = [item["id"] for item in self.results(response)]
        self.assertIn(match.id, ids)

    def test_other_organizer_cannot_view_private_matches(self):
        draft_event = self.make_event(status=Event.Status.DRAFT)
        tournament = Tournament.objects.create(event=draft_event, title="Private")
        self.client.force_authenticate(self.other_organizer)

        response = self.client.get(reverse("tournament-matches", args=[tournament.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_match_creation_is_not_exposed_in_basic_api(self):
        tournament = self.make_tournament()
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("tournament-matches", args=[tournament.id]),
            {"round": 1, "position": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
