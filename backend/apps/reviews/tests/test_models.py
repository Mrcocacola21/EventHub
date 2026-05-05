from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.bookings.models import Booking
from apps.events.models import Event
from apps.reviews.models import Review

from .utils import ReviewTestMixin


class ReviewModelTests(ReviewTestMixin, TestCase):
    def test_review_created_and_str_is_readable(self):
        event = self.make_event()
        self.make_booking(event, self.user)

        review = Review.objects.create(
            user=self.user,
            event=event,
            rating=5,
            comment="Great event",
        )

        self.assertEqual(str(review), f"{self.user.email} -> {event.title}: 5")
        self.assertTrue(review.is_published)

    def test_rating_must_be_between_one_and_five(self):
        event = self.make_event()
        self.make_booking(event, self.user)

        for rating in (0, 6):
            with self.subTest(rating=rating):
                review = Review(user=self.user, event=event, rating=rating)
                with self.assertRaises(ValidationError):
                    review.full_clean()

    def test_duplicate_user_event_denied(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        Review.objects.create(user=self.user, event=event, rating=4)

        with self.assertRaises(IntegrityError):
            Review.objects.create(user=self.user, event=event, rating=5)

    def test_cannot_review_draft_or_future_event(self):
        draft = self.make_event(status=Event.Status.DRAFT)
        future = self.make_future_event()
        self.make_booking(draft, self.user)
        self.make_booking(future, self.user)

        for event in (draft, future):
            with self.subTest(event=event.title):
                review = Review(user=self.user, event=event, rating=5)
                with self.assertRaises(ValidationError):
                    review.full_clean()

    def test_paid_booking_required(self):
        event = self.make_event()

        review = Review(user=self.user, event=event, rating=5)

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_canceled_or_expired_booking_does_not_allow_review(self):
        event = self.make_event()

        for booking_status in (Booking.Status.CANCELED, Booking.Status.EXPIRED):
            with self.subTest(status=booking_status):
                user = self.second_user if booking_status == Booking.Status.CANCELED else self.user
                self.make_booking(event, user, status=booking_status)
                review = Review(user=user, event=event, rating=5)
                with self.assertRaises(ValidationError):
                    review.full_clean()

    def test_finished_event_with_paid_booking_can_be_reviewed(self):
        event = self.make_event()
        self.make_booking(event, self.user)
        review = Review(user=self.user, event=event, rating=5)

        review.full_clean()
