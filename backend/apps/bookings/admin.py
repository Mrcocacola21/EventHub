from django.contrib import admin

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
        "ticket_type",
        "event_title",
        "status",
        "price_at_purchase",
        "is_used",
        "used_at",
        "has_qr_code",
        "has_pdf_ticket",
        "created_at",
    )
    list_filter = ("status", "is_used", "created_at", "ticket_type__event")
    search_fields = (
        "user__email",
        "ticket_type__name",
        "ticket_type__event__title",
    )
    readonly_fields = (
        "price_at_purchase",
        "qr_code",
        "pdf_ticket",
        "created_at",
        "updated_at",
        "used_at",
    )
    list_select_related = ("user", "ticket_type", "ticket_type__event")
    actions = (
        "cancel_bookings",
        "mark_bookings_used",
        "regenerate_qr_codes",
        "regenerate_pdf_tickets",
    )

    @admin.display(description="Event")
    def event_title(self, obj):
        return obj.ticket_type.event.title

    @admin.display(boolean=True, description="QR code")
    def has_qr_code(self, obj):
        return bool(obj.qr_code)

    @admin.display(boolean=True, description="PDF ticket")
    def has_pdf_ticket(self, obj):
        return bool(obj.pdf_ticket)

    @admin.action(description="Cancel selected bookings")
    def cancel_bookings(self, request, queryset):
        for booking in queryset.select_related(
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
        ):
            if booking.can_be_canceled:
                BookingService.cancel_booking(booking=booking, user=request.user)

    @admin.action(description="Mark selected bookings used")
    def mark_bookings_used(self, request, queryset):
        for booking in queryset.select_related(
            "ticket_type",
            "ticket_type__event",
            "ticket_type__event__organizer",
        ):
            if (
                booking.status == Booking.Status.PAID
                and not booking.is_used
                and booking.ticket_type.event.status != Event.Status.CANCELED
            ):
                TicketValidationService.use_booking(
                    booking_id=booking.id,
                    checked_by_user=request.user,
                )

    @admin.action(description="Regenerate QR codes")
    def regenerate_qr_codes(self, request, queryset):
        for booking in queryset:
            QRCodeService.generate_for_booking(booking, force=True)

    @admin.action(description="Regenerate PDF tickets")
    def regenerate_pdf_tickets(self, request, queryset):
        for booking in queryset.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
        ):
            PDFTicketService.generate_for_booking(booking, force=True)
