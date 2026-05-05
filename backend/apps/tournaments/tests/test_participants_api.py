from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tournaments.models import Participant, Tournament

from .utils import TournamentTestMixin


class ParticipantApiTests(TournamentTestMixin, APITestCase):
    def results(self, response):
        return response.data.get("results", response.data)

    def test_authenticated_user_can_join_open_tournament(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("tournament-participants", args=[tournament.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertTrue(
            Participant.objects.filter(tournament=tournament, user=self.user).exists()
        )

    def test_anonymous_cannot_join(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)

        response = self.client.post(
            reverse("tournament-participants", args=[tournament.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_join_denied(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("tournament-participants", args=[tournament.id]),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_max_participants_and_deadline_enforced(self):
        full = self.make_tournament(
            title="Full",
            status=Tournament.Status.REGISTRATION_OPEN,
            max_participants=1,
        )
        self.make_participant(tournament=full, user=self.user)
        closed = self.make_tournament(
            title="Closed",
            status=Tournament.Status.REGISTRATION_OPEN,
            registration_deadline=timezone.now() - timedelta(minutes=1),
        )
        self.client.force_authenticate(self.second_user)

        full_response = self.client.post(
            reverse("tournament-participants", args=[full.id]),
            {},
            format="json",
        )
        closed_response = self.client.post(
            reverse("tournament-participants", args=[closed.id]),
            {},
            format="json",
        )

        self.assertEqual(full_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(closed_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_can_add_participant_by_user_id(self):
        tournament = self.make_tournament(status=Tournament.Status.DRAFT)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("tournament-participants", args=[tournament.id]),
            {"user": self.user.id, "seed": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["seed"], 1)

    def test_another_organizer_joining_cannot_add_someone_else(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.client.force_authenticate(self.other_organizer)

        response = self.client.post(
            reverse("tournament-participants", args=[tournament.id]),
            {"user": self.user.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.other_organizer.id)

    def test_participant_list_visible_for_public_tournament(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        participant = self.make_participant(tournament=tournament, user=self.user)

        response = self.client.get(
            reverse("tournament-participants", args=[tournament.id])
        )

        ids = [item["id"] for item in self.results(response)]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(participant.id, ids)
