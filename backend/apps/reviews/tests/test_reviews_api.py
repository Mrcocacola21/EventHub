from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.reviews.models import Review

from .utils import ReviewTestMixin


class ReviewApiTests(ReviewTestMixin, APITestCase):
    def event_reviews_url(self, event):
        return reverse("event-review-list", args=[event.id])

    def review_url(self, review):
        return reverse("review-detail", args=[review.id])

    def results(self, response):
        return response.data.get("results", response.data)

    def ids(self, response):
        return [item["id"] for item in self.results(response)]

    def test_list_shows_published_reviews_only_to_public_users(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        self.make_booking(event, self.second_user)
        published = Review.objects.create(user=self.user, event=event, rating=5)
        unpublished = Review.objects.create(
            user=self.second_user,
            event=event,
            rating=2,
            is_published=False,
        )

        anonymous = self.client.get(self.event_reviews_url(event))
        self.client.force_authenticate(self.user)
        regular = self.client.get(self.event_reviews_url(event))

        self.assertIn(published.id, self.ids(anonymous))
        self.assertNotIn(unpublished.id, self.ids(anonymous))
        self.assertIn(published.id, self.ids(regular))
        self.assertNotIn(unpublished.id, self.ids(regular))

    def test_organizer_and_admin_can_see_unpublished_event_reviews(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(
            user=self.user,
            event=event,
            rating=3,
            is_published=False,
        )

        self.client.force_authenticate(self.organizer)
        organizer_response = self.client.get(self.event_reviews_url(event))

        self.client.force_authenticate(self.admin_user)
        admin_response = self.client.get(self.event_reviews_url(event))

        self.assertIn(review.id, self.ids(organizer_response))
        self.assertIn(review.id, self.ids(admin_response))

    def test_create_requires_auth_paid_booking_finished_event_and_no_duplicate(self):
        event = self.make_event()
        self.make_booking(event, self.user)

        anonymous = self.client.post(
            self.event_reviews_url(event),
            {"rating": 5},
            format="json",
        )

        self.client.force_authenticate(self.user)
        created = self.client.post(
            self.event_reviews_url(event),
            {"rating": 5, "comment": "Great"},
            format="json",
        )
        duplicate = self.client.post(
            self.event_reviews_url(event),
            {"rating": 4},
            format="json",
        )

        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["user"], self.user.id)
        self.assertEqual(created.data["event"], event.id)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_without_paid_booking_or_with_canceled_booking_cannot_create(self):
        event = self.make_event()
        self.make_booking(event, self.second_user, status=Booking.Status.CANCELED)

        self.client.force_authenticate(self.user)
        no_booking = self.client.post(
            self.event_reviews_url(event),
            {"rating": 5},
            format="json",
        )

        self.client.force_authenticate(self.second_user)
        canceled_booking = self.client.post(
            self.event_reviews_url(event),
            {"rating": 5},
            format="json",
        )

        self.assertEqual(no_booking.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(canceled_booking.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_review_future_event_or_override_url_event(self):
        event = self.make_event()
        future = self.make_future_event()
        self.make_booking(future, self.user)
        self.make_booking(event, self.user)
        self.client.force_authenticate(self.user)

        future_response = self.client.post(
            self.event_reviews_url(future),
            {"rating": 5},
            format="json",
        )
        created = self.client.post(
            self.event_reviews_url(event),
            {"rating": 5, "event": future.id, "user": self.second_user.id},
            format="json",
        )

        self.assertEqual(future_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(id=created.data["id"])
        self.assertEqual(review.event_id, event.id)
        self.assertEqual(review.user_id, self.user.id)

    def test_retrieve_visibility_rules(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(
            user=self.user,
            event=event,
            rating=5,
            is_published=False,
        )

        anonymous = self.client.get(self.review_url(review))

        self.client.force_authenticate(self.user)
        owner = self.client.get(self.review_url(review))

        self.client.force_authenticate(self.organizer)
        organizer = self.client.get(self.review_url(review))

        self.assertEqual(anonymous.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(owner.status_code, status.HTTP_200_OK)
        self.assertEqual(organizer.status_code, status.HTTP_200_OK)

    def test_owner_can_update_rating_comment_but_not_publication_or_identity(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        other_event = self.make_event(title="Other")
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            self.review_url(review),
            {
                "rating": 4,
                "comment": "Updated",
                "is_published": False,
                "event": other_event.id,
                "user": self.second_user.id,
            },
            format="json",
        )

        review.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "Updated")
        self.assertTrue(review.is_published)
        self.assertEqual(review.event_id, event.id)
        self.assertEqual(review.user_id, self.user.id)

    def test_admin_and_organizer_can_moderate_publication(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)

        self.client.force_authenticate(self.organizer)
        organizer_response = self.client.patch(
            self.review_url(review),
            {"is_published": False, "rating": 1},
            format="json",
        )
        review.refresh_from_db()

        self.client.force_authenticate(self.admin_user)
        admin_response = self.client.patch(
            self.review_url(review),
            {"is_published": True},
            format="json",
        )

        self.assertEqual(organizer_response.status_code, status.HTTP_200_OK)
        self.assertFalse(review.is_published)
        self.assertEqual(review.rating, 5)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)

    def test_another_user_cannot_update_or_delete(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        self.client.force_authenticate(self.second_user)

        patch_response = self.client.patch(
            self.review_url(review),
            {"rating": 1},
            format="json",
        )
        delete_response = self.client.delete(self.review_url(review))

        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_admin_and_organizer_can_delete(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        self.make_booking(event, self.second_user)
        owner_review = Review.objects.create(user=self.user, event=event, rating=5)
        organizer_review = Review.objects.create(
            user=self.second_user,
            event=event,
            rating=4,
        )

        self.client.force_authenticate(self.user)
        owner_delete = self.client.delete(self.review_url(owner_review))

        self.client.force_authenticate(self.organizer)
        organizer_delete = self.client.delete(self.review_url(organizer_review))

        self.assertEqual(owner_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(organizer_delete.status_code, status.HTTP_204_NO_CONTENT)
