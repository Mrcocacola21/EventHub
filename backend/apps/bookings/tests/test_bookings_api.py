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
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

User = get_user_model()


class BookingApiTests(TempMediaRootMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Booking API Events")
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
        cls.other_event = cls.make_event(
            title="Other Event",
            organizer=cls.other_organizer,
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

    def results(self, response):
        return response.data.get("results", response.data)

    def result_ids(self, response):
        return [item["id"] for item in self.results(response)]

    def test_anonymous_cannot_create_booking(self):
        ticket_type = self.make_ticket_type()

        response = self.client.post(
            reverse("booking-list"),
            {"ticket_type_id": ticket_type.id},
            format="json",
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_authenticated_user_can_create_booking(self):
        self.client.force_authenticate(self.user)
        ticket_type = self.make_ticket_type()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("booking-list"),
                {"ticket_type_id": ticket_type.id},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket_type.refresh_from_db()
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["status"], Booking.Status.PAID)
        self.assertEqual(ticket_type.sold_count, 1)
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.BOOKING_CREATED,
                entity_type="Booking",
                entity_id=str(response.data["id"]),
            ).exists()
        )

    def test_user_and_server_fields_cannot_be_overridden_on_create(self):
        self.client.force_authenticate(self.user)
        ticket_type = self.make_ticket_type(price=Decimal("17.00"))

        response = self.client.post(
            reverse("booking-list"),
            {
                "ticket_type_id": ticket_type.id,
                "user": self.another_user.id,
                "status": Booking.Status.CANCELED,
                "price_at_purchase": "0.00",
                "is_used": True,
                "qr_code": "manual.png",
                "pdf_ticket": "manual.pdf",
                "sold_count": 100,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        ticket_type.refresh_from_db()
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertEqual(booking.price_at_purchase, Decimal("17.00"))
        self.assertFalse(booking.is_used)
        self.assertTrue(booking.qr_code)
        self.assertTrue(booking.pdf_ticket)
        self.assertNotEqual(booking.qr_code.name, "manual.png")
        self.assertNotEqual(booking.pdf_ticket.name, "manual.pdf")
        self.assertEqual(ticket_type.sold_count, 1)

    def test_cannot_create_booking_if_ticket_type_sold_out(self):
        self.client.force_authenticate(self.user)
        ticket_type = self.make_ticket_type(quantity=1, sold_count=1)

        response = self.client.post(
            reverse("booking-list"),
            {"ticket_type_id": ticket_type.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_booking_for_inactive_ticket_type(self):
        self.client.force_authenticate(self.user)
        ticket_type = self.make_ticket_type(is_active=False)

        response = self.client.post(
            reverse("booking-list"),
            {"ticket_type_id": ticket_type.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_booking_for_draft_canceled_or_finished_event(self):
        self.client.force_authenticate(self.user)
        draft_ticket = self.make_ticket_type(event=self.draft_event, name="Draft")
        canceled_ticket = self.make_ticket_type(
            event=self.canceled_event,
            name="Canceled",
        )
        finished_ticket = self.make_ticket_type(
            event=self.finished_event,
            name="Finished",
        )

        for ticket_type in (draft_ticket, canceled_ticket, finished_ticket):
            response = self.client.post(
                reverse("booking-list"),
                {"ticket_type_id": ticket_type.id},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_booking_without_ticket_type_id(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("booking-list"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ticket_type_id", response.data)

    def test_cannot_create_booking_with_unknown_ticket_type_id(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("booking-list"),
            {"ticket_type_id": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ticket_type_id", response.data)

    def test_my_bookings_requires_authentication(self):
        response = self.client.get(reverse("booking-my"))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_user_sees_only_own_bookings_in_my_endpoint(self):
        own = self.make_booking(user=self.user)
        other = self.make_booking(
            user=self.another_user,
            ticket_type=self.make_ticket_type(name="Other"),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("booking-my"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self.result_ids(response)
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)
        self.assertIn("ticket_type_detail", self.results(response)[0])
        self.assertIn("event", self.results(response)[0])

    def test_my_bookings_are_ordered_by_newest_first(self):
        older = self.make_booking(user=self.user)
        newer = self.make_booking(
            user=self.user,
            ticket_type=self.make_ticket_type(name="Newest"),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("booking-my"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self.result_ids(response)
        self.assertLess(ids.index(newer.id), ids.index(older.id))

    def test_owner_can_retrieve_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.admin)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_event_organizer_can_retrieve_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.organizer)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_another_user_cannot_retrieve_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.another_user)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_another_organizer_cannot_retrieve_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.other_organizer)

        response = self.client.get(reverse("booking-detail", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_cancel_booking(self):
        ticket_type = self.make_ticket_type(sold_count=1)
        booking = self.make_booking(user=self.user, ticket_type=ticket_type)
        self.client.force_authenticate(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        ticket_type.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELED)
        self.assertEqual(ticket_type.sold_count, 0)
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type=Notification.Type.BOOKING_CANCELED,
                entity_type="Booking",
                entity_id=str(booking.id),
            ).exists()
        )

    def test_admin_can_cancel_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.admin)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_event_organizer_can_cancel_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_another_user_cannot_cancel_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.another_user)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_cancel_booking(self):
        booking = self.make_booking(user=self.user)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_another_organizer_cannot_cancel_booking(self):
        booking = self.make_booking(user=self.user)
        self.client.force_authenticate(self.other_organizer)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_cancel_already_canceled_booking(self):
        booking = self.make_booking(
            user=self.user,
            status=Booking.Status.CANCELED,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_cancel_used_booking(self):
        booking = self.make_booking(user=self.user, is_used=True)
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_cancel_expired_booking(self):
        booking = self.make_booking(user=self.user, status=Booking.Status.EXPIRED)
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("booking-cancel", args=[booking.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
