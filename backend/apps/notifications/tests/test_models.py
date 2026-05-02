from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="notification-user@example.com",
            password="StrongPass123!",
        )

    def make_notification(self, **overrides):
        data = {
            "user": self.user,
            "type": Notification.Type.SYSTEM,
            "title": "System notice",
            "message": "System message",
        }
        data.update(overrides)
        return Notification.objects.create(**data)

    def test_notification_can_be_created(self):
        notification = self.make_notification(entity_type="System", entity_id="1")

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.type, Notification.Type.SYSTEM)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.entity_id, "1")

    def test_str_is_human_readable(self):
        notification = self.make_notification(title="Readable")

        self.assertEqual(
            str(notification),
            f"{self.user.email} - {Notification.Type.SYSTEM} - Readable",
        )

    def test_metadata_default_is_independent_dict(self):
        first = self.make_notification(title="First")
        second = self.make_notification(title="Second")

        first.metadata["key"] = "value"
        first.save(update_fields=["metadata", "updated_at"])
        second.refresh_from_db()

        self.assertEqual(second.metadata, {})

    def test_ordering_is_newest_first(self):
        older = self.make_notification(title="Older")
        newer = self.make_notification(title="Newer")
        Notification.objects.filter(id=older.id).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )
        older.refresh_from_db()

        notifications = list(Notification.objects.all())

        self.assertEqual(notifications[0], newer)
        self.assertEqual(notifications[1], older)

    def test_mark_as_read_sets_read_fields(self):
        notification = self.make_notification()

        notification.mark_as_read()
        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_as_read_does_not_overwrite_existing_read_at(self):
        notification = self.make_notification()
        notification.mark_as_read()
        first_read_at = notification.read_at

        notification.mark_as_read()
        notification.refresh_from_db()

        self.assertEqual(notification.read_at, first_read_at)
