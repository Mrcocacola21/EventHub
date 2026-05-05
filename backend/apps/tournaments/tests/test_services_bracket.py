from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.tournaments.models import Match, Participant, Tournament
from apps.tournaments.services import TournamentService

from .utils import TournamentTestMixin


class TournamentBracketServiceTests(TournamentTestMixin, APITestCase):
    def add_participants(self, tournament, count):
        users = [self.user, self.second_user, self.third_user]
        for index in range(4, count + 1):
            users.append(
                self.user.__class__.objects.create_user(
                    email=f"bracket-user-{index}@example.com",
                    password="StrongPass123!",
                )
            )

        participants = []
        for seed, user in enumerate(users[:count], start=1):
            participants.append(
                self.make_participant(
                    tournament=tournament,
                    user=user,
                    seed=seed,
                )
            )
        return participants

    def start_with_participants(self, count):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        participants = self.add_participants(tournament, count)
        TournamentService.start_tournament(tournament)
        return tournament, participants

    def test_start_requires_registration_open_and_two_participants(self):
        draft = self.make_tournament(status=Tournament.Status.DRAFT)
        open_tournament = self.make_tournament(
            title="One Player",
            status=Tournament.Status.REGISTRATION_OPEN,
        )
        self.make_participant(tournament=open_tournament, user=self.user)

        with self.assertRaises(ValidationError):
            TournamentService.start_tournament(draft)

        with self.assertRaises(ValidationError):
            TournamentService.start_tournament(open_tournament)

    def test_start_sets_tournament_and_participants_active(self):
        tournament = self.make_tournament(status=Tournament.Status.REGISTRATION_OPEN)
        self.add_participants(tournament, 2)

        TournamentService.start_tournament(tournament)

        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.IN_PROGRESS)
        self.assertEqual(
            set(tournament.participants.values_list("status", flat=True)),
            {Participant.Status.ACTIVE},
        )
        self.assertEqual(tournament.matches.count(), 1)

    def test_start_cannot_run_twice(self):
        tournament, _ = self.start_with_participants(2)

        with self.assertRaises(ValidationError):
            TournamentService.start_tournament(tournament)

    def test_two_participants_create_final_match(self):
        tournament, participants = self.start_with_participants(2)

        match = tournament.matches.get()
        self.assertEqual(match.round, 1)
        self.assertEqual(match.position, 1)
        self.assertEqual(match.player1_id, participants[0].id)
        self.assertEqual(match.player2_id, participants[1].id)
        self.assertIsNone(match.next_match_id)

    def test_four_participants_create_semifinals_and_final(self):
        tournament, _ = self.start_with_participants(4)

        self.assertEqual(tournament.matches.count(), 3)
        semifinals = list(tournament.matches.filter(round=1).order_by("position"))
        final = tournament.matches.get(round=2, position=1)

        self.assertEqual(len(semifinals), 2)
        self.assertEqual(semifinals[0].next_match_id, final.id)
        self.assertEqual(semifinals[0].next_match_slot, Match.NextMatchSlot.PLAYER1)
        self.assertEqual(semifinals[1].next_match_id, final.id)
        self.assertEqual(semifinals[1].next_match_slot, Match.NextMatchSlot.PLAYER2)

    def test_three_participants_uses_bye_and_promotes_seed_one(self):
        tournament, participants = self.start_with_participants(3)

        self.assertEqual(tournament.matches.count(), 3)
        bye_match = tournament.matches.get(round=1, position=1)
        final = tournament.matches.get(round=2, position=1)

        self.assertEqual(bye_match.status, Match.Status.FINISHED)
        self.assertEqual(bye_match.winner_id, participants[0].id)
        self.assertEqual(final.player1_id, participants[0].id)

    def test_five_participants_create_eight_slot_bracket_with_byes(self):
        tournament, participants = self.start_with_participants(5)

        self.assertEqual(tournament.matches.count(), 7)
        self.assertEqual(tournament.matches.filter(round=1).count(), 4)
        self.assertEqual(tournament.matches.filter(round=2).count(), 2)
        self.assertEqual(tournament.matches.filter(round=3).count(), 1)
        self.assertEqual(
            tournament.matches.filter(round=1, status=Match.Status.FINISHED).count(),
            3,
        )

        semifinal_one = tournament.matches.get(round=2, position=1)
        semifinal_two = tournament.matches.get(round=2, position=2)
        self.assertEqual(semifinal_one.player1_id, participants[0].id)
        self.assertEqual(semifinal_one.player2_id, participants[1].id)
        self.assertEqual(semifinal_two.player1_id, participants[2].id)
