from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone

from apps.bookings.tasks import send_booking_confirmation_email
from apps.common.tests.factories import BookingFactory, NotificationFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import cleanup_old_notifications


@pytest.mark.django_db
@pytest.mark.celery
def test_celery_test_settings_are_eager():
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
    assert settings.CELERY_TASK_EAGER_PROPAGATES is True


@pytest.mark.django_db
@pytest.mark.celery
def test_send_booking_confirmation_email_uses_locmem_mailbox():
    booking = BookingFactory()

    result = send_booking_confirmation_email(booking.id)

    assert result == "sent"
    assert len(mail.outbox) == 1
    assert booking.ticket_type.event.title in mail.outbox[0].subject
    assert str(booking.id) in mail.outbox[0].body


@pytest.mark.django_db
@pytest.mark.celery
def test_cleanup_old_notifications_deletes_only_old_read_notifications():
    old_read = NotificationFactory(is_read=True, read_at=timezone.now())
    old_unread = NotificationFactory(is_read=False)
    recent_read = NotificationFactory(is_read=True, read_at=timezone.now())
    Notification.objects.filter(id__in=[old_read.id, old_unread.id]).update(
        created_at=timezone.now() - timedelta(days=40),
    )

    deleted_count = cleanup_old_notifications(days=30)

    assert deleted_count == 1
    assert not Notification.objects.filter(id=old_read.id).exists()
    assert Notification.objects.filter(id=old_unread.id).exists()
    assert Notification.objects.filter(id=recent_read.id).exists()
