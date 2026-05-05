from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.tournaments.models import Participant, Tournament
from apps.tournaments.permissions import CanJoinTournament, CanManageTournament

from .utils import TournamentTestMixin


class TournamentPermissionTests(TournamentTestMixin, TestCase):
    def request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def test_can_manage_tournament_allows_organizer_and_admin(self):
        tournament = self.make_tournament()
        permission = CanManageTournament()

        self.assertTrue(
            permission.has_object_permission(
                self.request(self.organizer),
                None,
                tournament,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.request(self.admin_user),
                None,
                tournament,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.request(self.other_organizer),
                None,
                tournament,
            )
        )

    def test_can_join_tournament_checks_status_duplicate_and_capacity(self):
        tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
            max_participants=2,
        )
        permission = CanJoinTournament()

        self.assertTrue(
            permission.has_object_permission(self.request(self.user), None, tournament)
        )
        self.make_participant(tournament=tournament, user=self.user)
        self.assertFalse(
            permission.has_object_permission(self.request(self.user), None, tournament)
        )
        self.make_participant(tournament=tournament, user=self.second_user)
        self.assertFalse(
            permission.has_object_permission(
                self.request(self.third_user),
                None,
                tournament,
            )
        )

    def test_can_join_tournament_requires_open_registration(self):
        tournament = self.make_tournament(status=Tournament.Status.DRAFT)
        permission = CanJoinTournament()

        self.assertFalse(
            permission.has_object_permission(self.request(self.user), None, tournament)
        )
