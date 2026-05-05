from django.urls import path

from .views import EventReviewListCreateView, ReviewDetailView

urlpatterns = [
    path(
        "events/<int:event_id>/reviews/",
        EventReviewListCreateView.as_view(),
        name="event-review-list",
    ),
    path(
        "reviews/<int:pk>/",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
]
