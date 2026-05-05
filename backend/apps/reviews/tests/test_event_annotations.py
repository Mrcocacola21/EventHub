from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.events.models import Event
from apps.reviews.models import Review

from .utils import ReviewTestMixin


class EventReviewAnnotationTests(ReviewTestMixin, APITestCase):
    def make_public_past_event(self, **overrides):
        data = {"status": Event.Status.PUBLISHED}
        data.update(overrides)
        return self.make_event(**data)

    def test_event_detail_includes_average_rating_and_reviews_count(self):
        event = self.make_public_past_event()
        self.make_booking(event, self.user)
        self.make_booking(event, self.second_user)
        Review.objects.create(user=self.user, event=event, rating=5)
        Review.objects.create(user=self.second_user, event=event, rating=3)

        response = self.client.get(reverse("event-detail", args=[event.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["average_rating"], 4.0)
        self.assertEqual(response.data["reviews_count"], 2)

    def test_unpublished_reviews_do_not_affect_average_rating(self):
        event = self.make_public_past_event()
        self.make_booking(event, self.user)
        self.make_booking(event, self.second_user)
        Review.objects.create(user=self.user, event=event, rating=5)
        Review.objects.create(
            user=self.second_user,
            event=event,
            rating=1,
            is_published=False,
        )

        response = self.client.get(reverse("event-detail", args=[event.id]))

        self.assertEqual(response.data["average_rating"], 5.0)
        self.assertEqual(response.data["reviews_count"], 1)

    def test_event_list_includes_rating_summary_and_null_without_reviews(self):
        reviewed = self.make_public_past_event(title="Reviewed")
        empty = self.make_public_past_event(title="Empty")
        self.make_booking(reviewed, self.user)
        Review.objects.create(user=self.user, event=reviewed, rating=4)

        response = self.client.get(reverse("event-list"))
        results = response.data.get("results", response.data)
        by_id = {item["id"]: item for item in results}

        self.assertEqual(by_id[reviewed.id]["average_rating"], 4.0)
        self.assertEqual(by_id[reviewed.id]["reviews_count"], 1)
        self.assertIsNone(by_id[empty.id]["average_rating"])
        self.assertEqual(by_id[empty.id]["reviews_count"], 0)
