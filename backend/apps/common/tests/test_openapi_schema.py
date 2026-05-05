from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class OpenApiSchemaTests(APITestCase):
    def get_schema(self):
        response = self.client.get(
            reverse("schema"),
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()

    def test_schema_docs_and_redoc_are_available(self):
        schema = self.client.get(reverse("schema"), HTTP_ACCEPT="application/json")
        docs = self.client.get(reverse("swagger-ui"))
        redoc = self.client.get(reverse("redoc"))

        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
        self.assertEqual(redoc.status_code, status.HTTP_200_OK)

    def test_schema_contains_core_paths(self):
        schema = self.get_schema()
        paths = schema["paths"]

        for path in (
            "/api/health/",
            "/api/auth/register/",
            "/api/auth/login/",
            "/api/events/",
            "/api/bookings/",
            "/api/tournaments/",
            "/api/notifications/",
        ):
            self.assertIn(path, paths)

    def test_schema_contains_custom_actions(self):
        schema = self.get_schema()
        paths = schema["paths"]

        for path in (
            "/api/events/{id}/publish/",
            "/api/bookings/{id}/use/",
            "/api/bookings/{id}/download-pdf/",
            "/api/tournaments/{id}/start/",
            "/api/matches/{id}/result/",
            "/api/notifications/read-all/",
        ):
            self.assertIn(path, paths)

    def test_schema_includes_jwt_bearer_security_scheme(self):
        schema = self.get_schema()
        security_schemes = schema["components"]["securitySchemes"]

        self.assertTrue(
            any(
                scheme.get("type") == "http"
                and scheme.get("scheme") == "bearer"
                for scheme in security_schemes.values()
            )
        )
