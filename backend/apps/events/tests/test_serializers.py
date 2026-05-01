from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.events.serializers import EventSerializer

User = get_user_model()


class EventSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Sports")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.other_organizer = User.objects.create_user(
            email="other-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )

    def payload(self, **overrides):
        start = timezone.now() + timedelta(days=3)
        data = {
            "title": "City Tournament",
            "description": "Open event",
            "category": self.category.id,
            "location": "Lviv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=3),
            "max_participants": 32,
        }
        data.update(overrides)
        return data

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_organizer_is_set_from_request_user(self):
        serializer = EventSerializer(
            data=self.payload(organizer=self.other_organizer.id),
            context={"request": self.request_for(self.organizer)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        self.assertEqual(event.organizer, self.organizer)

    def test_regular_user_cannot_create_event(self):
        serializer = EventSerializer(
            data=self.payload(),
            context={"request": self.request_for(self.regular_user)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("organizer", serializer.errors)

    def test_organizer_can_create_event(self):
        serializer = EventSerializer(
            data=self.payload(),
            context={"request": self.request_for(self.organizer)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()

        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.status, Event.Status.DRAFT)

    def test_admin_can_create_event(self):
        serializer = EventSerializer(
            data=self.payload(title="Admin Event"),
            context={"request": self.request_for(self.admin)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_end_datetime_validation_works(self):
        start = timezone.now() + timedelta(days=1)
        serializer = EventSerializer(
            data=self.payload(start_datetime=start, end_datetime=start),
            context={"request": self.request_for(self.organizer)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("end_datetime", serializer.errors)

    def test_max_participants_must_be_greater_than_zero(self):
        serializer = EventSerializer(
            data=self.payload(max_participants=0),
            context={"request": self.request_for(self.organizer)},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("max_participants", serializer.errors)

    def test_status_cannot_be_changed_directly_through_patch(self):
        start = timezone.now() + timedelta(days=2)
        event = Event.objects.create(
            title="Draft Event",
            description="Draft",
            category=self.category,
            location="Odesa",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=self.organizer,
        )
        serializer = EventSerializer(
            event,
            data={"status": Event.Status.PUBLISHED, "is_published": True},
            partial=True,
            context={"request": self.request_for(self.organizer)},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        event.refresh_from_db()

        self.assertEqual(event.status, Event.Status.DRAFT)
        self.assertFalse(event.is_published)
