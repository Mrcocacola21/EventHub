from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.events.admin import EventAdmin, TicketTypeInline
from apps.events.models import Event, EventCategory
from apps.tickets.admin import TicketTypeAdmin
from apps.tickets.models import TicketType

User = get_user_model()


class TicketTypeAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Admin Ticket Events")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin_user = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )
        cls.event = cls.make_event(
            title="Published Event",
            status=Event.Status.PUBLISHED,
        )
        cls.canceled_event = cls.make_event(
            title="Canceled Event",
            status=Event.Status.CANCELED,
        )
        cls.finished_event = cls.make_event(
            title="Finished Event",
            status=Event.Status.FINISHED,
        )

    @classmethod
    def make_event(cls, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Event",
            "description": "Event description",
            "category": cls.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": cls.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def test_ticket_type_admin_is_registered(self):
        self.assertIsInstance(admin.site._registry[TicketType], TicketTypeAdmin)

    def test_event_admin_contains_ticket_type_inline(self):
        event_admin = admin.site._registry[Event]

        self.assertIsInstance(event_admin, EventAdmin)
        self.assertIn(TicketTypeInline, event_admin.inlines)

    def test_ticket_type_admin_readonly_fields_include_sold_count(self):
        ticket_type_admin = admin.site._registry[TicketType]

        self.assertIn("sold_count", ticket_type_admin.readonly_fields)
        self.assertIn("created_at", ticket_type_admin.readonly_fields)
        self.assertIn("updated_at", ticket_type_admin.readonly_fields)

    def test_ticket_type_admin_configuration_exposes_expected_controls(self):
        ticket_type_admin = admin.site._registry[TicketType]

        for field_name in (
            "event",
            "name",
            "price",
            "quantity",
            "sold_count",
            "available_quantity_display",
            "is_active",
        ):
            self.assertIn(field_name, ticket_type_admin.list_display)

        self.assertIn("is_active", ticket_type_admin.list_filter)
        self.assertIn("event__status", ticket_type_admin.list_filter)
        self.assertIn("name", ticket_type_admin.search_fields)
        self.assertIn("event__title", ticket_type_admin.search_fields)
        self.assertIn("event__organizer__email", ticket_type_admin.search_fields)
        self.assertIn("deactivate_ticket_types", ticket_type_admin.actions)
        self.assertIn("activate_ticket_types", ticket_type_admin.actions)
        self.assertEqual(
            ticket_type_admin.list_select_related,
            ("event", "event__organizer", "event__category"),
        )
        self.assertEqual(ticket_type_admin.date_hierarchy, "created_at")
        self.assertEqual(
            ticket_type_admin.ordering,
            ("event__start_datetime", "price", "name"),
        )

    def test_admin_actions_deactivate_and_activate_ticket_types(self):
        ticket_type_admin = admin.site._registry[TicketType]
        active = self.make_ticket_type(name="Active", is_active=True)
        inactive = self.make_ticket_type(name="Inactive", is_active=False)
        canceled = self.make_ticket_type(
            event=self.canceled_event,
            name="Canceled",
            is_active=False,
        )
        finished = self.make_ticket_type(
            event=self.finished_event,
            name="Finished",
            is_active=False,
        )

        ticket_type_admin.deactivate_ticket_types(
            self.request(),
            TicketType.objects.filter(id=active.id),
        )
        ticket_type_admin.activate_ticket_types(
            self.request(),
            TicketType.objects.filter(id__in=(inactive.id, canceled.id, finished.id)),
        )

        active.refresh_from_db()
        inactive.refresh_from_db()
        canceled.refresh_from_db()
        finished.refresh_from_db()
        self.assertFalse(active.is_active)
        self.assertTrue(inactive.is_active)
        self.assertFalse(canceled.is_active)
        self.assertFalse(finished.is_active)
