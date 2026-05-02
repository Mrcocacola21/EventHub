from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.cache import EventCacheService
from apps.events.models import Event
from apps.tickets.models import TicketType

from .models import Booking
from .pdf import PDFTicketService
from .qr import QRCodeService


class BookingService:
    @classmethod
    def create_booking(cls, user, ticket_type_id, request=None):
        if not user or not user.is_authenticated:
            raise ValidationError("Authentication is required to create bookings.")

        if not ticket_type_id:
            raise ValidationError({"ticket_type_id": "This field is required."})

        with transaction.atomic():
            try:
                ticket_type = (
                    TicketType.objects.select_for_update()
                    .select_related("event", "event__organizer", "event__category")
                    .get(id=ticket_type_id)
                )
            except TicketType.DoesNotExist as exc:
                raise ValidationError(
                    {"ticket_type_id": "Ticket type does not exist."}
                ) from exc

            if not ticket_type.can_sell(1):
                raise ValidationError(
                    "Ticket type is not available for purchase."
                )

            booking = Booking.objects.create(
                user=user,
                ticket_type=ticket_type,
                status=Booking.Status.PAID,
                price_at_purchase=ticket_type.price,
                expires_at=None,
            )
            ticket_type.sold_count += 1
            ticket_type.save(update_fields=["sold_count", "updated_at"])
            QRCodeService.generate_for_booking(booking)
            PDFTicketService.generate_for_booking(booking)
            AuditService.log_booking_created(
                booking,
                request=request,
                user=user,
            )
            from .tasks import send_booking_confirmation_email

            transaction.on_commit(
                lambda: send_booking_confirmation_email.delay(booking.id),
            )
            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_booking_created(booking),
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return booking

    @classmethod
    def cancel_booking(cls, booking, user, request=None):
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        with transaction.atomic():
            locked_booking = (
                Booking.objects.select_for_update()
                .select_related(
                    "user",
                    "ticket_type",
                    "ticket_type__event",
                    "ticket_type__event__organizer",
                    "ticket_type__event__category",
                )
                .get(id=booking.id)
            )

            if not cls._user_can_cancel_booking(user, locked_booking):
                raise PermissionDenied("You cannot cancel this booking.")

            if not locked_booking.can_be_canceled:
                raise ValidationError("This booking cannot be canceled.")

            ticket_type = (
                TicketType.objects.select_for_update()
                .select_related("event", "event__organizer", "event__category")
                .get(id=locked_booking.ticket_type_id)
            )

            locked_booking.status = Booking.Status.CANCELED
            locked_booking.save(update_fields=["status", "updated_at"])

            if ticket_type.sold_count > 0:
                ticket_type.sold_count -= 1
                ticket_type.save(update_fields=["sold_count", "updated_at"])

            AuditService.log_booking_canceled(
                locked_booking,
                request=request,
                user=user,
            )
            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_booking_canceled(locked_booking),
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return locked_booking

    @classmethod
    def expire_booking(cls, booking_id):
        with transaction.atomic():
            try:
                locked_booking = (
                    Booking.objects.select_for_update()
                    .select_related(
                        "user",
                        "ticket_type",
                        "ticket_type__event",
                        "ticket_type__event__organizer",
                        "ticket_type__event__category",
                    )
                    .get(id=booking_id)
                )
            except Booking.DoesNotExist as exc:
                raise ValidationError("Booking does not exist.") from exc

            if locked_booking.status != Booking.Status.PENDING:
                return locked_booking

            ticket_type = (
                TicketType.objects.select_for_update()
                .select_related("event", "event__organizer", "event__category")
                .get(id=locked_booking.ticket_type_id)
            )

            locked_booking.status = Booking.Status.EXPIRED
            locked_booking.save(update_fields=["status", "updated_at"])

            if ticket_type.sold_count > 0:
                ticket_type.sold_count -= 1
                ticket_type.save(update_fields=["sold_count", "updated_at"])

            AuditService.log_action(
                action=AuditLog.Action.BOOKING_EXPIRED,
                entity_type="Booking",
                entity_id=locked_booking.id,
                metadata={
                    "user_id": locked_booking.user_id,
                    "ticket_type_id": locked_booking.ticket_type_id,
                    "event_id": locked_booking.ticket_type.event_id,
                    "status": locked_booking.status,
                    "price_at_purchase": str(locked_booking.price_at_purchase),
                },
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return locked_booking

    @staticmethod
    def _user_can_cancel_booking(user, booking):
        if user.is_superuser or user.is_admin_role:
            return True

        if booking.user_id == user.id:
            return True

        event = booking.ticket_type.event
        return user.is_organizer and event.organizer_id == user.id


class TicketValidationService:
    @classmethod
    def use_booking(cls, booking_id, checked_by_user, request=None):
        if not checked_by_user or not checked_by_user.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        with transaction.atomic():
            try:
                booking = (
                    Booking.objects.select_for_update()
                    .select_related(
                        "user",
                        "ticket_type",
                        "ticket_type__event",
                        "ticket_type__event__organizer",
                    )
                    .get(id=booking_id)
                )
            except Booking.DoesNotExist as exc:
                raise ValidationError("Booking does not exist.") from exc

            if not cls._user_can_use_booking(checked_by_user, booking):
                raise PermissionDenied("You cannot validate this booking.")

            if booking.is_used or booking.used_at is not None:
                raise ValidationError("This booking has already been used.")

            if booking.status != Booking.Status.PAID:
                raise ValidationError("Only paid bookings can be used.")

            if booking.ticket_type.event.status == Event.Status.CANCELED:
                raise ValidationError("Cannot use booking for a canceled event.")

            booking.is_used = True
            booking.used_at = timezone.now()
            booking.save(update_fields=["is_used", "used_at", "updated_at"])
            AuditService.log_booking_used(
                booking,
                request=request,
                user=checked_by_user,
            )
            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_booking_used(booking),
            )

        return booking

    @classmethod
    def use_booking_by_token(cls, token, checked_by_user, request=None):
        payload = QRCodeService.parse_token(token)
        return cls.use_booking(
            booking_id=payload.get("booking_id"),
            checked_by_user=checked_by_user,
            request=request,
        )

    @staticmethod
    def _user_can_use_booking(user, booking):
        if user.is_superuser or user.is_admin_role:
            return True

        event = booking.ticket_type.event
        return user.is_organizer and event.organizer_id == user.id
