from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from apps.audit.models import AuditLog
from apps.events.cache import EventCacheService
from apps.notifications.models import Notification
from apps.reviews.models import Review

from .utils import ReviewTestMixin


LOCMEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "review-cache-tests",
    }
}


class ReviewAuditNotificationTests(ReviewTestMixin, APITestCase):
    @patch("apps.notifications.services.NotificationService.send_realtime_notification")
    def test_review_created_logs_audit_and_notifies_organizer(self, mocked_realtime):
        event = self.make_event()
        self.make_booking(event, self.user)
        self.client.force_authenticate(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("event-review-list", args=[event.id]),
                {"rating": 5, "comment": "Great"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(id=response.data["id"])
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.REVIEW_CREATED,
                entity_type="Review",
                entity_id=str(review.id),
                metadata__event_id=event.id,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.organizer,
                type=Notification.Type.REVIEW_CREATED,
                entity_type="Review",
                entity_id=str(review.id),
            ).exists()
        )
        mocked_realtime.assert_called_once()

    def test_publish_unpublish_and_delete_are_audited(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        self.client.force_authenticate(self.admin_user)

        unpublish = self.client.patch(
            reverse("review-detail", args=[review.id]),
            {"is_published": False},
            format="json",
        )
        publish = self.client.patch(
            reverse("review-detail", args=[review.id]),
            {"is_published": True},
            format="json",
        )
        deleted = self.client.delete(reverse("review-detail", args=[review.id]))

        self.assertEqual(unpublish.status_code, status.HTTP_200_OK)
        self.assertEqual(publish.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.REVIEW_UNPUBLISHED).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.REVIEW_PUBLISHED).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.REVIEW_DELETED).exists()
        )


@override_settings(CACHES=LOCMEM_CACHES)
class ReviewCacheInvalidationTests(ReviewTestMixin, APITransactionTestCase):
    def setUp(self):
        type(self).setUpTestData()
        cache.clear()

    def test_create_update_delete_review_bumps_events_cache_version(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        self.client.force_authenticate(self.user)
        before = EventCacheService.get_events_cache_version()

        created = self.client.post(
            reverse("event-review-list", args=[event.id]),
            {"rating": 5},
            format="json",
        )
        after_create = EventCacheService.get_events_cache_version()

        updated = self.client.patch(
            reverse("review-detail", args=[created.data["id"]]),
            {"rating": 4},
            format="json",
        )
        after_update = EventCacheService.get_events_cache_version()

        deleted = self.client.delete(reverse("review-detail", args=[created.data["id"]]))
        after_delete = EventCacheService.get_events_cache_version()

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertGreater(after_create, before)
        self.assertGreater(after_update, after_create)
        self.assertGreater(after_delete, after_update)

    def test_publish_unpublish_bumps_events_cache_version(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        self.client.force_authenticate(self.admin_user)
        before = EventCacheService.get_events_cache_version()

        unpublish = self.client.patch(
            reverse("review-detail", args=[review.id]),
            {"is_published": False},
            format="json",
        )
        after_unpublish = EventCacheService.get_events_cache_version()
        publish = self.client.patch(
            reverse("review-detail", args=[review.id]),
            {"is_published": True},
            format="json",
        )
        after_publish = EventCacheService.get_events_cache_version()

        self.assertEqual(unpublish.status_code, status.HTTP_200_OK)
        self.assertEqual(publish.status_code, status.HTTP_200_OK)
        self.assertGreater(after_unpublish, before)
        self.assertGreater(after_publish, after_unpublish)
