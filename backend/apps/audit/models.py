from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        USER_REGISTERED = "USER_REGISTERED", "User registered"
        EVENT_CREATED = "EVENT_CREATED", "Event created"
        EVENT_UPDATED = "EVENT_UPDATED", "Event updated"
        EVENT_PUBLISHED = "EVENT_PUBLISHED", "Event published"
        EVENT_CANCELED = "EVENT_CANCELED", "Event canceled"
        EVENT_FINISHED = "EVENT_FINISHED", "Event finished"
        TICKET_TYPE_CREATED = "TICKET_TYPE_CREATED", "Ticket type created"
        BOOKING_CREATED = "BOOKING_CREATED", "Booking created"
        BOOKING_CANCELED = "BOOKING_CANCELED", "Booking canceled"
        BOOKING_EXPIRED = "BOOKING_EXPIRED", "Booking expired"
        BOOKING_USED = "BOOKING_USED", "Booking used"
        EVENT_REMINDER_SENT = "EVENT_REMINDER_SENT", "Event reminder sent"
        TOURNAMENT_CREATED = "TOURNAMENT_CREATED", "Tournament created"
        TOURNAMENT_PARTICIPANT_REGISTERED = (
            "TOURNAMENT_PARTICIPANT_REGISTERED",
            "Tournament participant registered",
        )
        TOURNAMENT_REGISTRATION_OPENED = (
            "TOURNAMENT_REGISTRATION_OPENED",
            "Tournament registration opened",
        )
        TOURNAMENT_STARTED = "TOURNAMENT_STARTED", "Tournament started"
        TOURNAMENT_FINISHED = "TOURNAMENT_FINISHED", "Tournament finished"
        TOURNAMENT_CANCELED = "TOURNAMENT_CANCELED", "Tournament canceled"
        MATCH_RESULT_SUBMITTED = "MATCH_RESULT_SUBMITTED", "Match result submitted"
        REVIEW_CREATED = "REVIEW_CREATED", "Review created"
        REVIEW_UPDATED = "REVIEW_UPDATED", "Review updated"
        REVIEW_DELETED = "REVIEW_DELETED", "Review deleted"
        REVIEW_PUBLISHED = "REVIEW_PUBLISHED", "Review published"
        REVIEW_UNPUBLISHED = "REVIEW_UNPUBLISHED", "Review unpublished"
        QR_REGENERATED = "QR_REGENERATED", "QR regenerated"
        PDF_REGENERATED = "PDF_REGENERATED", "PDF regenerated"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(
        max_length=100,
        choices=Action.choices,
        db_index=True,
    )
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["request_id"]),
        ]
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"
