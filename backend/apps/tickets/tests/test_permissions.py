from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType
from apps.tickets.permissions import IsEventOrganizerOrAdminForTicketType

User = get_user_model()


class TicketTypePermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Permission Events")
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
            title="Permission Event",
            description="Event",
            category=cls.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.ticket_type = TicketType.objects.create(
            event=cls.event,
            name="Standard",
            price=Decimal("10.00"),
            quantity=100,
        )

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def view_for(self, action, event_id=None):
        kwargs = {}
        if event_id is not None:
            kwargs["event_id"] = event_id
        return SimpleNamespace(action=action, kwargs=kwargs)

    def test_create_permission_allows_event_organizer_admin_and_superuser(self):
        permission = IsEventOrganizerOrAdminForTicketType()
        view = self.view_for("create", self.event.id)

        self.assertTrue(permission.has_permission(self.request_for(self.organizer), view))
        self.assertTrue(permission.has_permission(self.request_for(self.admin), view))
        self.assertTrue(
            permission.has_permission(self.request_for(self.superuser), view)
        )

    def test_create_permission_denies_regular_and_other_organizer(self):
        permission = IsEventOrganizerOrAdminForTicketType()
        view = self.view_for("create", self.event.id)

        self.assertFalse(
            permission.has_permission(self.request_for(self.regular_user), view)
        )
        self.assertFalse(
            permission.has_permission(self.request_for(self.other_organizer), view)
        )

    def test_object_permission_allows_owner_admin_and_superuser(self):
        permission = IsEventOrganizerOrAdminForTicketType()

        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.organizer),
                None,
                self.ticket_type,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.admin),
                None,
                self.ticket_type,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.superuser),
                None,
                self.ticket_type,
            )
        )

    def test_object_permission_denies_regular_and_other_organizer(self):
        permission = IsEventOrganizerOrAdminForTicketType()

        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.regular_user),
                None,
                self.ticket_type,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.other_organizer),
                None,
                self.ticket_type,
            )
        )
