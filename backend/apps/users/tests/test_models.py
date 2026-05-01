from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import Profile

User = get_user_model()


class UserModelTests(TestCase):
    def test_user_role_properties(self):
        user = User(role=User.Roles.USER)
        organizer = User(role=User.Roles.ORGANIZER)
        admin = User(role=User.Roles.ADMIN)

        self.assertTrue(user.is_user)
        self.assertFalse(user.is_organizer)
        self.assertFalse(user.is_admin_role)

        self.assertTrue(organizer.is_organizer)
        self.assertFalse(organizer.is_user)
        self.assertFalse(organizer.is_admin_role)

        self.assertTrue(admin.is_admin_role)
        self.assertFalse(admin.is_user)
        self.assertFalse(admin.is_organizer)

    def test_user_string_representation(self):
        user = User(email="member@example.com")

        self.assertEqual(str(user), "member@example.com")

    def test_create_user_defaults(self):
        user = User.objects.create_user(
            email="defaults@example.com",
            password="test-password",
        )

        self.assertEqual(user.role, User.Roles.USER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_profile_string_representation(self):
        user = User.objects.create_user(
            email="profile@example.com",
            password="test-password",
        )
        profile = Profile.objects.get(user=user)

        self.assertEqual(str(profile), "Profile for profile@example.com")
