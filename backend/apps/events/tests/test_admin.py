from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone

from apps.events.admin import EventAdmin, EventCategoryAdmin
from apps.events.models import Event, EventCategory

User = get_user_model()


class EventAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Admin Events")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin_user = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )

    def make_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Admin Managed Event",
            "description": "Managed from admin",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": self.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def test_event_category_admin_is_registered(self):
        self.assertIsInstance(
            admin.site._registry[EventCategory],
            EventCategoryAdmin,
        )

    def test_event_admin_is_registered(self):
        self.assertIsInstance(admin.site._registry[Event], EventAdmin)

    def test_event_admin_configuration_exposes_expected_controls(self):
        event_admin = admin.site._registry[Event]

        for field_name in (
            "title",
            "organizer",
            "category",
            "status",
            "is_published",
        ):
            self.assertIn(field_name, event_admin.list_display)

        self.assertIn("status", event_admin.list_filter)
        self.assertIn("title", event_admin.search_fields)
        self.assertIn("organizer__email", event_admin.search_fields)
        self.assertIn("publish_events", event_admin.actions)
        self.assertIn("cancel_events", event_admin.actions)
        self.assertIn("finish_events", event_admin.actions)

    def test_admin_actions_use_event_state_methods(self):
        event_admin = admin.site._registry[Event]
        draft = self.make_event(title="Publish From Admin")
        published_for_cancel = self.make_event(
            title="Cancel From Admin",
            status=Event.Status.PUBLISHED,
        )
        published_for_finish = self.make_event(
            title="Finish From Admin",
            status=Event.Status.PUBLISHED,
        )

        event_admin.publish_events(self.request(), Event.objects.filter(id=draft.id))
        event_admin.cancel_events(
            self.request(),
            Event.objects.filter(id=published_for_cancel.id),
        )
        event_admin.finish_events(
            self.request(),
            Event.objects.filter(id=published_for_finish.id),
        )

        draft.refresh_from_db()
        published_for_cancel.refresh_from_db()
        published_for_finish.refresh_from_db()
        self.assertEqual(draft.status, Event.Status.PUBLISHED)
        self.assertTrue(draft.is_published)
        self.assertEqual(published_for_cancel.status, Event.Status.CANCELED)
        self.assertFalse(published_for_cancel.is_published)
        self.assertEqual(published_for_finish.status, Event.Status.FINISHED)
        self.assertFalse(published_for_finish.is_published)
