from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserMeApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("users-me")

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="user1",
        )

    def test_get_me_authenticated(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["username"], "user1")
        self.assertEqual(response.data["role"], User.Roles.USER)
        self.assertIn("profile", response.data)

    def test_get_me_unauthenticated(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_me_updates_username(self):
        self.client.force_authenticate(user=self.user)
        payload = {"username": "new_name"}

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.username, "new_name")

    def test_patch_me_updates_profile(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "profile": {
                "bio": "Hello",
                "phone": "+380000000000",
            },
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()

        self.assertEqual(self.user.profile.bio, "Hello")
        self.assertEqual(self.user.profile.phone, "+380000000000")

    def test_patch_me_cannot_change_email(self):
        self.client.force_authenticate(user=self.user)
        payload = {"email": "new-email@example.com"}

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "user@example.com")

    def test_patch_me_cannot_change_role(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "role": User.Roles.ADMIN,
            "is_verified": True,
            "is_staff": True,
            "is_superuser": True,
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Roles.USER)

    def test_patch_me_cannot_change_staff_flags(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "is_verified": True,
            "is_staff": True,
            "is_superuser": True,
        }

        response = self.client.patch(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
