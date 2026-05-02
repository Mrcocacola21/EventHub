from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.notifications.models import Notification
from apps.tickets.models import TicketType

User = get_user_model()


class EventApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.list_url = reverse("event-list")
        cls.category = EventCategory.objects.create(name="Meetups")
        cls.other_category = EventCategory.objects.create(name="Leagues")
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

    def window(self, days=2):
        start = timezone.now() + timedelta(days=days)
        return start, start + timedelta(hours=2)

    def event_payload(self, **overrides):
        start, end = self.window()
        data = {
            "title": "Open Meetup",
            "description": "Public event",
            "category": self.category.id,
            "location": "Kyiv",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "max_participants": 50,
        }
        data.update(overrides)
        return data

    def make_event(self, **overrides):
        start, end = self.window(overrides.pop("days", 2))
        data = {
            "title": "Open Meetup",
            "description": "Public event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": end,
            "organizer": self.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def detail_url(self, event):
        return reverse("event-detail", args=[event.id])

    def action_url(self, event, action):
        return reverse(f"event-{action}", args=[event.id])

    def results(self, response):
        return response.data.get("results", response.data)

    def result_ids(self, response):
        return [item["id"] for item in self.results(response)]

    def test_anonymous_sees_only_published_events(self):
        published = self.make_event(
            title="Published",
            status=Event.Status.PUBLISHED,
        )
        draft = self.make_event(title="Draft")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(published.id, self.result_ids(response))
        self.assertNotIn(draft.id, self.result_ids(response))

    def test_regular_user_sees_only_published_events(self):
        self.client.force_authenticate(self.regular_user)
        published = self.make_event(
            title="Published",
            status=Event.Status.PUBLISHED,
        )
        draft = self.make_event(title="Draft")

        response = self.client.get(self.list_url)

        self.assertIn(published.id, self.result_ids(response))
        self.assertNotIn(draft.id, self.result_ids(response))

    def test_organizer_sees_published_and_own_draft_events(self):
        self.client.force_authenticate(self.organizer)
        published = self.make_event(
            title="Published",
            status=Event.Status.PUBLISHED,
            organizer=self.other_organizer,
        )
        own_draft = self.make_event(title="Own Draft", organizer=self.organizer)
        other_draft = self.make_event(
            title="Other Draft",
            organizer=self.other_organizer,
        )

        response = self.client.get(self.list_url)

        ids = self.result_ids(response)
        self.assertIn(published.id, ids)
        self.assertIn(own_draft.id, ids)
        self.assertNotIn(other_draft.id, ids)

    def test_admin_sees_all_events(self):
        self.client.force_authenticate(self.admin)
        published = self.make_event(
            title="Published",
            status=Event.Status.PUBLISHED,
        )
        draft = self.make_event(title="Draft")

        response = self.client.get(self.list_url)

        ids = self.result_ids(response)
        self.assertIn(published.id, ids)
        self.assertIn(draft.id, ids)

    def test_anonymous_cannot_create_event(self):
        response = self.client.post(
            self.list_url,
            self.event_payload(),
            format="json",
        )

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_user_cannot_create_event(self):
        self.client.force_authenticate(self.regular_user)

        response = self.client.post(
            self.list_url,
            self.event_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_can_create_event(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url,
            self.event_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organizer"], self.organizer.id)
        self.assertEqual(response.data["status"], Event.Status.DRAFT)

    def test_admin_can_create_event(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.list_url,
            self.event_payload(title="Admin Event"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organizer"], self.admin.id)

    def test_organizer_field_is_current_user_not_payload(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            self.list_url,
            self.event_payload(organizer=self.other_organizer.id),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = Event.objects.get(id=response.data["id"])
        self.assertEqual(event.organizer, self.organizer)

    def test_anonymous_can_retrieve_published_event(self):
        event = self.make_event(status=Event.Status.PUBLISHED)

        response = self.client.get(self.detail_url(event))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], event.id)

    def test_anonymous_cannot_retrieve_draft_event(self):
        event = self.make_event()

        response = self.client.get(self.detail_url(event))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_retrieve_own_draft_event(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(organizer=self.organizer)

        response = self.client.get(self.detail_url(event))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_draft_event(self):
        self.client.force_authenticate(self.admin)
        event = self.make_event()

        response = self.client.get(self.detail_url(event))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_organizer_can_update_own_event(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(organizer=self.organizer)

        response = self.client.patch(
            self.detail_url(event),
            {"title": "Updated Title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.title, "Updated Title")

    def test_organizer_cannot_update_another_organizers_event(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(
            organizer=self.other_organizer,
            status=Event.Status.PUBLISHED,
        )

        response = self.client.patch(
            self.detail_url(event),
            {"title": "Blocked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_event(self):
        self.client.force_authenticate(self.admin)
        event = self.make_event(organizer=self.other_organizer)

        response = self.client.patch(
            self.detail_url(event),
            {"title": "Admin Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.title, "Admin Updated")

    def test_user_cannot_update_event(self):
        self.client.force_authenticate(self.regular_user)
        event = self.make_event(status=Event.Status.PUBLISHED)

        response = self.client.patch(
            self.detail_url(event),
            {"title": "Blocked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_cannot_change_organizer_through_payload(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(organizer=self.organizer)

        response = self.client.patch(
            self.detail_url(event),
            {"organizer": self.other_organizer.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.organizer, self.organizer)

    def test_organizer_can_delete_own_event(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(organizer=self.organizer)

        response = self.client.delete(self.detail_url(event))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(id=event.id).exists())

    def test_publish_action_sets_status_and_publication_flag(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(organizer=self.organizer)

        response = self.client.post(self.action_url(event, "publish"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Event.Status.PUBLISHED)
        self.assertTrue(response.data["is_published"])

    def test_cancel_action_sets_status_and_publication_flag(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )
        ticket_type = TicketType.objects.create(
            event=event,
            name="Standard",
            price=Decimal("10.00"),
            quantity=10,
            sold_count=1,
        )
        booking = Booking.objects.create(
            user=self.regular_user,
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
            price_at_purchase=ticket_type.price,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.action_url(event, "cancel"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Event.Status.CANCELED)
        self.assertFalse(response.data["is_published"])
        self.assertTrue(
            Notification.objects.filter(
                user=self.regular_user,
                type=Notification.Type.EVENT_CANCELED,
                entity_type="Event",
                entity_id=str(event.id),
                metadata__event_id=event.id,
            ).exists()
        )

    def test_finish_action_sets_status_and_publication_flag(self):
        self.client.force_authenticate(self.organizer)
        event = self.make_event(
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )

        response = self.client.post(self.action_url(event, "finish"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Event.Status.FINISHED)
        self.assertFalse(response.data["is_published"])

    def test_another_organizer_cannot_publish_cancel_or_finish_event(self):
        self.client.force_authenticate(self.organizer)
        draft = self.make_event(organizer=self.other_organizer)
        published_for_cancel = self.make_event(
            title="Published For Cancel",
            organizer=self.other_organizer,
            status=Event.Status.PUBLISHED,
        )
        published_for_finish = self.make_event(
            title="Published For Finish",
            organizer=self.other_organizer,
            status=Event.Status.PUBLISHED,
        )

        publish_response = self.client.post(self.action_url(draft, "publish"))
        cancel_response = self.client.post(
            self.action_url(published_for_cancel, "cancel")
        )
        finish_response = self.client.post(
            self.action_url(published_for_finish, "finish")
        )

        self.assertIn(
            publish_response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(finish_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_publish_cancel_and_finish_any_event(self):
        self.client.force_authenticate(self.admin)
        draft = self.make_event(title="Admin Publish", organizer=self.organizer)
        published_for_cancel = self.make_event(
            title="Admin Cancel",
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )
        published_for_finish = self.make_event(
            title="Admin Finish",
            organizer=self.organizer,
            status=Event.Status.PUBLISHED,
        )

        publish_response = self.client.post(self.action_url(draft, "publish"))
        cancel_response = self.client.post(
            self.action_url(published_for_cancel, "cancel")
        )
        finish_response = self.client.post(
            self.action_url(published_for_finish, "finish")
        )

        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(finish_response.status_code, status.HTTP_200_OK)
        self.assertEqual(publish_response.data["status"], Event.Status.PUBLISHED)
        self.assertEqual(cancel_response.data["status"], Event.Status.CANCELED)
        self.assertEqual(finish_response.data["status"], Event.Status.FINISHED)

    def test_filter_by_category_works(self):
        first = self.make_event(
            title="Category One",
            category=self.category,
            status=Event.Status.PUBLISHED,
        )
        second = self.make_event(
            title="Category Two",
            category=self.other_category,
            status=Event.Status.PUBLISHED,
        )

        response = self.client.get(self.list_url, {"category": self.category.id})

        ids = self.result_ids(response)
        self.assertIn(first.id, ids)
        self.assertNotIn(second.id, ids)

    def test_search_by_title_works(self):
        matching = self.make_event(
            title="Unique Chess Event",
            status=Event.Status.PUBLISHED,
        )
        non_matching = self.make_event(
            title="Basketball Event",
            status=Event.Status.PUBLISHED,
        )

        response = self.client.get(self.list_url, {"search": "Chess"})

        ids = self.result_ids(response)
        self.assertIn(matching.id, ids)
        self.assertNotIn(non_matching.id, ids)

    def test_ordering_by_start_datetime_works(self):
        later = self.make_event(
            title="Later Event",
            days=5,
            status=Event.Status.PUBLISHED,
        )
        earlier = self.make_event(
            title="Earlier Event",
            days=1,
            status=Event.Status.PUBLISHED,
        )

        response = self.client.get(self.list_url, {"ordering": "start_datetime"})

        self.assertEqual(self.result_ids(response), [earlier.id, later.id])
