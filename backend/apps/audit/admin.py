from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action",
        "entity_type",
        "entity_id",
        "user",
        "ip_address",
        "request_id",
        "created_at",
    )
    list_filter = ("action", "entity_type", "created_at")
    search_fields = (
        "action",
        "entity_type",
        "entity_id",
        "user__email",
        "request_id",
        "ip_address",
    )
    readonly_fields = (
        "id",
        "user",
        "action",
        "entity_type",
        "entity_id",
        "ip_address",
        "user_agent",
        "request_id",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) or super().has_change_permission(
            request,
            obj,
        )

    def has_delete_permission(self, request, obj=None):
        return False
