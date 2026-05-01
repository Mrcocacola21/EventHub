from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.tickets.models import TicketType


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELED = "CANCELED", "Canceled"
        EXPIRED = "EXPIRED", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAID,
        db_index=True,
    )
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.ImageField(
        upload_to="booking_qr_codes/",
        null=True,
        blank=True,
    )
    pdf_ticket = models.FileField(
        upload_to="booking_pdf_tickets/",
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["ticket_type", "status"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "booking"
        verbose_name_plural = "bookings"

    def __str__(self):
        return f"{self.user.email} - {self.ticket_type.name} - {self.status}"

    @property
    def event(self):
        return self.ticket_type.event

    @property
    def can_be_canceled(self):
        return self.status in (
            self.Status.PENDING,
            self.Status.PAID,
        ) and not self.is_used

    @property
    def can_be_used(self):
        return self.status == self.Status.PAID and not self.is_used

    def cancel(self):
        if not self.can_be_canceled:
            raise ValidationError("This booking cannot be canceled.")

        self.status = self.Status.CANCELED
        self.save(update_fields=["status", "updated_at"])
