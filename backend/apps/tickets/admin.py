from django.contrib import admin, messages
from django.db import transaction

from apps.events.cache import EventCacheService
from apps.events.models import Event

from .models import TicketType


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event",
        "name",
        "price",
        "quantity",
        "sold_count",
        "available_quantity_display",
        "is_sold_out_display",
        "is_active",
        "sales_start",
        "sales_end",
        "created_at",
    )
    list_filter = (
        "is_active",
        "event__status",
        "sales_start",
        "sales_end",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "event__title",
        "event__organizer__email",
    )
    readonly_fields = (
        "id",
        "sold_count",
        "available_quantity_display",
        "is_sold_out_display",
        "is_available_for_purchase_display",
        "created_at",
        "updated_at",
    )
    list_select_related = ("event", "event__organizer", "event__category")
    date_hierarchy = "created_at"
    ordering = ("event__start_datetime", "price", "name")
    actions = ("deactivate_ticket_types", "activate_ticket_types")

    @admin.display(description="Available")
    def available_quantity_display(self, obj):
        return obj.available_quantity

    @admin.display(boolean=True, description="Sold out")
    def is_sold_out_display(self, obj):
        return obj.is_sold_out

    @admin.display(boolean=True, description="Available for purchase")
    def is_available_for_purchase_display(self, obj):
        return obj.is_available_for_purchase

    def _message_action_result(self, request, updated_count, skipped_count=0):
        self.message_user(
            request,
            (
                f"{updated_count} ticket type(s) updated. "
                f"{skipped_count} ticket type(s) skipped."
            ),
            messages.SUCCESS,
            fail_silently=True,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    @admin.action(description="Deactivate selected ticket types")
    def deactivate_ticket_types(self, request, queryset):
        updated_count = queryset.filter(is_active=True).update(is_active=False)
        if updated_count:
            transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count)
        return updated_count

    @admin.action(description="Activate selected ticket types")
    def activate_ticket_types(self, request, queryset):
        invalid_statuses = (Event.Status.CANCELED, Event.Status.FINISHED)
        skipped_count = queryset.filter(event__status__in=invalid_statuses).count()
        updated_count = (
            queryset.exclude(event__status__in=invalid_statuses)
            .filter(is_active=False)
            .update(is_active=True)
        )
        if updated_count:
            transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count, skipped_count)
        return updated_count
