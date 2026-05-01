from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Profile

User = get_user_model()


class AuthApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.register_url = reverse("auth-register")
        cls.login_url = reverse("auth-login")
        cls.refresh_url = reverse("auth-refresh")

    def test_register_success(self):
        payload = {
            "email": "user@example.com",
            "username": "user1",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], User.Roles.USER)

        user = User.objects.get(email="user@example.com")
        self.assertEqual(user.role, User.Roles.USER)
        self.assertNotEqual(user.password, payload["password"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_register_password_mismatch(self):
        payload = {
            "email": "user@example.com",
            "username": "user1",
            "password": "StrongPass123!",
            "password_confirm": "OtherStrongPass123!",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        payload = {
            "email": "user@example.com",
            "username": "user2",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_cannot_set_role(self):
        payload = {
            "email": "organizer@example.com",
            "username": "organizer1",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "role": User.Roles.ADMIN,
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="organizer@example.com")
        self.assertEqual(user.role, User.Roles.USER)

    def test_register_invalid_password(self):
        payload = {
            "email": "weak@example.com",
            "username": "weak_user",
            "password": "123",
            "password_confirm": "123",
        }

        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="user1",
        )
        payload = {
            "email": "user@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "user@example.com")
        self.assertEqual(response.data["user"]["role"], User.Roles.USER)

    def test_login_invalid_credentials(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        payload = {
            "email": "user@example.com",
            "password": "WrongPass123!",
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED),
        )

    def test_login_unknown_email(self):
        payload = {
            "email": "missing@example.com",
            "password": "StrongPass123!",
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED),
        )

    def test_login_uses_email_not_username(self):
        User.objects.create_user(
            email="email-login@example.com",
            password="StrongPass123!",
            username="login_name",
        )

        response = self.client.post(
            self.login_url,
            {
                "email": "email-login@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "email-login@example.com")

    def test_refresh_success(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        login_response = self.client.post(
            self.login_url,
            {
                "email": "user@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        response = self.client.post(
            self.refresh_url,
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_invalid_token(self):
        response = self.client.post(
            self.refresh_url,
            {"refresh": "invalid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
