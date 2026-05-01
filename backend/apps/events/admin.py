from django.contrib import admin

from apps.tickets.models import TicketType

from .models import Event, EventCategory


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    fields = (
        "name",
        "price",
        "quantity",
        "sold_count",
        "is_active",
        "sales_start",
        "sales_end",
    )
    readonly_fields = ("sold_count",)
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organizer",
        "category",
        "status",
        "is_published",
        "location",
        "start_datetime",
        "end_datetime",
        "created_at",
    )
    list_filter = ("status", "is_published", "category", "start_datetime")
    search_fields = ("title", "description", "location", "organizer__email")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "start_datetime"
    actions = ("publish_events", "cancel_events", "finish_events")
    inlines = (TicketTypeInline,)

    @admin.action(description="Publish selected events")
    def publish_events(self, request, queryset):
        for event in queryset:
            event.publish()

    @admin.action(description="Cancel selected events")
    def cancel_events(self, request, queryset):
        for event in queryset:
            event.cancel()

    @admin.action(description="Finish selected events")
    def finish_events(self, request, queryset):
        for event in queryset:
            event.finish()
