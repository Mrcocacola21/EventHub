from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.reviews.admin import ReviewAdmin
from apps.reviews.models import Review

from .utils import ReviewTestMixin


class ReviewAdminTests(ReviewTestMixin, TestCase):
    def request(self):
        request = RequestFactory().post("/")
        request.user = self.admin_user
        return request

    def test_review_admin_registered_and_configured(self):
        review_admin = admin.site._registry[Review]

        self.assertIsInstance(review_admin, ReviewAdmin)
        for field_name in ("event", "user", "rating", "is_published"):
            self.assertIn(field_name, review_admin.list_display)
        self.assertIn("rating", review_admin.list_filter)
        self.assertIn("is_published", review_admin.list_filter)
        self.assertIn("user__email", review_admin.search_fields)
        self.assertIn("event__title", review_admin.search_fields)
        self.assertIn("publish_reviews", review_admin.actions)
        self.assertIn("unpublish_reviews", review_admin.actions)

    def test_admin_actions_publish_and_unpublish_reviews(self):
        review_admin = admin.site._registry[Review]
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)

        review_admin.unpublish_reviews(
            self.request(),
            Review.objects.filter(id=review.id),
        )
        review.refresh_from_db()
        self.assertFalse(review.is_published)

        review_admin.publish_reviews(
            self.request(),
            Review.objects.filter(id=review.id),
        )
        review.refresh_from_db()
        self.assertTrue(review.is_published)
