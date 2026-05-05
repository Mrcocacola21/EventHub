from django.contrib import admin, messages
from django.db import transaction

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.cache import EventCacheService

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event",
        "user",
        "rating",
        "is_published",
        "created_at",
    )
    list_filter = ("rating", "is_published", "created_at", "event__category")
    search_fields = ("user__email", "user__username", "event__title", "comment")
    readonly_fields = ("id", "user", "event", "created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("user", "event", "event__organizer", "event__category")
    actions = ("publish_reviews", "unpublish_reviews")

    @admin.action(description="Publish selected reviews")
    def publish_reviews(self, request, queryset):
        updated_count = 0
        for review in queryset.select_related("event", "user"):
            if review.is_published:
                continue
            review.is_published = True
            review.save(update_fields=["is_published", "updated_at"])
            self._log_review_moderation(
                request,
                review,
                AuditLog.Action.REVIEW_PUBLISHED,
            )
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self.message_user(
            request,
            f"{updated_count} review(s) published.",
            messages.SUCCESS,
            fail_silently=True,
        )
        return updated_count

    @admin.action(description="Unpublish selected reviews")
    def unpublish_reviews(self, request, queryset):
        updated_count = 0
        for review in queryset.select_related("event", "user"):
            if not review.is_published:
                continue
            review.is_published = False
            review.save(update_fields=["is_published", "updated_at"])
            self._log_review_moderation(
                request,
                review,
                AuditLog.Action.REVIEW_UNPUBLISHED,
            )
            updated_count += 1
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        self.message_user(
            request,
            f"{updated_count} review(s) unpublished.",
            messages.SUCCESS,
            fail_silently=True,
        )
        return updated_count

    @staticmethod
    def _log_review_moderation(request, review, action):
        AuditService.log_action(
            action=action,
            entity_type="Review",
            entity_id=review.id,
            request=request,
            metadata={
                "review_id": review.id,
                "event_id": review.event_id,
                "rating": review.rating,
                "user_id": review.user_id,
                "is_published": review.is_published,
            },
        )
