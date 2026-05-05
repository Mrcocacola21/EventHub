from types import SimpleNamespace

from django.test import TestCase

from apps.reviews.models import Review
from apps.reviews.serializers import ReviewCreateSerializer, ReviewSerializer

from .utils import ReviewTestMixin


class ReviewSerializerTests(ReviewTestMixin, TestCase):
    def request_for(self, user):
        return SimpleNamespace(user=user)

    def test_create_serializer_accepts_valid_paid_attendee_review(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        serializer = ReviewCreateSerializer(
            data={"rating": 5, "comment": "Excellent"},
            context={"request": self.request_for(self.user), "event": event},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        review = serializer.save()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.event, event)

    def test_rating_out_of_range_invalid(self):
        event = self.make_event()
        self.make_booking(event, self.user)

        for rating in (0, 6):
            serializer = ReviewCreateSerializer(
                data={"rating": rating},
                context={"request": self.request_for(self.user), "event": event},
            )
            self.assertFalse(serializer.is_valid())
            self.assertIn("rating", serializer.errors)

    def test_duplicate_review_invalid(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        Review.objects.create(user=self.user, event=event, rating=5)
        serializer = ReviewCreateSerializer(
            data={"rating": 4},
            context={"request": self.request_for(self.user), "event": event},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_output_serializer_keeps_server_owned_fields_read_only(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review.objects.create(user=self.user, event=event, rating=5)
        serializer = ReviewSerializer(
            review,
            data={
                "user": self.second_user.id,
                "event": self.make_event(title="Other").id,
                "is_published": False,
                "rating": 4,
            },
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.user, self.user)
        self.assertEqual(updated.event, event)
        self.assertTrue(updated.is_published)
        self.assertEqual(updated.rating, 4)
