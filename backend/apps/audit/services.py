import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @classmethod
    def log_action(
        cls,
        *,
        action,
        entity_type,
        entity_id=None,
        user=None,
        request=None,
        metadata=None,
    ):
        try:
            return AuditLog.objects.create(
                user=cls._resolve_user(user=user, request=request),
                action=action,
                entity_type=entity_type,
                entity_id="" if entity_id is None else str(entity_id),
                ip_address=cls._resolve_ip_address(request),
                user_agent=cls._resolve_user_agent(request),
                request_id=cls._resolve_request_id(request),
                metadata=metadata or {},
            )
        except Exception:
            logger.exception("Failed to create audit log.")
            return None

    @classmethod
    def log_event_created(cls, event, request=None, user=None):
        return cls._log_event(
            action=AuditLog.Action.EVENT_CREATED,
            event=event,
            request=request,
            user=user,
        )

    @classmethod
    def log_event_updated(cls, event, request=None, user=None):
        return cls._log_event(
            action=AuditLog.Action.EVENT_UPDATED,
            event=event,
            request=request,
            user=user,
        )

    @classmethod
    def log_event_published(cls, event, request=None, user=None):
        return cls._log_event(
            action=AuditLog.Action.EVENT_PUBLISHED,
            event=event,
            request=request,
            user=user,
        )

    @classmethod
    def log_event_canceled(cls, event, request=None, user=None):
        return cls._log_event(
            action=AuditLog.Action.EVENT_CANCELED,
            event=event,
            request=request,
            user=user,
        )

    @classmethod
    def log_event_finished(cls, event, request=None, user=None):
        return cls._log_event(
            action=AuditLog.Action.EVENT_FINISHED,
            event=event,
            request=request,
            user=user,
        )

    @classmethod
    def log_booking_created(cls, booking, request=None, user=None):
        return cls._log_booking(
            action=AuditLog.Action.BOOKING_CREATED,
            booking=booking,
            request=request,
            user=user,
        )

    @classmethod
    def log_booking_canceled(cls, booking, request=None, user=None):
        return cls._log_booking(
            action=AuditLog.Action.BOOKING_CANCELED,
            booking=booking,
            request=request,
            user=user,
        )

    @classmethod
    def log_booking_used(cls, booking, request=None, user=None):
        return cls._log_booking(
            action=AuditLog.Action.BOOKING_USED,
            booking=booking,
            request=request,
            user=user,
        )

    @classmethod
    def _log_event(cls, *, action, event, request=None, user=None):
        return cls.log_action(
            action=action,
            entity_type="Event",
            entity_id=event.id,
            request=request,
            user=user,
            metadata={
                "title": event.title,
                "status": event.status,
                "organizer_id": event.organizer_id,
            },
        )

    @classmethod
    def _log_booking(cls, *, action, booking, request=None, user=None):
        return cls.log_action(
            action=action,
            entity_type="Booking",
            entity_id=booking.id,
            request=request,
            user=user,
            metadata={
                "user_id": booking.user_id,
                "ticket_type_id": booking.ticket_type_id,
                "event_id": booking.ticket_type.event_id,
                "status": booking.status,
                "price_at_purchase": str(booking.price_at_purchase),
            },
        )

    @staticmethod
    def _resolve_user(*, user=None, request=None):
        if user is not None and getattr(user, "is_authenticated", False):
            return user

        request_user = getattr(request, "user", None)
        if request_user is not None and getattr(request_user, "is_authenticated", False):
            return request_user

        return None

    @classmethod
    def _resolve_ip_address(cls, request):
        if request is None:
            return None

        ip_address = getattr(request, "audit_ip_address", None)
        if ip_address:
            return ip_address

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _resolve_user_agent(request):
        if request is None:
            return ""

        return getattr(
            request,
            "audit_user_agent",
            request.META.get("HTTP_USER_AGENT", ""),
        )

    @staticmethod
    def _resolve_request_id(request):
        if request is None:
            return ""

        return getattr(request, "request_id", "") or ""
