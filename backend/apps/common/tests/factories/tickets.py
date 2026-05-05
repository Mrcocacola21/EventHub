from decimal import Decimal

import factory

from apps.tickets.models import TicketType

from .events import PublishedEventFactory


class TicketTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TicketType

    event = factory.SubFactory(PublishedEventFactory)
    name = factory.Sequence(lambda n: f"Standard {n}")
    description = "Factory ticket type"
    price = Decimal("25.00")
    quantity = 10
    sold_count = 0
    is_active = True
