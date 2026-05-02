from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.tasks import cleanup_old_notifications

User = get_user_model()


class CleanupOldNotificationsTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="cleanup-user@example.com",
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
        notification = Notification.objects.create(**data)
        if "created_at" in overrides:
            Notification.objects.filter(id=notification.id).update(
                created_at=overrides["created_at"]
            )
            notification.refresh_from_db()
        return notification

    def test_cleanup_old_notifications_deletes_only_old_read_notifications(self):
        old = timezone.now() - timedelta(days=31)
        recent = timezone.now() - timedelta(days=2)
        old_read = self.make_notification(
            title="Old read",
            is_read=True,
            read_at=old,
            created_at=old,
        )
        old_unread = self.make_notification(title="Old unread", created_at=old)
        recent_read = self.make_notification(
            title="Recent read",
            is_read=True,
            read_at=recent,
            created_at=recent,
        )

        deleted_count = cleanup_old_notifications(days=30)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(Notification.objects.filter(id=old_read.id).exists())
        self.assertTrue(Notification.objects.filter(id=old_unread.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent_read.id).exists())
