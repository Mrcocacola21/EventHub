from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bookings.models import Booking
from apps.bookings.services import BookingService
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingServiceTests(TempMediaRootMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Service Events")
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        cls.another_user = User.objects.create_user(
            email="another@example.com",
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
        cls.published_event = cls.make_event(
            title="Published Event",
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.draft_event = cls.make_event(
            title="Draft Event",
            organizer=cls.organizer,
        )
        cls.canceled_event = cls.make_event(
            title="Canceled Event",
            organizer=cls.organizer,
            status=Event.Status.CANCELED,
        )
        cls.finished_event = cls.make_event(
            title="Finished Event",
            organizer=cls.organizer,
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

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.published_event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None)
        if ticket_type is None:
            ticket_type = self.make_ticket_type()
        ticket_type.sold_count = max(ticket_type.sold_count, 1)
        ticket_type.save(update_fields=["sold_count", "updated_at"])
        data = {
            "user": self.user,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def test_authenticated_user_can_create_booking_for_available_ticket_type(self):
        ticket_type = self.make_ticket_type()

        booking = BookingService.create_booking(
            user=self.user,
            ticket_type_id=ticket_type.id,
        )

        ticket_type.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertEqual(booking.price_at_purchase, Decimal("10.00"))
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.pdf_ticket)
        self.assertEqual(ticket_type.sold_count, 1)

    def test_anonymous_user_cannot_create_booking(self):
        ticket_type = self.make_ticket_type()

        with self.assertRaises(ValidationError):
            BookingService.create_booking(
                user=AnonymousUser(),
                ticket_type_id=ticket_type.id,
            )

    def test_cannot_book_inactive_ticket_type(self):
        ticket_type = self.make_ticket_type(is_active=False)

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_sold_out_ticket_type(self):
        ticket_type = self.make_ticket_type(quantity=1, sold_count=1)

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_ticket_type_for_draft_event(self):
        ticket_type = self.make_ticket_type(event=self.draft_event)

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_ticket_type_for_canceled_event(self):
        ticket_type = self.make_ticket_type(event=self.canceled_event)

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_ticket_type_for_finished_event(self):
        ticket_type = self.make_ticket_type(event=self.finished_event)

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_after_sales_end(self):
        ticket_type = self.make_ticket_type(
            sales_end=timezone.now() - timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_cannot_book_before_sales_start(self):
        ticket_type = self.make_ticket_type(
            sales_start=timezone.now() + timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.user, ticket_type.id)

    def test_price_at_purchase_is_snapshot(self):
        ticket_type = self.make_ticket_type(price=Decimal("15.00"))

        booking = BookingService.create_booking(self.user, ticket_type.id)
        ticket_type.price = Decimal("25.00")
        ticket_type.save(update_fields=["price", "updated_at"])
        booking.refresh_from_db()

        self.assertEqual(booking.price_at_purchase, Decimal("15.00"))

    def test_sequential_overselling_protection(self):
        ticket_type = self.make_ticket_type(quantity=1, sold_count=0)

        first_booking = BookingService.create_booking(self.user, ticket_type.id)
        with self.assertRaises(ValidationError):
            BookingService.create_booking(self.another_user, ticket_type.id)

        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.sold_count, 1)
        self.assertEqual(
            Booking.objects.filter(ticket_type=ticket_type).count(),
            1,
        )
        self.assertEqual(first_booking.ticket_type_id, ticket_type.id)

    def test_owner_can_cancel_own_booking(self):
        booking = self.make_booking()

        canceled = BookingService.cancel_booking(booking, self.user)

        booking.refresh_from_db()
        self.assertEqual(canceled.status, Booking.Status.CANCELED)
        self.assertEqual(booking.status, Booking.Status.CANCELED)

    def test_admin_can_cancel_any_booking(self):
        booking = self.make_booking(user=self.another_user)

        canceled = BookingService.cancel_booking(booking, self.admin)

        self.assertEqual(canceled.status, Booking.Status.CANCELED)

    def test_event_organizer_can_cancel_booking_for_own_event(self):
        booking = self.make_booking(user=self.another_user)

        canceled = BookingService.cancel_booking(booking, self.organizer)

        self.assertEqual(canceled.status, Booking.Status.CANCELED)

    def test_another_user_cannot_cancel_booking(self):
        booking = self.make_booking()

        with self.assertRaises(PermissionDenied):
            BookingService.cancel_booking(booking, self.another_user)

    def test_another_organizer_cannot_cancel_booking_for_other_event(self):
        booking = self.make_booking(user=self.another_user)

        with self.assertRaises(PermissionDenied):
            BookingService.cancel_booking(booking, self.other_organizer)

    def test_cancel_decreases_sold_count_by_one(self):
        ticket_type = self.make_ticket_type(sold_count=3)
        booking = self.make_booking(ticket_type=ticket_type)

        BookingService.cancel_booking(booking, self.user)

        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.sold_count, 2)

    def test_cancel_does_not_decrease_sold_count_below_zero(self):
        ticket_type = self.make_ticket_type(sold_count=0)
        booking = Booking.objects.create(
            user=self.user,
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=ticket_type.price,
        )

        BookingService.cancel_booking(booking, self.user)

        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.sold_count, 0)

    def test_cannot_cancel_already_canceled_booking(self):
        booking = self.make_booking(status=Booking.Status.CANCELED)

        with self.assertRaises(ValidationError):
            BookingService.cancel_booking(booking, self.user)

    def test_cannot_cancel_used_booking(self):
        booking = self.make_booking(is_used=True)

        with self.assertRaises(ValidationError):
            BookingService.cancel_booking(booking, self.user)

    def test_cannot_cancel_expired_booking(self):
        booking = self.make_booking(status=Booking.Status.EXPIRED)

        with self.assertRaises(ValidationError):
            BookingService.cancel_booking(booking, self.user)
