from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from apps.audit.models import AuditLog
from apps.audit.services import AuditService

User = get_user_model()


class AuditServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="audit-service@example.com",
            password="StrongPass123!",
        )

    def request(self, user=None):
        request = RequestFactory().post(
            "/",
            HTTP_X_FORWARDED_FOR="198.51.100.9, 203.0.113.4",
            HTTP_USER_AGENT="AuditServiceTest/1.0",
        )
        request.user = user or self.user
        request.request_id = "service-request-id"
        request.audit_ip_address = "198.51.100.9"
        request.audit_user_agent = "AuditServiceTest/1.0"
        return request

    def test_log_action_creates_audit_log(self):
        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
        )

        self.assertIsNotNone(log)
        self.assertTrue(AuditLog.objects.filter(id=log.id).exists())

    def test_log_action_saves_user(self):
        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
            user=self.user,
        )

        self.assertEqual(log.user, self.user)

    def test_log_action_saves_request_context(self):
        request = self.request()

        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
            request=request,
        )

        self.assertEqual(log.user, self.user)
        self.assertEqual(log.request_id, "service-request-id")
        self.assertEqual(log.ip_address, "198.51.100.9")
        self.assertEqual(log.user_agent, "AuditServiceTest/1.0")

    def test_log_action_uses_request_meta_fallbacks(self):
        request = RequestFactory().post(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.30, 203.0.113.31",
            HTTP_USER_AGENT="FallbackAgent/1.0",
        )
        request.user = self.user

        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
            request=request,
        )

        self.assertEqual(log.ip_address, "203.0.113.30")
        self.assertEqual(log.user_agent, "FallbackAgent/1.0")

    def test_log_action_converts_entity_id_to_string(self):
        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=123,
        )

        self.assertEqual(log.entity_id, "123")

    def test_log_action_saves_metadata(self):
        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
            metadata={"title": "Audit"},
        )

        self.assertEqual(log.metadata, {"title": "Audit"})

    def test_anonymous_request_saves_user_as_none(self):
        request = self.request(user=AnonymousUser())

        log = AuditService.log_action(
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id=1,
            request=request,
        )

        self.assertIsNone(log.user)

    def test_log_action_returns_none_when_create_fails(self):
        with (
            patch(
                "apps.audit.services.AuditLog.objects.create",
                side_effect=RuntimeError("audit failure"),
            ),
            patch("apps.audit.services.logger.exception"),
        ):
            log = AuditService.log_action(
                action=AuditLog.Action.EVENT_CREATED,
                entity_type="Event",
                entity_id=1,
            )

        self.assertIsNone(log)
