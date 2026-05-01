from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import Profile

User = get_user_model()


class UserSignalsTests(TestCase):
    def test_profile_created_automatically(self):
        user = User.objects.create_user(
            email="member@example.com",
            password="test-password",
        )

        self.assertTrue(hasattr(user, "profile"))
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.user, user)
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_profile_not_duplicated_on_user_update(self):
        user = User.objects.create_user(
            email="member@example.com",
            password="test-password",
        )

        user.username = "updated"
        user.save()

        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
