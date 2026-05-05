import factory

from apps.reviews.models import Review

from .events import FinishedEventFactory
from .users import UserFactory


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    user = factory.SubFactory(UserFactory)
    event = factory.SubFactory(FinishedEventFactory)
    rating = 5
    comment = "Great event!"
    is_published = True
