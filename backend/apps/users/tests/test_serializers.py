from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import Profile
from apps.users.serializers import (
    ProfileSerializer,
    RegisterSerializer,
    UserMeSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterSerializerTests(TestCase):
    def test_valid_data_passes_validation(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "username": "user1",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_password_confirmation_must_match(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "username": "user1",
                "password": "StrongPass123!",
                "password_confirm": "OtherStrongPass123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("password_confirm", serializer.errors)

    def test_duplicate_email_is_invalid(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "username": "user2",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_invalid_password_is_rejected(self):
        serializer = RegisterSerializer(
            data={
                "email": "user@example.com",
                "username": "user1",
                "password": "123",
                "password_confirm": "123",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_role_payload_is_ignored_on_create(self):
        serializer = RegisterSerializer(
            data={
                "email": "admin@example.com",
                "username": "adminish",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "role": User.Roles.ADMIN,
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.role, User.Roles.USER)


class UserSerializerTests(TestCase):
    def test_user_serializer_returns_expected_fields(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="user1",
        )

        data = UserSerializer(user).data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "email",
                "username",
                "role",
                "is_verified",
                "date_joined",
                "created_at",
                "updated_at",
            },
        )
        self.assertNotIn("password", data)


class UserMeSerializerTests(TestCase):
    def test_user_me_serializer_returns_profile(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="user1",
        )

        data = UserMeSerializer(user).data

        self.assertEqual(data["email"], "user@example.com")
        self.assertEqual(data["role"], User.Roles.USER)
        self.assertIn("profile", data)
        self.assertNotIn("password", data)

    def test_user_me_serializer_ignores_protected_fields(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
            username="user1",
        )
        serializer = UserMeSerializer(
            user,
            data={
                "email": "changed@example.com",
                "role": User.Roles.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_verified": True,
                "username": "updated",
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user.refresh_from_db()
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(user.role, User.Roles.USER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_verified)
        self.assertEqual(user.username, "updated")


class ProfileSerializerTests(TestCase):
    def test_profile_serializer_returns_profile_fields(self):
        user = User.objects.create_user(
            email="profile@example.com",
            password="StrongPass123!",
        )
        profile = user.profile
        profile.bio = "Hello"
        profile.phone = "+380000000000"
        profile.save()

        data = ProfileSerializer(profile).data

        self.assertIn("avatar", data)
        self.assertEqual(data["bio"], "Hello")
        self.assertEqual(data["phone"], "+380000000000")

    def test_profile_serializer_updates_allowed_fields(self):
        user = User.objects.create_user(
            email="profile@example.com",
            password="StrongPass123!",
        )
        profile = Profile.objects.get(user=user)
        serializer = ProfileSerializer(
            profile,
            data={"bio": "Updated", "phone": "+380111111111"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        profile.refresh_from_db()
        self.assertEqual(profile.bio, "Updated")
        self.assertEqual(profile.phone, "+380111111111")

