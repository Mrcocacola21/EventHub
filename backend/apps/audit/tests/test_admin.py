from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.audit.admin import AuditLogAdmin
from apps.audit.models import AuditLog

User = get_user_model()


class AuditLogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email="audit-admin@example.com",
            password="StrongPass123!",
        )
        cls.log = AuditLog.objects.create(
            user=cls.admin_user,
            action=AuditLog.Action.EVENT_CREATED,
            entity_type="Event",
            entity_id="1",
            request_id="admin-request-id",
        )

    def request(self):
        request = RequestFactory().get("/")
        request.user = self.admin_user
        return request

    def test_audit_log_admin_is_registered(self):
        self.assertIsInstance(admin.site._registry[AuditLog], AuditLogAdmin)

    def test_list_display_contains_expected_fields(self):
        audit_admin = admin.site._registry[AuditLog]

        for field_name in (
            "action",
            "entity_type",
            "entity_id",
            "user",
            "request_id",
            "created_at",
        ):
            self.assertIn(field_name, audit_admin.list_display)

    def test_readonly_fields_contains_important_fields(self):
        audit_admin = admin.site._registry[AuditLog]

        for field_name in (
            "id",
            "user",
            "action",
            "entity_type",
            "entity_id",
            "ip_address",
            "user_agent",
            "request_id",
            "metadata",
            "created_at",
        ):
            self.assertIn(field_name, audit_admin.readonly_fields)

    def test_permissions_keep_audit_log_read_only(self):
        audit_admin = admin.site._registry[AuditLog]
        request = self.request()

        self.assertFalse(audit_admin.has_add_permission(request))
        self.assertFalse(audit_admin.has_change_permission(request, self.log))
        self.assertTrue(audit_admin.has_view_permission(request, self.log))
        self.assertFalse(audit_admin.has_delete_permission(request, self.log))

    def test_search_fields_include_traceability_fields(self):
        audit_admin = admin.site._registry[AuditLog]

        self.assertIn("user__email", audit_admin.search_fields)
        self.assertIn("request_id", audit_admin.search_fields)
        self.assertIn("ip_address", audit_admin.search_fields)
