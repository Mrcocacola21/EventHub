from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ("avatar", "bio", "phone", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = User

    list_display = (
        "id",
        "email",
        "username",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    list_filter = (
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    )
    search_fields = ("email", "username", "profile__phone")
    ordering = ("email",)
    readonly_fields = (
        "id",
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
    )
    inlines = (ProfileInline,)
    actions = (
        "mark_verified",
        "mark_unverified",
        "promote_to_organizer",
        "demote_to_user",
    )

    fieldsets = (
        ("Account", {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username",)}),
        ("Role and verification", {"fields": ("role", "is_verified")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "role",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "is_verified",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    def _update_non_superusers(self, request, queryset, **updates):
        superusers_count = queryset.filter(is_superuser=True).count()
        updated_count = queryset.exclude(is_superuser=True).update(**updates)
        self.message_user(
            request,
            (
                f"{updated_count} user(s) updated. "
                f"{superusers_count} superuser(s) skipped."
            ),
            messages.SUCCESS,
            fail_silently=True,
        )
        return updated_count

    @admin.action(description="Mark selected users as verified")
    def mark_verified(self, request, queryset):
        return self._update_non_superusers(
            request,
            queryset,
            is_verified=True,
        )

    @admin.action(description="Mark selected users as unverified")
    def mark_unverified(self, request, queryset):
        return self._update_non_superusers(
            request,
            queryset,
            is_verified=False,
        )

    @admin.action(description="Promote selected users to organizer")
    def promote_to_organizer(self, request, queryset):
        return self._update_non_superusers(
            request,
            queryset,
            role=User.Roles.ORGANIZER,
        )

    @admin.action(description="Demote selected users to regular user")
    def demote_to_user(self, request, queryset):
        return self._update_non_superusers(
            request,
            queryset,
            role=User.Roles.USER,
        )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "created_at")
    search_fields = ("user__email", "user__username", "phone")
    readonly_fields = ("created_at", "updated_at")
