from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class TicketTypeApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="API Events")
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
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
        cls.other_published_event = cls.make_event(
            title="Other Published Event",
            organizer=cls.other_organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.other_draft_event = cls.make_event(
            title="Other Draft Event",
            organizer=cls.other_organizer,
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
            "description": "Base access",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def payload(self, **overrides):
        data = {
            "name": "Standard",
            "description": "Base access",
            "price": "10.00",
            "quantity": 100,
        }
        data.update(overrides)
        return data

    def list_url(self, event):
        return reverse("event-ticket-types-list", kwargs={"event_id": event.id})

    def detail_url(self, ticket_type):
        return reverse("ticket-type-detail", kwargs={"pk": ticket_type.id})

    def results(self, response):
        return response.data.get("results", response.data)

    def result_ids(self, response):
        return [item["id"] for item in self.results(response)]

    def test_anonymous_can_list_active_ticket_types_for_published_event(self):
        active = self.make_ticket_type(name="Standard", is_active=True)
        inactive = self.make_ticket_type(name="VIP", is_active=False)

        response = self.client.get(self.list_url(self.published_event))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self.result_ids(response)
        self.assertIn(active.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_anonymous_cannot_see_ticket_types_for_draft_event(self):
        ticket_type = self.make_ticket_type(event=self.draft_event)

        response = self.client.get(self.list_url(self.draft_event))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(ticket_type.id, self.result_ids(response))

    def test_anonymous_cannot_see_ticket_types_for_canceled_or_finished_event(self):
        canceled = self.make_ticket_type(
            event=self.canceled_event,
            name="Canceled",
            is_active=True,
        )
        finished = self.make_ticket_type(
            event=self.finished_event,
            name="Finished",
            is_active=True,
        )

        canceled_response = self.client.get(self.list_url(self.canceled_event))
        finished_response = self.client.get(self.list_url(self.finished_event))

        self.assertEqual(canceled_response.status_code, status.HTTP_200_OK)
        self.assertEqual(finished_response.status_code, status.HTTP_200_OK)
        self.assertNotIn(canceled.id, self.result_ids(canceled_response))
        self.assertNotIn(finished.id, self.result_ids(finished_response))

    def test_regular_user_lists_active_ticket_types_for_published_event(self):
        self.client.force_authenticate(self.regular_user)
        active = self.make_ticket_type(name="Standard", is_active=True)
        inactive = self.make_ticket_type(name="VIP", is_active=False)

        response = self.client.get(self.list_url(self.published_event))

        ids = self.result_ids(response)
        self.assertIn(active.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_organizer_sees_all_ticket_types_for_own_event(self):
        self.client.force_authenticate(self.organizer)
        active = self.make_ticket_type(name="Standard", is_active=True)
        inactive = self.make_ticket_type(name="VIP", is_active=False)

        response = self.client.get(self.list_url(self.published_event))

        ids = self.result_ids(response)
        self.assertIn(active.id, ids)
        self.assertIn(inactive.id, ids)

    def test_organizer_does_not_see_hidden_ticket_types_for_other_draft_event(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(
            event=self.other_draft_event,
            is_active=False,
        )

        response = self.client.get(self.list_url(self.other_draft_event))

        self.assertNotIn(ticket_type.id, self.result_ids(response))

    def test_admin_sees_all_ticket_types(self):
        self.client.force_authenticate(self.admin)
        active = self.make_ticket_type(event=self.draft_event, name="Standard")
        inactive = self.make_ticket_type(
            event=self.draft_event,
            name="VIP",
            is_active=False,
        )

        response = self.client.get(self.list_url(self.draft_event))

        ids = self.result_ids(response)
        self.assertIn(active.id, ids)
        self.assertIn(inactive.id, ids)

    def test_anonymous_cannot_create_ticket_type(self):
        response = self.client.post(
            self.list_url(self.published_event),
            self.payload(),
            format="json",
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_user_cannot_create_ticket_type(self):
        self.client.force_authenticate(self.regular_user)

        response = self.client.post(
            self.list_url(self.published_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_can_create_ticket_type_for_own_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url(self.published_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event"], self.published_event.id)

    def test_organizer_cannot_create_ticket_type_for_other_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url(self.other_published_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_ticket_type_for_any_event(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.list_url(self.other_published_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event"], self.other_published_event.id)

    def test_payload_event_field_cannot_override_url_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url(self.published_event),
            self.payload(event=self.other_published_event.id),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket_type = TicketType.objects.get(id=response.data["id"])
        self.assertEqual(ticket_type.event, self.published_event)

    def test_cannot_create_ticket_type_for_canceled_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url(self.canceled_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_ticket_type_for_finished_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url(self.finished_event),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_can_retrieve_active_ticket_type_for_published_event(self):
        ticket_type = self.make_ticket_type()

        response = self.client.get(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], ticket_type.id)

    def test_anonymous_cannot_retrieve_inactive_ticket_type(self):
        ticket_type = self.make_ticket_type(is_active=False)

        response = self.client.get(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_retrieve_own_inactive_ticket_type(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(is_active=False)

        response = self.client.get(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_any_ticket_type(self):
        self.client.force_authenticate(self.admin)
        ticket_type = self.make_ticket_type(event=self.draft_event, is_active=False)

        response = self.client.get(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_organizer_can_update_own_ticket_type(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type()

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"price": "12.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.price, Decimal("12.50"))

    def test_organizer_cannot_update_another_organizers_ticket_type(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(event=self.other_published_event)

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"price": "12.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_ticket_type(self):
        self.client.force_authenticate(self.admin)
        ticket_type = self.make_ticket_type(event=self.other_published_event)

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"price": "15.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.price, Decimal("15.00"))

    def test_user_cannot_update_ticket_type(self):
        self.client.force_authenticate(self.regular_user)
        ticket_type = self.make_ticket_type()

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"price": "15.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_change_event_through_payload(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type()

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"event": self.other_published_event.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.event, self.published_event)

    def test_cannot_change_sold_count_through_payload(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(sold_count=3)

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"sold_count": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket_type.refresh_from_db()
        self.assertEqual(ticket_type.sold_count, 3)

    def test_cannot_set_quantity_below_sold_count(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(quantity=10, sold_count=5)

        response = self.client.patch(
            self.detail_url(ticket_type),
            {"quantity": 4},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_can_delete_own_ticket_type_when_no_tickets_sold(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type()

        response = self.client.delete(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TicketType.objects.filter(id=ticket_type.id).exists())

    def test_cannot_delete_ticket_type_when_tickets_have_been_sold(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(sold_count=1)

        response = self.client.delete(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(TicketType.objects.filter(id=ticket_type.id).exists())

    def test_organizer_cannot_delete_another_organizers_ticket_type(self):
        self.client.force_authenticate(self.organizer)
        ticket_type = self.make_ticket_type(event=self.other_published_event)

        response = self.client.delete(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_ticket_type_when_no_tickets_sold(self):
        self.client.force_authenticate(self.admin)
        ticket_type = self.make_ticket_type(event=self.other_published_event)

        response = self.client.delete(self.detail_url(ticket_type))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TicketType.objects.filter(id=ticket_type.id).exists())
