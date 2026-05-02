from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.audit.services import AuditService
from apps.tickets.models import TicketType

from .cache import EventCacheService
from .models import Event, EventCategory

# TournamentAdmin will be added later when the Tournament app is implemented.


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "events_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    @admin.display(description="Events")
    def events_count(self, obj):
        return obj.events.count()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        transaction.on_commit(EventCacheService.invalidate_events_cache)


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    fields = (
        "name",
        "price",
        "quantity",
        "sold_count",
        "available_quantity_display",
        "is_active",
        "sales_start",
        "sales_end",
    )
    readonly_fields = ("sold_count", "available_quantity_display")
    extra = 0
    show_change_link = True

    @admin.display(description="Available")
    def available_quantity_display(self, obj):
        if not obj.pk:
            return "-"
        return obj.available_quantity


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "category",
        "organizer",
        "status",
        "is_published",
        "location",
        "start_datetime",
        "end_datetime",
        "ticket_types_count",
        "bookings_count",
        "created_at",
    )
    list_filter = (
        "status",
        "is_published",
        "category",
        "start_datetime",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "location",
        "organizer__email",
        "organizer__username",
        "category__name",
    )
    readonly_fields = (
        "id",
        "slug",
        "created_at",
        "updated_at",
        "ticket_types_count",
        "bookings_count",
    )
    date_hierarchy = "start_datetime"
    ordering = ("start_datetime",)
    list_select_related = ("organizer", "category")
    actions = ("publish_events", "cancel_events", "finish_events", "mark_as_draft")
    inlines = (TicketTypeInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("organizer", "category")
            .annotate(
                ticket_types_total=Count("ticket_types", distinct=True),
                bookings_total=Count("ticket_types__bookings", distinct=True),
            )
        )

    @admin.display(description="Ticket types")
    def ticket_types_count(self, obj):
        return getattr(obj, "ticket_types_total", obj.ticket_types.count())

    @admin.display(description="Bookings")
    def bookings_count(self, obj):
        if hasattr(obj, "bookings_total"):
            return obj.bookings_total
        return obj.ticket_types.aggregate(total=Count("bookings"))["total"]

    def _message_action_result(self, request, count, label):
        self.message_user(
            request,
            f"{count} event(s) {label}.",
            messages.SUCCESS,
            fail_silently=True,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    @admin.action(description="Publish selected events")
    def publish_events(self, request, queryset):
        updated_count = 0
        for event in queryset:
            event.publish()
            AuditService.log_event_published(
                event,
                request=request,
                user=request.user,
            )
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count, "published")
        return updated_count

    @admin.action(description="Cancel selected events")
    def cancel_events(self, request, queryset):
        updated_count = 0
        for event in queryset:
            previous_status = event.status
            event.cancel()
            AuditService.log_event_canceled(
                event,
                request=request,
                user=request.user,
            )
            if previous_status != Event.Status.CANCELED:
                from apps.notifications.services import NotificationService

                transaction.on_commit(
                    lambda event=event: NotificationService.notify_event_canceled(
                        event
                    ),
                )
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count, "canceled")
        return updated_count

    @admin.action(description="Finish selected events")
    def finish_events(self, request, queryset):
        updated_count = 0
        for event in queryset:
            event.finish()
            AuditService.log_event_finished(
                event,
                request=request,
                user=request.user,
            )
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count, "finished")
        return updated_count

    @admin.action(description="Mark selected events as draft")
    def mark_as_draft(self, request, queryset):
        updated_count = 0
        for event in queryset:
            event.status = Event.Status.DRAFT
            event.is_published = False
            event.updated_at = timezone.now()
            event.save(update_fields=["status", "is_published", "updated_at"])
            AuditService.log_event_updated(event, request=request, user=request.user)
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self._message_action_result(request, updated_count, "marked as draft")
        return updated_count
