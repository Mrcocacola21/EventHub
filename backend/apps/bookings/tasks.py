import logging

from celery import shared_task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Booking
from .services import BookingService

logger = logging.getLogger(__name__)


@shared_task
def send_booking_confirmation_email(booking_id):
    try:
        booking = (
            Booking.objects.select_related(
                "user",
                "ticket_type",
                "ticket_type__event",
            )
            .get(id=booking_id)
        )
    except Booking.DoesNotExist:
        logger.warning("Booking %s not found for confirmation email.", booking_id)
        return "not_found"

    event = booking.ticket_type.event
    event_start = timezone.localtime(event.start_datetime).strftime("%Y-%m-%d %H:%M")
    subject = f"Your EventHub ticket for {event.title}"
    body = "\n".join(
        [
            f"Hello {booking.user.email},",
            "",
            "Your booking is confirmed.",
            f"Booking ID: {booking.id}",
            f"Event: {event.title}",
            f"Date/time: {event_start}",
            f"Location: {event.location}",
            f"Ticket type: {booking.ticket_type.name}",
            f"Price: {booking.price_at_purchase}",
        ]
    )
    send_mail(subject, body, None, [booking.user.email], fail_silently=False)
    return "sent"


@shared_task
def expire_pending_bookings():
    booking_ids = list(
        Booking.objects.filter(
            status=Booking.Status.PENDING,
            expires_at__isnull=False,
            expires_at__lte=timezone.now(),
        ).values_list("id", flat=True)
    )

    expired_count = 0
    for booking_id in booking_ids:
        with transaction.atomic():
            booking = BookingService.expire_booking(booking_id)
        if booking.status == Booking.Status.EXPIRED:
            expired_count += 1

    return expired_count
