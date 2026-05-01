from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingPDFDownloadApiTests(TempMediaRootMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="PDF Download Events")
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

    def download_url(self, booking):
        return reverse("booking-download-pdf", args=[booking.id])

    def response_body(self, response):
        return b"".join(response.streaming_content)

    def test_anonymous_cannot_download_pdf(self):
        booking = self.make_booking()

        response = self.client.get(self.download_url(booking))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_owner_can_download_pdf(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.owner)

        response = self.client.get(self.download_url(booking))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(self.response_body(response).startswith(b"%PDF"))

    def test_another_user_cannot_download_pdf(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.another_user)

        response = self.client.get(self.download_url(booking))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_organizer_can_download_pdf(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.organizer)

        response = self.client.get(self.download_url(booking))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.response_body(response).startswith(b"%PDF"))

    def test_another_organizer_cannot_download_pdf(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.other_organizer)

        response = self.client.get(self.download_url(booking))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_download_pdf(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.download_url(booking))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.response_body(response).startswith(b"%PDF"))

    def test_download_generates_pdf_if_missing(self):
        booking = self.make_booking()
        self.assertFalse(booking.pdf_ticket)
        self.client.force_authenticate(self.owner)

        response = self.client.get(self.download_url(booking))

        booking.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(booking.pdf_ticket)
        self.assertTrue(self.response_body(response).startswith(b"%PDF"))
