from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.bookings.models import Booking
from apps.tickets.models import TicketType

from .cache import EventCacheService
from .models import Event, EventCategory


@receiver((post_save, post_delete), sender=Event)
@receiver((post_save, post_delete), sender=EventCategory)
@receiver((post_save, post_delete), sender=TicketType)
@receiver((post_save, post_delete), sender=Booking)
def invalidate_events_cache_on_public_data_change(sender, instance, **kwargs):
    EventCacheService.invalidate_events_cache()
