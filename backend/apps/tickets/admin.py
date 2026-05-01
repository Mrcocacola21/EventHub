from django.contrib import admin

from apps.events.models import Event

from .models import TicketType


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "name",
        "price",
        "quantity",
        "sold_count",
        "available_quantity",
        "is_active",
        "sales_start",
        "sales_end",
    )
    list_filter = ("is_active", "event__status", "sales_start", "sales_end")
    search_fields = ("name", "event__title", "event__organizer__email")
    readonly_fields = ("sold_count", "created_at", "updated_at")
    list_select_related = ("event", "event__organizer")
    actions = ("deactivate_ticket_types", "activate_ticket_types")

    @admin.action(description="Deactivate selected ticket types")
    def deactivate_ticket_types(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Activate selected ticket types")
    def activate_ticket_types(self, request, queryset):
        queryset.exclude(
            event__status__in=(Event.Status.CANCELED, Event.Status.FINISHED)
        ).update(is_active=True)
