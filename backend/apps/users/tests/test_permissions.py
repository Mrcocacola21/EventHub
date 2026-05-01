from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.permissions import IsAdminRole, IsOrganizerRole, IsOwnerOrAdmin

User = get_user_model()


class PermissionTests(TestCase):
    def _request_for(self, user):
        return SimpleNamespace(user=user)

    def test_is_admin_role_allows_admin_role(self):
        user = User.objects.create_user(
            email="admin-role@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )

        self.assertTrue(IsAdminRole().has_permission(self._request_for(user), None))

    def test_is_admin_role_allows_superuser(self):
        user = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )

        self.assertTrue(IsAdminRole().has_permission(self._request_for(user), None))

    def test_is_admin_role_denies_regular_user(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )

        self.assertFalse(IsAdminRole().has_permission(self._request_for(user), None))

    def test_is_organizer_role_allows_organizer(self):
        user = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )

        self.assertTrue(
            IsOrganizerRole().has_permission(self._request_for(user), None)
        )

    def test_is_organizer_role_allows_admin(self):
        user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )

        self.assertTrue(
            IsOrganizerRole().has_permission(self._request_for(user), None)
        )

    def test_is_organizer_role_denies_regular_user(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )

        self.assertFalse(
            IsOrganizerRole().has_permission(self._request_for(user), None)
        )

    def test_is_owner_or_admin_allows_owner(self):
        user = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
        )
        obj = SimpleNamespace(user=user)

        self.assertTrue(
            IsOwnerOrAdmin().has_object_permission(self._request_for(user), None, obj)
        )

    def test_is_owner_or_admin_allows_admin(self):
        admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )
        owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
        )
        obj = SimpleNamespace(user=owner)

        self.assertTrue(
            IsOwnerOrAdmin().has_object_permission(self._request_for(admin), None, obj)
        )

    def test_is_owner_or_admin_denies_other_user(self):
        owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
        )
        other = User.objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
        )
        obj = SimpleNamespace(user=owner)

        self.assertFalse(
            IsOwnerOrAdmin().has_object_permission(self._request_for(other), None, obj)
        )

