from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.bookings.models import Booking
from apps.bookings.tests.utils import TempMediaRootMixin
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class BookingAuditTests(TempMediaRootMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Audit Booking Events")
        cls.user = User.objects.create_user(
            email="audit-booking-user@example.com",
            password="StrongPass123!",
        )
        cls.organizer = User.objects.create_user(
            email="audit-booking-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        start = timezone.now() + timedelta(days=2)
        cls.event = Event.objects.create(
            title="Audit Booking Event",
            description="Audit booking event",
            category=cls.category,
            location="Kyiv",
            start_datetime=start,
            end_datetime=start + timedelta(hours=2),
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 10,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, **overrides):
        ticket_type = overrides.pop("ticket_type", None) or self.make_ticket_type()
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

    def assert_booking_log(self, *, action, booking, user, request_id):
        log = AuditLog.objects.get(action=action)

        self.assertEqual(log.user, user)
        self.assertEqual(log.entity_type, "Booking")
        self.assertEqual(log.entity_id, str(booking.id))
        self.assertEqual(log.request_id, request_id)
        self.assertEqual(log.metadata["user_id"], booking.user_id)
        self.assertEqual(log.metadata["ticket_type_id"], booking.ticket_type_id)
        self.assertEqual(log.metadata["event_id"], booking.ticket_type.event_id)
        self.assertEqual(log.metadata["status"], booking.status)
        self.assertEqual(log.metadata["price_at_purchase"], "10.00")

    def test_create_booking_writes_audit_log(self):
        ticket_type = self.make_ticket_type()
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("booking-list"),
            {"ticket_type_id": ticket_type.id},
            format="json",
            HTTP_X_REQUEST_ID="booking-created-request",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assert_booking_log(
            action=AuditLog.Action.BOOKING_CREATED,
            booking=booking,
            user=self.user,
            request_id="booking-created-request",
        )

    def test_cancel_booking_writes_audit_log(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("booking-cancel", args=[booking.id]),
            HTTP_X_REQUEST_ID="booking-canceled-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assert_booking_log(
            action=AuditLog.Action.BOOKING_CANCELED,
            booking=booking,
            user=self.user,
            request_id="booking-canceled-request",
        )

    def test_use_booking_writes_audit_log(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("booking-use", args=[booking.id]),
            HTTP_X_REQUEST_ID="booking-used-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assert_booking_log(
            action=AuditLog.Action.BOOKING_USED,
            booking=booking,
            user=self.organizer,
            request_id="booking-used-request",
        )
