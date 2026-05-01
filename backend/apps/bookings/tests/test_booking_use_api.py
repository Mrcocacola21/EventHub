from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingUseApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Use API Events")
        cls.owner = User.objects.create_user(
            email="owner@example.com",
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
        cls.event = cls.make_event(
            title="Published Event",
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
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
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
            "sold_count": 1,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None)
        if ticket_type is None:
            ticket_type = self.make_ticket_type()
        data = {
            "user": self.owner,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)

    def use_url(self, booking):
        return reverse("booking-use", args=[booking.id])

    def test_anonymous_cannot_use_booking(self):
        booking = self.make_booking()

        response = self.client.post(self.use_url(booking))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_ticket_owner_cannot_use_own_booking(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.owner)

        response = self.client.post(self.use_url(booking))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unrelated_regular_user_cannot_use_booking(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.another_user)

        response = self.client.post(self.use_url(booking))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_organizer_can_use_booking(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.organizer)

        response = self.client.post(self.use_url(booking))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertTrue(booking.is_used)
        self.assertIsNotNone(booking.used_at)
        self.assertTrue(response.data["is_used"])
        self.assertIsNotNone(response.data["used_at"])

    def test_admin_can_use_booking(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.admin)

        response = self.client.post(self.use_url(booking))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_another_organizer_cannot_use_booking(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.other_organizer)

        response = self.client.post(self.use_url(booking))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_repeated_use_returns_400(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.organizer)

        first_response = self.client.post(self.use_url(booking))
        booking.refresh_from_db()
        first_used_at = booking.used_at
        second_response = self.client.post(self.use_url(booking))

        booking.refresh_from_db()
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(booking.used_at, first_used_at)

    def test_canceled_and_expired_bookings_return_400(self):
        canceled = self.make_booking(status=Booking.Status.CANCELED)
        expired = self.make_booking(
            ticket_type=self.make_ticket_type(name="Expired"),
            status=Booking.Status.EXPIRED,
        )
        self.client.force_authenticate(self.organizer)

        canceled_response = self.client.post(self.use_url(canceled))
        expired_response = self.client.post(self.use_url(expired))

        self.assertEqual(canceled_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired_response.status_code, status.HTTP_400_BAD_REQUEST)
