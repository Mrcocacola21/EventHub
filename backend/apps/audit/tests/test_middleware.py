from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.middleware import RequestIDMiddleware

User = get_user_model()


class RequestIDMiddlewareTests(TestCase):
    def get_response(self, request):
        self.request = request
        return HttpResponse("ok")

    def build_response(self, request):
        middleware = RequestIDMiddleware(self.get_response)
        return middleware(request)

    def test_response_contains_generated_request_id(self):
        request = RequestFactory().get("/")

        response = self.build_response(request)

        self.assertTrue(self.request.request_id)
        self.assertEqual(response["X-Request-ID"], self.request.request_id)

    def test_client_request_id_is_used_and_truncated(self):
        request_id = "x" * 80
        request = RequestFactory().get("/", HTTP_X_REQUEST_ID=request_id)

        response = self.build_response(request)

        self.assertEqual(self.request.request_id, "x" * 64)
        self.assertEqual(response["X-Request-ID"], "x" * 64)

    def test_request_audit_ip_address_uses_remote_addr(self):
        request = RequestFactory().get("/", REMOTE_ADDR="203.0.113.10")

        self.build_response(request)

        self.assertEqual(self.request.audit_ip_address, "203.0.113.10")

    def test_request_audit_user_agent_is_set(self):
        request = RequestFactory().get("/", HTTP_USER_AGENT="AuditTest/1.0")

        self.build_response(request)

        self.assertEqual(self.request.audit_user_agent, "AuditTest/1.0")

    def test_x_forwarded_for_uses_first_ip(self):
        request = RequestFactory().get(
            "/",
            HTTP_X_FORWARDED_FOR="198.51.100.7, 203.0.113.20",
        )

        self.build_response(request)

        self.assertEqual(self.request.audit_ip_address, "198.51.100.7")


class RequestIDResponseHeaderTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="request-id@example.com",
            password="StrongPass123!",
        )

    def test_health_response_contains_request_id_header(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("X-Request-ID", response)

    def test_events_response_contains_request_id_header(self):
        response = self.client.get(reverse("event-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("X-Request-ID", response)

    def test_my_bookings_response_contains_request_id_header(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("booking-my"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("X-Request-ID", response)
