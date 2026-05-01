from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.permissions import (
    CanUseBookingTicket,
    IsBookingOwnerOrAdminOrEventOrganizer,
)
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Permission Bookings")
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
        )
        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
        )
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
            quantity=10,
            sold_count=1,
        )
        cls.booking = Booking.objects.create(
            user=cls.owner,
            ticket_type=cls.ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=cls.ticket_type.price,
        )

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_permission_allows_owner(self):
        self.assertTrue(
            IsBookingOwnerOrAdminOrEventOrganizer().has_object_permission(
                self.request_for(self.owner),
                None,
                self.booking,
            )
        )

    def test_permission_allows_admin(self):
        self.assertTrue(
            IsBookingOwnerOrAdminOrEventOrganizer().has_object_permission(
                self.request_for(self.admin),
                None,
                self.booking,
            )
        )

    def test_permission_allows_event_organizer(self):
        self.assertTrue(
            IsBookingOwnerOrAdminOrEventOrganizer().has_object_permission(
                self.request_for(self.organizer),
                None,
                self.booking,
            )
        )

    def test_permission_denies_another_user(self):
        self.assertFalse(
            IsBookingOwnerOrAdminOrEventOrganizer().has_object_permission(
                self.request_for(self.other_user),
                None,
                self.booking,
            )
        )

    def test_permission_denies_another_organizer(self):
        self.assertFalse(
            IsBookingOwnerOrAdminOrEventOrganizer().has_object_permission(
                self.request_for(self.other_organizer),
                None,
                self.booking,
            )
        )

    def test_can_use_permission_allows_admin_and_event_organizer(self):
        permission = CanUseBookingTicket()

        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.admin),
                None,
                self.booking,
            )
        )
        self.assertTrue(
            permission.has_object_permission(
                self.request_for(self.organizer),
                None,
                self.booking,
            )
        )

    def test_can_use_permission_denies_owner_regular_user_and_other_organizer(self):
        permission = CanUseBookingTicket()

        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.owner),
                None,
                self.booking,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.other_user),
                None,
                self.booking,
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.other_organizer),
                None,
                self.booking,
            )
        )
