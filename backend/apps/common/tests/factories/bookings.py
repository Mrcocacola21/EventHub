import factory

from apps.bookings.models import Booking

from .tickets import TicketTypeFactory
from .users import UserFactory


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Booking

    user = factory.SubFactory(UserFactory)
    ticket_type = factory.SubFactory(TicketTypeFactory)
    status = Booking.Status.PAID
    price_at_purchase = factory.LazyAttribute(lambda obj: obj.ticket_type.price)
    is_used = False
