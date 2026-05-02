import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import NotificationSerializer
from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    @classmethod
    def create_notification(
        cls,
        *,
        user,
        type,
        title,
        message,
        entity_type="",
        entity_id="",
        metadata=None,
    ):
        if user is None:
            logger.warning("Notification skipped because user is missing.")
            return None

        try:
            notification = Notification.objects.create(
                user=user,
                type=type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id not in (None, "") else "",
                metadata=metadata or {},
            )
        except Exception:
            logger.exception("Failed to create notification.")
            return None

        cls.send_realtime_notification(notification)
        return notification

    @classmethod
    def send_realtime_notification(cls, notification):
        try:
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return

            notification_data = dict(NotificationSerializer(notification).data)
            payload = {
                "type": "notification",
                "notification": notification_data,
            }
            async_to_sync(channel_layer.group_send)(
                f"user_notifications_{notification.user_id}",
                {
                    "type": "notification.event",
                    "payload": payload,
                },
            )
        except Exception:
            logger.exception("Failed to send realtime notification.")

    @classmethod
    def notify_booking_created(cls, booking):
        try:
            event = booking.ticket_type.event
            return cls.create_notification(
                user=booking.user,
                type=Notification.Type.BOOKING_CREATED,
                title="Ticket booked",
                message=(
                    f"Your ticket for {event.title} "
                    f"({booking.ticket_type.name}) has been booked."
                ),
                entity_type="Booking",
                entity_id=booking.id,
                metadata=cls._booking_metadata(booking),
            )
        except Exception:
            logger.exception("Failed to create booking created notification.")
            return None

    @classmethod
    def notify_booking_canceled(cls, booking):
        try:
            event = booking.ticket_type.event
            return cls.create_notification(
                user=booking.user,
                type=Notification.Type.BOOKING_CANCELED,
                title="Booking canceled",
                message=f"Your booking for {event.title} has been canceled.",
                entity_type="Booking",
                entity_id=booking.id,
                metadata=cls._booking_metadata(booking),
            )
        except Exception:
            logger.exception("Failed to create booking canceled notification.")
            return None

    @classmethod
    def notify_booking_used(cls, booking):
        try:
            event = booking.ticket_type.event
            return cls.create_notification(
                user=booking.user,
                type=Notification.Type.BOOKING_USED,
                title="Ticket used",
                message=f"Your ticket for {event.title} has been used.",
                entity_type="Booking",
                entity_id=booking.id,
                metadata=cls._booking_metadata(booking),
            )
        except Exception:
            logger.exception("Failed to create booking used notification.")
            return None

    @classmethod
    def notify_event_canceled(cls, event):
        try:
            from apps.bookings.models import Booking

            bookings = (
                Booking.objects.filter(
                    ticket_type__event=event,
                    status=Booking.Status.PAID,
                )
                .select_related("user")
                .order_by("user_id")
            )

            notifications = []
            seen_user_ids = set()
            for booking in bookings:
                if booking.user_id in seen_user_ids:
                    continue
                seen_user_ids.add(booking.user_id)

                if Notification.objects.filter(
                    user_id=booking.user_id,
                    type=Notification.Type.EVENT_CANCELED,
                    entity_type="Event",
                    entity_id=str(event.id),
                ).exists():
                    continue

                notification = cls._create_event_canceled_notification(
                    user=booking.user,
                    event=event,
                )
                if notification is not None:
                    notifications.append(notification)

            return notifications
        except Exception:
            logger.exception("Failed to create event canceled notifications.")
            return []

    @classmethod
    def notify_event_reminder(cls, booking):
        try:
            event = booking.ticket_type.event
            return cls.create_notification(
                user=booking.user,
                type=Notification.Type.EVENT_REMINDER,
                title="Event reminder",
                message=f"{event.title} starts soon at {event.location}.",
                entity_type="Booking",
                entity_id=booking.id,
                metadata=cls._booking_metadata(booking),
            )
        except Exception:
            logger.exception("Failed to create event reminder notification.")
            return None

    @classmethod
    def notify_match_started(cls, match):
        """Placeholder for tournament match notifications after Match exists."""
        if match is None:
            return None
        return None

    @classmethod
    def notify_match_result_updated(cls, match):
        """Placeholder for tournament result notifications after Match exists."""
        if match is None:
            return None
        return None

    @staticmethod
    def _booking_metadata(booking):
        event = booking.ticket_type.event
        return {
            "booking_id": booking.id,
            "event_id": event.id,
            "ticket_type_id": booking.ticket_type_id,
            "price_at_purchase": str(booking.price_at_purchase),
            "event_title": event.title,
        }

    @classmethod
    def _create_event_canceled_notification(cls, *, user, event):
        return cls.create_notification(
            user=user,
            type=Notification.Type.EVENT_CANCELED,
            title="Event canceled",
            message=f"{event.title} has been canceled.",
            entity_type="Event",
            entity_id=event.id,
            metadata={
                "event_id": event.id,
                "event_title": event.title,
                "status": event.status,
            },
        )
