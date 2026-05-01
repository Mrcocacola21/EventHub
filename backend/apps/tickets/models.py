from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.events.models import Event


class TicketType(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    sold_count = models.PositiveIntegerField(default=0)
    sales_start = models.DateTimeField(null=True, blank=True)
    sales_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "name"],
                name="unique_ticket_type_name_per_event",
            ),
        ]
        verbose_name = "ticket type"
        verbose_name_plural = "ticket types"

    def __str__(self):
        return f"{self.event.title} - {self.name}"

    @property
    def available_quantity(self):
        return self.quantity - self.sold_count

    @property
    def is_sold_out(self):
        return self.sold_count >= self.quantity

    @property
    def is_sales_period_active(self):
        now = timezone.now()
        starts_ok = self.sales_start is None or now >= self.sales_start
        ends_ok = self.sales_end is None or now <= self.sales_end
        return starts_ok and ends_ok

    @property
    def is_available_for_purchase(self):
        return (
            self.is_active
            and self.event.is_active_for_booking
            and self.is_sales_period_active
            and self.sold_count < self.quantity
        )

    def can_sell(self, count=1):
        if count <= 0:
            return False

        return (
            self.is_available_for_purchase
            and self.sold_count + count <= self.quantity
        )

    def clean(self):
        errors = {}

        if self.price is not None and self.price < 0:
            errors["price"] = "Price must be greater than or equal to zero."

        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."

        if (
            self.sold_count is not None
            and self.quantity is not None
            and self.sold_count > self.quantity
        ):
            errors["sold_count"] = "Sold count cannot exceed quantity."

        if self.sales_start and self.sales_end and self.sales_end <= self.sales_start:
            errors["sales_end"] = "Sales end must be after sales start."

        event = self.event if self.event_id else None
        if event:
            organizer = event.organizer
            if not (
                organizer.is_superuser
                or organizer.is_organizer
                or organizer.is_admin_role
            ):
                errors["event"] = (
                    "Ticket types can only be created for events owned by "
                    "organizer or admin users."
                )

            if self.is_active and event.status in (
                Event.Status.CANCELED,
                Event.Status.FINISHED,
            ):
                errors["is_active"] = (
                    "Ticket types cannot be active for canceled or finished events."
                )

        if errors:
            raise ValidationError(errors)
