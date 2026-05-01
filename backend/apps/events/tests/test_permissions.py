from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.events.permissions import IsEventOrganizerOrAdmin, IsOrganizerOrAdmin

User = get_user_model()


class EventPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Workshops")
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
        cls.superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        start = timezone.now() + timedelta(days=2)
        cls.event = Event.objects.create(
            title="Workshop",
            description="Workshop",
            category=cls.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=cls.organizer,
        )

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_is_organizer_or_admin_allows_organizer_admin_and_superuser(self):
        permission = IsOrganizerOrAdmin()

        self.assertTrue(
            permission.has_permission(self.request_for(self.organizer), None)
        )
        self.assertTrue(permission.has_permission(self.request_for(self.admin), None))
        self.assertTrue(
            permission.has_permission(self.request_for(self.superuser), None)
        )

    def test_is_organizer_or_admin_denies_regular_user(self):
        self.assertFalse(
            IsOrganizerOrAdmin().has_permission(
                self.request_for(self.regular_user),
                None,
            )
        )

    def test_event_object_permission_allows_event_organizer(self):
        self.assertTrue(
            IsEventOrganizerOrAdmin().has_object_permission(
                self.request_for(self.organizer),
                None,
                self.event,
            )
        )

    def test_event_object_permission_allows_admin_and_superuser(self):
        permission = IsEventOrganizerOrAdmin()

        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.admin),
                None,
                self.event,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.superuser),
                None,
                self.event,
            )
        )

    def test_event_object_permission_denies_other_users(self):
        permission = IsEventOrganizerOrAdmin()

        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.other_organizer),
                None,
                self.event,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.regular_user),
                None,
                self.event,
            )
        )
