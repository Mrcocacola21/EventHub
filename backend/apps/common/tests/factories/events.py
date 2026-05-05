from datetime import timedelta

import factory
from django.utils import timezone

from apps.events.models import Event, EventCategory

from .users import OrganizerFactory


class EventCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")
    description = "Factory event category"


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Event {n}")
    slug = factory.Sequence(lambda n: f"event-{n}")
    description = "Factory event description"
    category = factory.SubFactory(EventCategoryFactory)
    location = "Kyiv"
    start_datetime = factory.LazyFunction(lambda: timezone.now() + timedelta(days=14))
    end_datetime = factory.LazyAttribute(lambda obj: obj.start_datetime + timedelta(hours=2))
    organizer = factory.SubFactory(OrganizerFactory)
    max_participants = 100
    status = Event.Status.DRAFT


class PublishedEventFactory(EventFactory):
    status = Event.Status.PUBLISHED


class FinishedEventFactory(EventFactory):
    status = Event.Status.FINISHED
    start_datetime = factory.LazyFunction(lambda: timezone.now() - timedelta(days=3))
    end_datetime = factory.LazyAttribute(lambda obj: obj.start_datetime + timedelta(hours=2))
