from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.notifications.admin import NotificationAdmin
from apps.notifications.models import Notification

User = get_user_model()


class NotificationAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email="notification-admin@example.com",
            password="StrongPass123!",
        )
        cls.user = User.objects.create_user(
            email="notification-user@example.com",
            password="StrongPass123!",
        )

    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def make_notification(self, **overrides):
        data = {
            "user": self.user,
            "type": Notification.Type.SYSTEM,
            "title": "Notice",
            "message": "Message",
        }
        data.update(overrides)
        return Notification.objects.create(**data)

    def test_notification_admin_registered(self):
        self.assertIsInstance(admin.site._registry[Notification], NotificationAdmin)

    def test_admin_configuration(self):
        notification_admin = admin.site._registry[Notification]

        for field_name in ("user", "type", "title", "is_read"):
            self.assertIn(field_name, notification_admin.list_display)

        self.assertIn("type", notification_admin.list_filter)
        self.assertIn("is_read", notification_admin.list_filter)
        self.assertIn("user__email", notification_admin.search_fields)
        self.assertIn("title", notification_admin.search_fields)
        self.assertIn("entity_id", notification_admin.search_fields)

        for field_name in (
            "id",
            "user",
            "type",
            "title",
            "message",
            "metadata",
            "created_at",
            "updated_at",
        ):
            self.assertIn(field_name, notification_admin.readonly_fields)

        self.assertIn("mark_as_read", notification_admin.actions)
        self.assertIn("mark_as_unread", notification_admin.actions)

    def test_has_add_permission_is_false(self):
        notification_admin = admin.site._registry[Notification]

        self.assertFalse(notification_admin.has_add_permission(self.request()))

    def test_mark_as_read_and_unread_actions(self):
        notification_admin = admin.site._registry[Notification]
        notification = self.make_notification()

        notification_admin.mark_as_read(
            self.request(),
            Notification.objects.filter(id=notification.id),
        )
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

        notification_admin.mark_as_unread(
            self.request(),
            Notification.objects.filter(id=notification.id),
        )
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
