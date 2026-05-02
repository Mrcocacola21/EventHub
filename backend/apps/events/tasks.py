from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.bookings.models import Booking

from .models import Event


@shared_task
def send_event_reminders():
    now = timezone.now()
    window_end = now + timedelta(hours=24)
    bookings = (
        Booking.objects.select_related(
            "user",
            "ticket_type",
            "ticket_type__event",
        )
        .filter(
            status=Booking.Status.PAID,
            reminder_sent_at__isnull=True,
            ticket_type__event__status=Event.Status.PUBLISHED,
            ticket_type__event__is_published=True,
            ticket_type__event__start_datetime__gte=now,
            ticket_type__event__start_datetime__lte=window_end,
        )
        .order_by("id")
    )

    sent_count = 0
    reminder_sent_at = timezone.now()
    for booking in bookings:
        event = booking.ticket_type.event
        event_start = timezone.localtime(event.start_datetime).strftime(
            "%Y-%m-%d %H:%M"
        )
        subject = f"Reminder: {event.title} starts soon"
        body = "\n".join(
            [
                f"Event: {event.title}",
                f"Start time: {event_start}",
                f"Location: {event.location}",
                f"Booking ID: {booking.id}",
            ]
        )
        sent = send_mail(
            subject,
            body,
            None,
            [booking.user.email],
            fail_silently=False,
        )
        if sent:
            booking.reminder_sent_at = reminder_sent_at
            booking.save(update_fields=["reminder_sent_at", "updated_at"])
            AuditService.log_action(
                action=AuditLog.Action.EVENT_REMINDER_SENT,
                entity_type="Booking",
                entity_id=booking.id,
                user=booking.user,
                metadata={
                    "event_id": event.id,
                    "event_title": event.title,
                    "event_start": event.start_datetime.isoformat(),
                },
            )
            from apps.notifications.services import NotificationService

            NotificationService.notify_event_reminder(booking)
            sent_count += 1

    return sent_count
