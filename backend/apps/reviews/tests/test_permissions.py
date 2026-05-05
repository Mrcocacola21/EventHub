from django.test import RequestFactory, TestCase

from apps.reviews.permissions import IsReviewOwnerOrEventOrganizerOrAdmin
from apps.reviews.models import Review

from .utils import ReviewTestMixin


class ReviewPermissionTests(ReviewTestMixin, TestCase):
    def request_for(self, user):
        request = RequestFactory().patch("/")
        request.user = user
        return request

    def test_owner_event_organizer_and_admin_allowed(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        permission = IsReviewOwnerOrEventOrganizerOrAdmin()

        self.assertTrue(permission.has_object_permission(self.request_for(self.user), None, review))
        self.assertTrue(permission.has_object_permission(self.request_for(self.organizer), None, review))
        self.assertTrue(permission.has_object_permission(self.request_for(self.admin_user), None, review))
        self.assertFalse(
            permission.has_object_permission(
                self.request_for(self.second_user),
                None,
                review,
            )
        )
