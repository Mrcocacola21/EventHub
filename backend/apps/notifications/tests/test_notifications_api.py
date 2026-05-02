from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification

User = get_user_model()


class NotificationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="api-user@example.com",
            password="StrongPass123!",
        )
        cls.other_user = User.objects.create_user(
            email="api-other@example.com",
            password="StrongPass123!",
        )

    def make_notification(self, **overrides):
        data = {
            "user": self.user,
            "type": Notification.Type.SYSTEM,
            "title": "Notice",
            "message": "Message",
        }
        data.update(overrides)
        return Notification.objects.create(**data)

    def results(self, response):
        return response.data.get("results", response.data)

    def test_list_requires_authentication(self):
        response = self.client.get(reverse("notification-list"))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_authenticated_user_sees_own_notifications_only(self):
        own = self.make_notification(title="Own")
        other = self.make_notification(
            user=self.other_user,
            title="Other",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("notification-list"))

        ids = [item["id"] for item in self.results(response)]
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)

    def test_list_is_ordered_by_newest_first(self):
        older = self.make_notification(title="Older")
        newer = self.make_notification(title="Newer")
        Notification.objects.filter(id=older.id).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )
        older.refresh_from_db()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("notification-list"))

        ids = [item["id"] for item in self.results(response)]
        self.assertLess(ids.index(newer.id), ids.index(older.id))

    def test_filter_by_is_read(self):
        unread = self.make_notification(title="Unread", is_read=False)
        read = self.make_notification(
            title="Read",
            is_read=True,
            read_at=timezone.now(),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("notification-list"), {"is_read": "false"})

        ids = [item["id"] for item in self.results(response)]
        self.assertIn(unread.id, ids)
        self.assertNotIn(read.id, ids)

    def test_filter_by_type(self):
        booking = self.make_notification(type=Notification.Type.BOOKING_CREATED)
        system = self.make_notification(type=Notification.Type.SYSTEM)
        self.client.force_authenticate(self.user)

        response = self.client.get(
            reverse("notification-list"),
            {"type": Notification.Type.BOOKING_CREATED},
        )

        ids = [item["id"] for item in self.results(response)]
        self.assertIn(booking.id, ids)
        self.assertNotIn(system.id, ids)

    def test_owner_can_mark_notification_as_read(self):
        notification = self.make_notification()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("notification-read", args=[notification.id]))

        notification.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_repeated_read_does_not_overwrite_read_at(self):
        notification = self.make_notification()
        notification.mark_as_read()
        first_read_at = notification.read_at
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("notification-read", args=[notification.id]))

        notification.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(notification.read_at, first_read_at)

    def test_another_user_cannot_mark_notification_read(self):
        notification = self.make_notification()
        self.client.force_authenticate(self.other_user)

        response = self.client.post(reverse("notification-read", args=[notification.id]))

        notification.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(notification.is_read)

    def test_read_requires_authentication(self):
        notification = self.make_notification()

        response = self.client.post(reverse("notification-read", args=[notification.id]))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_read_all_marks_current_users_unread_notifications(self):
        first = self.make_notification(title="First")
        second = self.make_notification(title="Second")
        other = self.make_notification(user=self.other_user, title="Other")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("notification-read-all"))

        first.refresh_from_db()
        second.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertTrue(first.is_read)
        self.assertTrue(second.is_read)
        self.assertIsNotNone(first.read_at)
        self.assertFalse(other.is_read)
