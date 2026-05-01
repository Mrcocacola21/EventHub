from django.contrib import admin
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
        "email",
        "username",
        "role",
        "is_verified",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_verified", "is_staff", "is_active")
    search_fields = ("email", "username")
    ordering = ("email",)
    readonly_fields = ("date_joined", "created_at", "updated_at", "last_login")
    inlines = (ProfileInline,)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Role", {"fields": ("role", "is_verified")}),
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
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
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
                    "is_verified",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "created_at")
    search_fields = ("user__email", "phone")
    readonly_fields = ("created_at", "updated_at")

