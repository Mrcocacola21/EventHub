from django.test import TestCase

from apps.events.cache import PopularTournamentsService
from apps.tournaments.models import Tournament

from .utils import TournamentTestMixin


class PopularTournamentsServiceTests(TournamentTestMixin, TestCase):
    def test_popular_tournaments_returns_real_tournaments_sorted_by_participants(self):
        less_popular = self.make_tournament(title="Less Popular")
        more_popular = self.make_tournament(title="More Popular")
        self.make_participant(tournament=less_popular, user=self.user)
        self.make_participant(tournament=more_popular, user=self.user)
        self.make_participant(tournament=more_popular, user=self.second_user)

        result = PopularTournamentsService.get_popular(limit=10)

        self.assertEqual(result[0]["id"], more_popular.id)
        self.assertEqual(result[0]["popularity_count"], 2)
        self.assertEqual(result[1]["id"], less_popular.id)

    def test_popular_tournaments_respects_limit(self):
        first = self.make_tournament(title="First")
        second = self.make_tournament(title="Second")

        result = PopularTournamentsService.get_popular(limit=1)

        self.assertEqual(len(result), 1)
