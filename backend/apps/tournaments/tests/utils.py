from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.events.models import Event, EventCategory

User = get_user_model()


class TournamentTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Tournament Events")
        cls.user = User.objects.create_user(
            email="tournament-user@example.com",
            password="StrongPass123!",
        )
        cls.second_user = User.objects.create_user(
            email="second-user@example.com",
            password="StrongPass123!",
        )
        cls.third_user = User.objects.create_user(
            email="third-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="tournament-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.other_organizer = User.objects.create_user(
            email="other-tournament-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin_user = User.objects.create_user(
            email="tournament-admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Tournament Event",
            "description": "Tournament event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_tournament(self, **overrides):
        from apps.tournaments.models import Tournament

        event = overrides.pop("event", None) or self.make_event()
        data = {
            "event": event,
            "title": "City Championship",
            "type": Tournament.Type.SINGLE_ELIMINATION,
        }
        data.update(overrides)
        return Tournament.objects.create(**data)

    def make_participant(self, tournament=None, user=None, **overrides):
        from apps.tournaments.models import Participant

        data = {
            "tournament": tournament or self.make_tournament(),
            "user": user or self.user,
        }
        data.update(overrides)
        return Participant.objects.create(**data)
