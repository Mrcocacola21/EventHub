from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Type(models.TextChoices):
        BOOKING_CREATED = "BOOKING_CREATED", "Booking created"
        BOOKING_CANCELED = "BOOKING_CANCELED", "Booking canceled"
        BOOKING_USED = "BOOKING_USED", "Booking used"
        EVENT_CANCELED = "EVENT_CANCELED", "Event canceled"
        EVENT_REMINDER = "EVENT_REMINDER", "Event reminder"
        MATCH_STARTED = "MATCH_STARTED", "Match started"
        MATCH_RESULT_UPDATED = "MATCH_RESULT_UPDATED", "Match result updated"
        TOURNAMENT_FINISHED = "TOURNAMENT_FINISHED", "Tournament finished"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    type = models.CharField(max_length=50, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    entity_type = models.CharField(max_length=100, blank=True, db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["type", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        return f"{self.user.email} - {self.type} - {self.title}"

    def mark_as_read(self):
        if self.is_read:
            return

        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at", "updated_at"])
