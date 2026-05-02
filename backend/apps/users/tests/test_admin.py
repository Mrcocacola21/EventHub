from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.users.admin import ProfileAdmin, ProfileInline, UserAdmin
from apps.users.models import Profile

User = get_user_model()


class UserAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email="superuser@example.com",
            password="StrongPass123!",
        )

    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def make_user(self, **overrides):
        data = {
            "email": "user@example.com",
            "password": "StrongPass123!",
        }
        data.update(overrides)
        password = data.pop("password")
        return User.objects.create_user(password=password, **data)

    def test_user_model_is_registered(self):
        self.assertIsInstance(admin.site._registry[User], UserAdmin)

    def test_profile_model_is_registered(self):
        self.assertIsInstance(admin.site._registry[Profile], ProfileAdmin)

    def test_user_admin_configuration_exposes_expected_controls(self):
        user_admin = admin.site._registry[User]

        for field_name in (
            "id",
            "email",
            "username",
            "role",
            "is_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
        ):
            self.assertIn(field_name, user_admin.list_display)

        for field_name in ("role", "is_verified", "is_staff", "is_active"):
            self.assertIn(field_name, user_admin.list_filter)

        for field_name in ("email", "username", "profile__phone"):
            self.assertIn(field_name, user_admin.search_fields)

        for field_name in ("id", "created_at", "updated_at", "date_joined"):
            self.assertIn(field_name, user_admin.readonly_fields)

        self.assertEqual(user_admin.ordering, ("email",))

    def test_user_admin_fieldsets_are_production_ready(self):
        user_admin = admin.site._registry[User]
        fieldsets = {title: options["fields"] for title, options in user_admin.fieldsets}
        add_fields = user_admin.add_fieldsets[0][1]["fields"]

        self.assertIn("Account", fieldsets)
        self.assertEqual(fieldsets["Account"], ("email", "password"))
        self.assertEqual(fieldsets["Personal info"], ("username",))
        self.assertEqual(fieldsets["Role and verification"], ("role", "is_verified"))
        self.assertIn("groups", fieldsets["Permissions"])
        self.assertIn("user_permissions", fieldsets["Permissions"])
        self.assertIn("last_login", fieldsets["Important dates"])

        for field_name in (
            "email",
            "username",
            "role",
            "password1",
            "password2",
            "is_staff",
            "is_superuser",
            "is_active",
            "is_verified",
        ):
            self.assertIn(field_name, add_fields)

    def test_profile_inline_exists_in_user_admin(self):
        user_admin = admin.site._registry[User]

        self.assertIn(ProfileInline, user_admin.inlines)

        self.assertEqual(ProfileInline.extra, 0)
        self.assertFalse(ProfileInline.can_delete)
        self.assertIn("created_at", ProfileInline.readonly_fields)
        self.assertIn("updated_at", ProfileInline.readonly_fields)

    def test_expected_actions_exist(self):
        user_admin = admin.site._registry[User]

        self.assertIn("mark_verified", user_admin.actions)
        self.assertIn("mark_unverified", user_admin.actions)
        self.assertIn("promote_to_organizer", user_admin.actions)
        self.assertIn("demote_to_user", user_admin.actions)

    def test_verify_actions_toggle_is_verified(self):
        user_admin = admin.site._registry[User]
        user = self.make_user(email="verify@example.com", is_verified=False)

        user_admin.mark_verified(self.request(), User.objects.filter(id=user.id))
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

        user_admin.mark_unverified(self.request(), User.objects.filter(id=user.id))
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_promote_to_organizer_changes_role(self):
        user_admin = admin.site._registry[User]
        user = self.make_user(email="promote@example.com")

        user_admin.promote_to_organizer(
            self.request(),
            User.objects.filter(id=user.id),
        )

        user.refresh_from_db()
        self.assertEqual(user.role, User.Roles.ORGANIZER)

    def test_demote_to_user_changes_role(self):
        user_admin = admin.site._registry[User]
        user = self.make_user(
            email="demote@example.com",
            role=User.Roles.ORGANIZER,
        )

        user_admin.demote_to_user(self.request(), User.objects.filter(id=user.id))

        user.refresh_from_db()
        self.assertEqual(user.role, User.Roles.USER)

    def test_demote_to_user_does_not_demote_superuser(self):
        user_admin = admin.site._registry[User]

        user_admin.demote_to_user(
            self.request(),
            User.objects.filter(id=self.admin_user.id),
        )

        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.role, User.Roles.ADMIN)
