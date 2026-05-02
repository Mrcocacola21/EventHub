from django.contrib import admin, messages
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.models import Event

from .models import Booking
from .pdf import PDFTicketService
from .qr import QRCodeService
from .services import BookingService, TicketValidationService


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "event_title",
        "ticket_type",
        "status",
        "price_at_purchase",
        "is_used",
        "has_qr_code",
        "has_pdf_ticket",
        "created_at",
        "used_at",
        "reminder_sent_at",
    )
    list_filter = (
        "status",
        "is_used",
        "created_at",
        "used_at",
        "reminder_sent_at",
        "ticket_type__event",
        "ticket_type__event__category",
    )
    search_fields = (
        "user__email",
        "user__username",
        "ticket_type__name",
        "ticket_type__event__title",
    )
    readonly_fields = (
        "id",
        "user",
        "ticket_type",
        "price_at_purchase",
        "qr_code",
        "pdf_ticket",
        "is_used",
        "used_at",
        "reminder_sent_at",
        "created_at",
        "updated_at",
        "event_title",
    )
    list_select_related = (
        "user",
        "ticket_type",
        "ticket_type__event",
        "ticket_type__event__organizer",
        "ticket_type__event__category",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = (
        "cancel_bookings",
        "mark_bookings_used",
        "regenerate_qr_codes",
        "regenerate_pdf_tickets",
    )

    @admin.display(ordering="ticket_type__event__title", description="Event")
    def event_title(self, obj):
        return obj.ticket_type.event.title

    @admin.display(boolean=True, description="QR code")
    def has_qr_code(self, obj):
        return bool(obj.qr_code)

    @admin.display(boolean=True, description="PDF ticket")
    def has_pdf_ticket(self, obj):
        return bool(obj.pdf_ticket)

    def _message_action_result(self, request, message):
        self.message_user(
            request,
            message,
            messages.SUCCESS,
            fail_silently=True,
        )

    @admin.action(description="Cancel selected bookings")
    def cancel_bookings(self, request, queryset):
        canceled_count = 0
        skipped_count = 0
        for booking in queryset.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
            "ticket_type__event__category",
        ):
            if not booking.can_be_canceled:
                skipped_count += 1
                continue

            try:
                BookingService.cancel_booking(
                    booking=booking,
                    user=request.user,
                    request=request,
                )
            except (PermissionDenied, ValidationError):
                skipped_count += 1
            else:
                canceled_count += 1

        self._message_action_result(
            request,
            (
                f"{canceled_count} booking(s) canceled. "
                f"{skipped_count} booking(s) skipped."
            ),
        )
        return canceled_count

    @admin.action(description="Mark selected bookings used")
    def mark_bookings_used(self, request, queryset):
        used_count = 0
        skipped_count = 0
        for booking in queryset.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
            "ticket_type__event__category",
        ):
            if not (
                booking.status == Booking.Status.PAID
                and not booking.is_used
                and booking.ticket_type.event.status != Event.Status.CANCELED
            ):
                skipped_count += 1
                continue

            try:
                TicketValidationService.use_booking(
                    booking_id=booking.id,
                    checked_by_user=request.user,
                    request=request,
                )
            except (PermissionDenied, ValidationError):
                skipped_count += 1
            else:
                used_count += 1

        self._message_action_result(
            request,
            f"{used_count} booking(s) used. {skipped_count} booking(s) skipped.",
        )
        return used_count

    @admin.action(description="Regenerate QR codes")
    def regenerate_qr_codes(self, request, queryset):
        regenerated_count = 0
        for booking in queryset.select_related("user", "ticket_type"):
            QRCodeService.generate_for_booking(booking, force=True)
            AuditService.log_action(
                action=AuditLog.Action.QR_REGENERATED,
                entity_type="Booking",
                entity_id=booking.id,
                request=request,
                user=request.user,
                metadata={
                    "user_id": booking.user_id,
                    "ticket_type_id": booking.ticket_type_id,
                    "status": booking.status,
                },
            )
            regenerated_count += 1

        self._message_action_result(
            request,
            f"{regenerated_count} QR code(s) regenerated.",
        )
        return regenerated_count

    @admin.action(description="Regenerate PDF tickets")
    def regenerate_pdf_tickets(self, request, queryset):
        regenerated_count = 0
        for booking in queryset.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
            "ticket_type__event__category",
        ):
            PDFTicketService.generate_for_booking(booking, force=True)
            AuditService.log_action(
                action=AuditLog.Action.PDF_REGENERATED,
                entity_type="Booking",
                entity_id=booking.id,
                request=request,
                user=request.user,
                metadata={
                    "user_id": booking.user_id,
                    "ticket_type_id": booking.ticket_type_id,
                    "event_id": booking.ticket_type.event_id,
                    "status": booking.status,
                },
            )
            regenerated_count += 1

        self._message_action_result(
            request,
            f"{regenerated_count} PDF ticket(s) regenerated.",
        )
        return regenerated_count
