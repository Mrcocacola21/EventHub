from django.contrib import admin
from django.utils import timezone

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "type",
        "title",
        "is_read",
        "entity_type",
        "entity_id",
        "created_at",
    )
    list_filter = ("type", "is_read", "created_at")
    search_fields = ("user__email", "title", "message", "entity_type", "entity_id")
    readonly_fields = (
        "id",
        "user",
        "type",
        "title",
        "message",
        "entity_type",
        "entity_id",
        "metadata",
        "created_at",
        "updated_at",
        "read_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("user",)
    actions = ("mark_as_read", "mark_as_unread")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        read_at = timezone.now()
        return queryset.filter(is_read=False).update(
            is_read=True,
            read_at=read_at,
            updated_at=read_at,
        )

    @admin.action(description="Mark selected notifications as unread")
    def mark_as_unread(self, request, queryset):
        return queryset.update(is_read=False, read_at=None, updated_at=timezone.now())
