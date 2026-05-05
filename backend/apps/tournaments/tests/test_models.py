from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event
from apps.tournaments.models import Match, Participant, Tournament

from .utils import TournamentTestMixin


class TournamentModelTests(TournamentTestMixin, TestCase):
    def test_tournament_str_and_counts(self):
        tournament = self.make_tournament(title="Autumn Cup")
        self.make_participant(tournament=tournament, user=self.user)
        Match.objects.create(tournament=tournament, round=1, position=1)

        self.assertEqual(str(tournament), "Autumn Cup")
        self.assertEqual(tournament.participants_count, 1)
        self.assertEqual(tournament.matches_count, 1)

    def test_one_tournament_per_event_is_enforced(self):
        event = self.make_event()
        self.make_tournament(event=event)

        with self.assertRaises(IntegrityError):
            self.make_tournament(event=event, title="Duplicate")

    def test_event_must_be_published(self):
        draft_event = self.make_event(status=Event.Status.DRAFT)
        tournament = Tournament(event=draft_event, title="Draft Cup")

        with self.assertRaises(ValidationError):
            tournament.full_clean()

    def test_max_participants_must_be_at_least_two(self):
        tournament = Tournament(
            event=self.make_event(),
            title="Tiny Cup",
            max_participants=1,
        )

        with self.assertRaises(ValidationError):
            tournament.full_clean()

    def test_registration_deadline_must_be_before_event_start(self):
        event = self.make_event()
        tournament = Tournament(
            event=event,
            title="Late Deadline",
            registration_deadline=event.start_datetime + timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            tournament.full_clean()

    def test_open_registration_and_cancel_update_status(self):
        tournament = self.make_tournament()

        tournament.open_registration()
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.REGISTRATION_OPEN)
        self.assertTrue(tournament.is_registration_open)

        tournament.cancel()
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.CANCELED)

    def test_can_start_requires_registration_open_and_two_participants(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)

        self.assertFalse(tournament.can_start)

        self.make_participant(tournament=tournament, user=self.second_user)
        self.assertTrue(tournament.can_start)

    def test_registration_deadline_controls_is_registration_open(self):
        tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
            registration_deadline=timezone.now() - timedelta(minutes=1),
        )

        self.assertFalse(tournament.is_registration_open)


class ParticipantModelTests(TournamentTestMixin, TestCase):
    def test_participant_str_and_default_status(self):
        tournament = self.make_tournament()
        participant = self.make_participant(tournament=tournament, user=self.user)

        self.assertEqual(
            str(participant),
            f"{self.user.email} in {tournament.title}",
        )
        self.assertEqual(participant.status, Participant.Status.REGISTERED)

    def test_unique_tournament_user_is_enforced(self):
        tournament = self.make_tournament()
        self.make_participant(tournament=tournament, user=self.user)

        with self.assertRaises(IntegrityError):
            self.make_participant(tournament=tournament, user=self.user)

    def test_max_participants_enforced(self):
        tournament = self.make_tournament(max_participants=2)
        self.make_participant(tournament=tournament, user=self.user)
        self.make_participant(tournament=tournament, user=self.second_user)
        participant = Participant(tournament=tournament, user=self.third_user)

        with self.assertRaises(ValidationError):
            participant.full_clean()

    def test_registration_deadline_enforced(self):
        tournament = self.make_tournament(
            registration_deadline=timezone.now() - timedelta(minutes=1),
        )
        participant = Participant(tournament=tournament, user=self.user)

        with self.assertRaises(ValidationError):
            participant.full_clean()


class MatchModelTests(TournamentTestMixin, TestCase):
    def test_match_str_and_properties(self):
        tournament = self.make_tournament()
        player1 = self.make_participant(tournament=tournament, user=self.user)
        player2 = self.make_participant(tournament=tournament, user=self.second_user)
        match = Match.objects.create(
            tournament=tournament,
            round=1,
            position=1,
            player1=player1,
            player2=player2,
            winner=player1,
            status=Match.Status.FINISHED,
        )

        self.assertEqual(str(match), f"{tournament.title} R1 M1")
        self.assertTrue(match.has_both_players)
        self.assertTrue(match.is_finished)

    def test_unique_round_position_per_tournament(self):
        tournament = self.make_tournament()
        Match.objects.create(tournament=tournament, round=1, position=1)

        with self.assertRaises(IntegrityError):
            Match.objects.create(tournament=tournament, round=1, position=1)

    def test_players_must_belong_to_same_tournament(self):
        tournament = self.make_tournament()
        other_tournament = self.make_tournament(title="Other")
        other_player = self.make_participant(
            tournament=other_tournament,
            user=self.user,
        )
        match = Match(
            tournament=tournament,
            round=1,
            position=1,
            player1=other_player,
        )

        with self.assertRaises(ValidationError):
            match.full_clean()

    def test_winner_must_be_player1_or_player2(self):
        tournament = self.make_tournament()
        player1 = self.make_participant(tournament=tournament, user=self.user)
        player2 = self.make_participant(tournament=tournament, user=self.second_user)
        unrelated = self.make_participant(tournament=tournament, user=self.third_user)
        match = Match(
            tournament=tournament,
            round=1,
            position=1,
            player1=player1,
            player2=player2,
            winner=unrelated,
        )

        with self.assertRaises(ValidationError):
            match.full_clean()

    def test_next_match_validation(self):
        tournament = self.make_tournament()
        next_match = Match.objects.create(tournament=tournament, round=2, position=1)
        missing_slot = Match(
            tournament=tournament,
            round=1,
            position=1,
            next_match=next_match,
        )
        slot_without_match = Match(
            tournament=tournament,
            round=1,
            position=2,
            next_match_slot=Match.NextMatchSlot.PLAYER1,
        )

        with self.assertRaises(ValidationError):
            missing_slot.full_clean()
        with self.assertRaises(ValidationError):
            slot_without_match.full_clean()
