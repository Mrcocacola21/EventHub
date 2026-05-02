from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.admin import EventAdmin, EventCategoryAdmin, TicketTypeInline
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

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

    def test_event_category_admin_configuration(self):
        category_admin = admin.site._registry[EventCategory]

        self.assertIn("events_count", category_admin.list_display)
        self.assertIn("created_at", category_admin.list_filter)
        self.assertIn("description", category_admin.search_fields)
        self.assertEqual(category_admin.prepopulated_fields, {"slug": ("name",)})
        self.assertIn("created_at", category_admin.readonly_fields)
        self.assertIn("updated_at", category_admin.readonly_fields)

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
            "start_datetime",
        ):
            self.assertIn(field_name, event_admin.list_display)

        self.assertIn("status", event_admin.list_filter)
        self.assertIn("is_published", event_admin.list_filter)
        self.assertIn("category", event_admin.list_filter)
        self.assertIn("title", event_admin.search_fields)
        self.assertIn("organizer__email", event_admin.search_fields)
        self.assertIn("category__name", event_admin.search_fields)
        self.assertIn("slug", event_admin.readonly_fields)
        self.assertIn("created_at", event_admin.readonly_fields)
        self.assertIn("updated_at", event_admin.readonly_fields)
        self.assertIn("publish_events", event_admin.actions)
        self.assertIn("cancel_events", event_admin.actions)
        self.assertIn("finish_events", event_admin.actions)
        self.assertIn("mark_as_draft", event_admin.actions)
        self.assertEqual(event_admin.date_hierarchy, "start_datetime")
        self.assertEqual(event_admin.list_select_related, ("organizer", "category"))

    def test_event_admin_contains_ticket_type_inline(self):
        event_admin = admin.site._registry[Event]

        self.assertIn(TicketTypeInline, event_admin.inlines)
        self.assertIn("sold_count", TicketTypeInline.readonly_fields)
        self.assertIn("available_quantity_display", TicketTypeInline.readonly_fields)
        self.assertTrue(TicketTypeInline.show_change_link)

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

    def test_cancel_action_creates_event_canceled_notifications_on_commit(self):
        event_admin = admin.site._registry[Event]
        event = self.make_event(
            title="Notify From Admin",
            status=Event.Status.PUBLISHED,
        )
        ticket_type = TicketType.objects.create(
            event=event,
            name="Standard",
            price=Decimal("10.00"),
            quantity=10,
            sold_count=1,
        )
        Booking.objects.create(
            user=self.organizer,
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=ticket_type.price,
        )

        with self.captureOnCommitCallbacks(execute=True):
            event_admin.cancel_events(self.request(), Event.objects.filter(id=event.id))

        self.assertTrue(
            Notification.objects.filter(
                user=self.organizer,
                type=Notification.Type.EVENT_CANCELED,
                entity_type="Event",
                entity_id=str(event.id),
            ).exists()
        )

    def test_mark_as_draft_action_updates_status_and_publication_flag(self):
        event_admin = admin.site._registry[Event]
        event = self.make_event(
            title="Draft From Admin",
            status=Event.Status.PUBLISHED,
        )

        event_admin.mark_as_draft(self.request(), Event.objects.filter(id=event.id))

        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.DRAFT)
        self.assertFalse(event.is_published)
