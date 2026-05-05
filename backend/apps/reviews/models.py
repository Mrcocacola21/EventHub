from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.events.models import Event


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                name="unique_review_per_user_event",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "is_published", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
        verbose_name = "review"
        verbose_name_plural = "reviews"

    def __str__(self):
        return f"{self.user.email} -> {self.event.title}: {self.rating}"

    def clean(self):
        errors = {}

        if self.rating is not None and not 1 <= self.rating <= 5:
            errors["rating"] = "Rating must be between 1 and 5."

        event = getattr(self, "event", None)
        user = getattr(self, "user", None)

        if event:
            if event.status in (Event.Status.DRAFT, Event.Status.CANCELED):
                errors["event"] = "Only completed events can be reviewed."
            elif (
                event.status != Event.Status.FINISHED
                and event.end_datetime
                and event.end_datetime > timezone.now()
            ):
                errors["event"] = "Only finished or past events can be reviewed."

        if self.user_id and self.event_id:
            queryset = Review.objects.filter(
                user_id=self.user_id,
                event_id=self.event_id,
            )
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                errors["event"] = "User has already reviewed this event."

        if user and event and not self._has_paid_booking():
            errors["user"] = "Only paid attendees can review this event."

        if errors:
            raise ValidationError(errors)

    def _has_paid_booking(self):
        from apps.bookings.models import Booking

        return Booking.objects.filter(
            user_id=self.user_id,
            ticket_type__event_id=self.event_id,
            status=Booking.Status.PAID,
        ).exists()
