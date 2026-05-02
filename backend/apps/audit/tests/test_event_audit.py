from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.events.models import Event, EventCategory

User = get_user_model()


class EventAuditTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Audit Events")
        cls.organizer = User.objects.create_user(
            email="audit-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

    def window(self, days=2):
        start = timezone.now() + timedelta(days=days)
        return start, start + timedelta(hours=2)

    def event_payload(self, **overrides):
        start, end = self.window()
        data = {
            "title": "Audited Event",
            "description": "Audit event",
            "category": self.category.id,
            "location": "Kyiv",
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "max_participants": 50,
        }
        data.update(overrides)
        return data

    def make_event(self, **overrides):
        start, end = self.window()
        data = {
            "title": "Audited Event",
            "description": "Audit event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": end,
            "organizer": self.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def assert_event_log(self, *, action, event, request_id):
        log = AuditLog.objects.get(action=action)

        self.assertEqual(log.user, self.organizer)
        self.assertEqual(log.entity_type, "Event")
        self.assertEqual(log.entity_id, str(event.id))
        self.assertEqual(log.request_id, request_id)
        self.assertEqual(log.metadata["title"], event.title)
        self.assertEqual(log.metadata["status"], event.status)
        self.assertEqual(log.metadata["organizer_id"], self.organizer.id)

    def test_create_event_writes_audit_log(self):
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("event-list"),
            self.event_payload(),
            format="json",
            HTTP_X_REQUEST_ID="event-created-request",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = Event.objects.get(id=response.data["id"])
        self.assert_event_log(
            action=AuditLog.Action.EVENT_CREATED,
            event=event,
            request_id="event-created-request",
        )

    def test_patch_event_writes_audit_log(self):
        event = self.make_event()
        self.client.force_authenticate(self.organizer)

        response = self.client.patch(
            reverse("event-detail", args=[event.id]),
            {"title": "Audited Event Updated"},
            format="json",
            HTTP_X_REQUEST_ID="event-updated-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assert_event_log(
            action=AuditLog.Action.EVENT_UPDATED,
            event=event,
            request_id="event-updated-request",
        )

    def test_publish_event_writes_audit_log(self):
        event = self.make_event()
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("event-publish", args=[event.id]),
            HTTP_X_REQUEST_ID="event-published-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assert_event_log(
            action=AuditLog.Action.EVENT_PUBLISHED,
            event=event,
            request_id="event-published-request",
        )

    def test_cancel_event_writes_audit_log(self):
        event = self.make_event(status=Event.Status.PUBLISHED)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("event-cancel", args=[event.id]),
            HTTP_X_REQUEST_ID="event-canceled-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assert_event_log(
            action=AuditLog.Action.EVENT_CANCELED,
            event=event,
            request_id="event-canceled-request",
        )

    def test_finish_event_writes_audit_log(self):
        event = self.make_event(status=Event.Status.PUBLISHED)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("event-finish", args=[event.id]),
            HTTP_X_REQUEST_ID="event-finished-request",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assert_event_log(
            action=AuditLog.Action.EVENT_FINISHED,
            event=event,
            request_id="event-finished-request",
        )
