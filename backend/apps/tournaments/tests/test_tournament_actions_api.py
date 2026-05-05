from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tournaments.models import Participant, Tournament

from .utils import TournamentTestMixin


class TournamentActionsApiTests(TournamentTestMixin, APITestCase):
    def test_register_endpoint(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)

        anonymous = self.client.post(reverse("tournament-register", args=[tournament.id]))

        self.client.force_authenticate(self.user)
        created = self.client.post(reverse("tournament-register", args=[tournament.id]))
        duplicate = self.client.post(reverse("tournament-register", args=[tournament.id]))

        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["user"], self.user.id)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_endpoint_rejects_closed_and_full_tournament(self):
        closed = self.make_tournament(status=Tournament.Status.DRAFT)
        full = self.make_tournament(
            title="Full",
            status=Tournament.Status.REGISTRATION_OPEN,
            max_participants=2,
        )
        self.make_participant(tournament=full, user=self.user)
        self.make_participant(tournament=full, user=self.second_user)
        self.client.force_authenticate(self.third_user)

        closed_response = self.client.post(reverse("tournament-register", args=[closed.id]))
        full_response = self.client.post(reverse("tournament-register", args=[full.id]))

        self.assertEqual(closed_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(full_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_endpoint_permissions_and_success(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)
        self.make_participant(tournament=tournament, user=self.second_user)

        self.client.force_authenticate(self.user)
        regular_response = self.client.post(reverse("tournament-start", args=[tournament.id]))

        self.client.force_authenticate(self.other_organizer)
        other_response = self.client.post(reverse("tournament-start", args=[tournament.id]))

        self.client.force_authenticate(self.organizer)
        organizer_response = self.client.post(
            reverse("tournament-start", args=[tournament.id])
        )

        tournament.refresh_from_db()
        self.assertEqual(regular_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(other_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(organizer_response.status_code, status.HTTP_200_OK)
        self.assertEqual(tournament.status, Tournament.Status.IN_PROGRESS)
        self.assertEqual(tournament.matches.count(), 1)
        self.assertEqual(
            set(tournament.participants.values_list("status", flat=True)),
            {Participant.Status.ACTIVE},
        )

    def test_admin_can_start_tournament(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)
        self.make_participant(tournament=tournament, user=self.second_user)
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(reverse("tournament-start", args=[tournament.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
