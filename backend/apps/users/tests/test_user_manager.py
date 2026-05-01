from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email="member@EXAMPLE.COM",
            password="test-password",
        )

        self.assertEqual(user.email, "member@example.com")
        self.assertNotEqual(user.password, "test-password")
        self.assertTrue(user.check_password("test-password"))
        self.assertEqual(user.role, User.Roles.USER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="test-password")

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="test-password",
            role=User.Roles.USER,
            is_verified=False,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, User.Roles.ADMIN)
        self.assertTrue(user.is_verified)

    def test_create_superuser_requires_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                password="test-password",
                is_staff=False,
            )

    def test_create_superuser_requires_superuser(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                password="test-password",
                is_superuser=False,
            )
