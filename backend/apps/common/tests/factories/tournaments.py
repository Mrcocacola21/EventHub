import factory

from apps.tournaments.models import Match, Participant, Tournament

from .events import PublishedEventFactory
from .users import UserFactory


class TournamentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tournament

    event = factory.SubFactory(PublishedEventFactory)
    title = factory.Sequence(lambda n: f"Tournament {n}")
    type = Tournament.Type.SINGLE_ELIMINATION
    status = Tournament.Status.DRAFT
    max_participants = 16


class RegistrationOpenTournamentFactory(TournamentFactory):
    status = Tournament.Status.REGISTRATION_OPEN


class ParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Participant

    tournament = factory.SubFactory(RegistrationOpenTournamentFactory)
    user = factory.SubFactory(UserFactory)
    seed = factory.Sequence(lambda n: n + 1)
    status = Participant.Status.REGISTERED


class MatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Match

    tournament = factory.SubFactory(TournamentFactory)
    round = 1
    position = factory.Sequence(lambda n: n + 1)
    status = Match.Status.PENDING
