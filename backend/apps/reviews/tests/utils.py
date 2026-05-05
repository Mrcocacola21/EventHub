from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import Booking
from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class ReviewTestMixin:
    @classmethod
    def setUpTestData(cls):
        cls.category, _ = EventCategory.objects.get_or_create(
            name="Reviewed Events",
        )
        cls.user = cls._get_or_create_user("review-user@example.com")
        cls.second_user = cls._get_or_create_user("second-review-user@example.com")
        cls.organizer = cls._get_or_create_user(
            "review-organizer@example.com",
            role=User.Roles.ORGANIZER,
        )
        cls.other_organizer = cls._get_or_create_user(
            "other-review-organizer@example.com",
            role=User.Roles.ORGANIZER,
        )
        cls.admin_user = cls._get_or_create_user(
            "review-admin@example.com",
            role=User.Roles.ADMIN,
        )

    @classmethod
    def _get_or_create_user(cls, email, role=User.Roles.USER):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@", 1)[0],
                "role": role,
            },
        )
        if created:
            user.set_password("StrongPass123!")
            user.save(update_fields=["password"])
        elif user.role != role:
            user.role = role
            user.save(update_fields=["role", "updated_at"])
        return user

    def make_event(self, **overrides):
        end = timezone.now() - timedelta(hours=1)
        data = {
            "title": "Reviewed Event",
            "description": "Reviewed event",
            "category": self.category,
            "location": "Kyiv",
            "start_datetime": end - timedelta(hours=2),
            "end_datetime": end,
            "organizer": self.organizer,
            "status": Event.Status.FINISHED,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def make_future_event(self, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "status": Event.Status.PUBLISHED,
        }
        data.update(overrides)
        return self.make_event(**data)

    def make_ticket_type(self, event, **overrides):
        data = {
            "event": event,
            "name": (
                f"Standard {event.id}-"
                f"{TicketType.objects.filter(event=event).count() + 1}"
            ),
            "price": Decimal("10.00"),
            "quantity": 100,
            "is_active": False,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def make_booking(self, event, user=None, **overrides):
        ticket_type = overrides.pop("ticket_type", None) or self.make_ticket_type(event)
        data = {
            "user": user or self.user,
            "ticket_type": ticket_type,
            "status": Booking.Status.PAID,
            "price_at_purchase": ticket_type.price,
        }
        data.update(overrides)
        return Booking.objects.create(**data)
