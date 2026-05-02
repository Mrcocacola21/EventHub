from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.audit.models import AuditLog

User = get_user_model()


class AuditLogModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="audit-user@example.com",
            password="StrongPass123!",
        )

    def test_audit_log_can_be_created(self):
        log = AuditLog.objects.create(
            user=self.user,
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id="1",
            metadata={"title": "Audit Event"},
        )

        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, AuditLog.Action.EVENT_CREATED)
        self.assertEqual(log.entity_type, "Event")
        self.assertEqual(log.entity_id, "1")
        self.assertEqual(log.metadata["title"], "Audit Event")

    def test_str_returns_action_entity_type_and_entity_id(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.BOOKING_CREATED,
            entity_type="Booking",
            entity_id="42",
        )

        self.assertEqual(str(log), "BOOKING_CREATED Booking:42")

    def test_metadata_defaults_to_dict(self):
        log = AuditLog.objects.create(
            action=AuditLog.Action.EVENT_UPDATED,
            entity_type="Event",
            entity_id="7",
        )

        self.assertEqual(log.metadata, {})

    def test_ordering_is_newest_first(self):
        older = AuditLog.objects.create(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id="1",
        )
        newer = AuditLog.objects.create(
            action=AuditLog.Action.EVENT_UPDATED,
            entity_type="Event",
            entity_id="1",
        )
        AuditLog.objects.filter(id=older.id).update(
            created_at=timezone.now() - timedelta(days=1),
        )
        AuditLog.objects.filter(id=newer.id).update(created_at=timezone.now())

        self.assertEqual(list(AuditLog.objects.values_list("id", flat=True)), [
            newer.id,
            older.id,
        ])
