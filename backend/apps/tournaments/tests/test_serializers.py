from datetime import timedelta

from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import serializers

from apps.events.models import Event
from apps.tournaments.models import Match, Participant, Tournament
from apps.tournaments.serializers import (
    MatchSerializer,
    ParticipantSerializer,
    TournamentSerializer,
)

from .utils import TournamentTestMixin


class TournamentSerializerTests(TournamentTestMixin, TestCase):
    def request(self, user):
        request = RequestFactory().post("/")
        request.user = user
        return request

    def test_organizer_can_create_for_own_published_event(self):
        event = self.make_event(organizer=self.organizer)
        serializer = TournamentSerializer(
            data={"event": event.id, "title": "Own Cup"},
            context={"request": self.request(self.organizer)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_organizer_cannot_create_for_other_organizer_event(self):
        event = self.make_event(organizer=self.other_organizer)
        serializer = TournamentSerializer(
            data={"event": event.id, "title": "Blocked Cup"},
            context={"request": self.request(self.organizer)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_admin_can_create_for_any_published_event(self):
        event = self.make_event(organizer=self.other_organizer)
        serializer = TournamentSerializer(
            data={"event": event.id, "title": "Admin Cup"},
            context={"request": self.request(self.admin_user)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_regular_user_cannot_create(self):
        event = self.make_event()
        serializer = TournamentSerializer(
            data={"event": event.id, "title": "User Cup"},
            context={"request": self.request(self.user)},
        )

        self.assertFalse(serializer.is_valid())

    def test_event_cannot_be_changed_after_create(self):
        tournament = self.make_tournament()
        other_event = self.make_event(title="Other Event")
        serializer = TournamentSerializer(
            tournament,
            data={"event": other_event.id, "title": "Changed"},
            partial=True,
            context={"request": self.request(self.organizer)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_status_is_read_only_on_patch(self):
        tournament = self.make_tournament()
        serializer = TournamentSerializer(
            tournament,
            data={"status": Tournament.Status.CANCELED, "title": "Still Active"},
            partial=True,
            context={"request": self.request(self.organizer)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.status, Tournament.Status.DRAFT)

    def test_validation_checks_max_participants_and_deadline(self):
        event = self.make_event()
        serializer = TournamentSerializer(
            data={
                "event": event.id,
                "title": "Invalid Cup",
                "max_participants": 1,
                "registration_deadline": (
                    event.start_datetime + timedelta(minutes=1)
                ).isoformat(),
            },
            context={"request": self.request(self.organizer)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("max_participants", serializer.errors)
        self.assertIn("registration_deadline", serializer.errors)


class ParticipantSerializerTests(TournamentTestMixin, TestCase):
    def request(self, user):
        request = RequestFactory().post("/")
        request.user = user
        return request

    def test_duplicate_participant_validation(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.make_participant(tournament=tournament, user=self.user)
        serializer = ParticipantSerializer(
            data={"user": self.user.id},
            context={"request": self.request(self.organizer), "tournament": tournament},
        )

        self.assertFalse(serializer.is_valid())

    def test_max_participants_validation(self):
        tournament = self.make_tournament(
            status=Tournament.Status.REGISTRATION_OPEN,
            max_participants=2,
        )
        self.make_participant(tournament=tournament, user=self.user)
        self.make_participant(tournament=tournament, user=self.second_user)
        serializer = ParticipantSerializer(
            data={"user": self.third_user.id},
            context={"request": self.request(self.organizer), "tournament": tournament},
        )

        self.assertFalse(serializer.is_valid())


class MatchSerializerTests(TournamentTestMixin, TestCase):
    def test_players_must_belong_to_tournament(self):
        tournament = self.make_tournament()
        other_tournament = self.make_tournament(title="Other")
        other_player = self.make_participant(
            tournament=other_tournament,
            user=self.user,
        )
        serializer = MatchSerializer(
            data={"round": 1, "position": 1, "player1": other_player.id},
            context={"tournament": tournament},
        )

        self.assertFalse(serializer.is_valid())

    def test_winner_must_be_player1_or_player2(self):
        tournament = self.make_tournament()
        player1 = self.make_participant(tournament=tournament, user=self.user)
        player2 = self.make_participant(tournament=tournament, user=self.second_user)
        winner = self.make_participant(tournament=tournament, user=self.third_user)
        serializer = MatchSerializer(
            data={
                "round": 1,
                "position": 1,
                "player1": player1.id,
                "player2": player2.id,
                "winner": winner.id,
            },
            context={"tournament": tournament},
        )

        self.assertFalse(serializer.is_valid())
