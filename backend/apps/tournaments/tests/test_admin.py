from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.tournaments.admin import (
    MatchAdmin,
    MatchInline,
    ParticipantAdmin,
    ParticipantInline,
    TournamentAdmin,
)
from apps.tournaments.models import Match, Participant, Tournament

from .utils import TournamentTestMixin


class TournamentAdminTests(TournamentTestMixin, TestCase):
    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def test_admin_models_are_registered(self):
        self.assertIsInstance(admin.site._registry[Tournament], TournamentAdmin)
        self.assertIsInstance(admin.site._registry[Participant], ParticipantAdmin)
        self.assertIsInstance(admin.site._registry[Match], MatchAdmin)

    def test_tournament_admin_configuration(self):
        tournament_admin = admin.site._registry[Tournament]

        for field_name in (
            "title",
            "event",
            "event_organizer",
            "type",
            "status",
            "participants_count_display",
            "matches_count_display",
        ):
            self.assertIn(field_name, tournament_admin.list_display)

        self.assertIn("status", tournament_admin.list_filter)
        self.assertIn("event__title", tournament_admin.search_fields)
        self.assertIn("event__organizer__email", tournament_admin.search_fields)
        self.assertIn("participants_count_display", tournament_admin.readonly_fields)
        self.assertIn("matches_count_display", tournament_admin.readonly_fields)
        self.assertEqual(tournament_admin.date_hierarchy, "created_at")
        self.assertEqual(
            tournament_admin.list_select_related,
            ("event", "event__organizer"),
        )
        self.assertIn("open_registration", tournament_admin.actions)
        self.assertIn("start_tournaments", tournament_admin.actions)
        self.assertIn("cancel_tournaments", tournament_admin.actions)
        self.assertIn(ParticipantInline, tournament_admin.inlines)
        self.assertIn(MatchInline, tournament_admin.inlines)

    def test_admin_actions_update_status(self):
        tournament_admin = admin.site._registry[Tournament]
        tournament = self.make_tournament()

        tournament_admin.open_registration(
            self.request(),
            Tournament.objects.filter(id=tournament.id),
        )
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.REGISTRATION_OPEN)

        tournament_admin.cancel_tournaments(
            self.request(),
            Tournament.objects.filter(id=tournament.id),
        )
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.CANCELED)

    def test_start_tournaments_action_uses_service_and_skips_invalid(self):
        tournament_admin = admin.site._registry[Tournament]
        valid = self.make_tournament(
            title="Valid",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        invalid = self.make_tournament(title="Invalid", status=Tournament.Status.DRAFT)
        self.make_participant(tournament=valid, user=self.user)
        self.make_participant(tournament=valid, user=self.second_user)

        started_count = tournament_admin.start_tournaments(
            self.request(),
            Tournament.objects.filter(id__in=[valid.id, invalid.id]),
        )

        valid.refresh_from_db()
        invalid.refresh_from_db()
        self.assertEqual(started_count, 1)
        self.assertEqual(valid.status, Tournament.Status.IN_PROGRESS)
        self.assertEqual(valid.matches.count(), 1)
        self.assertEqual(invalid.status, Tournament.Status.DRAFT)

    def test_participant_admin_configuration(self):
        participant_admin = admin.site._registry[Participant]

        self.assertIn("tournament", participant_admin.list_display)
        self.assertIn("user", participant_admin.list_display)
        self.assertIn("status", participant_admin.list_filter)
        self.assertIn("user__email", participant_admin.search_fields)

    def test_match_admin_configuration(self):
        match_admin = admin.site._registry[Match]

        self.assertIn("tournament", match_admin.list_display)
        self.assertIn("round", match_admin.list_display)
        self.assertIn("status", match_admin.list_filter)
        self.assertIn("player1__user__email", match_admin.search_fields)
        self.assertEqual(match_admin.ordering, ("tournament", "round", "position"))
