from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType
from apps.tickets.serializers import TicketTypeSerializer

User = get_user_model()


class TicketTypeSerializerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Serializer Events")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.other_organizer = User.objects.create_user(
            email="other-organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Roles.ADMIN,
        )
        cls.event = cls.make_event(
            title="Own Event",
            organizer=cls.organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.other_event = cls.make_event(
            title="Other Event",
            organizer=cls.other_organizer,
            status=Event.Status.PUBLISHED,
        )
        cls.canceled_event = cls.make_event(
            title="Canceled Event",
            organizer=cls.organizer,
            status=Event.Status.CANCELED,
        )
        cls.finished_event = cls.make_event(
            title="Finished Event",
            organizer=cls.organizer,
            status=Event.Status.FINISHED,
        )

    @classmethod
    def make_event(cls, **overrides):
        start = timezone.now() + timedelta(days=2)
        data = {
            "title": "Event",
            "description": "Event description",
            "category": cls.category,
            "location": "Kyiv",
            "start_datetime": start,
            "end_datetime": start + timedelta(hours=2),
            "organizer": cls.organizer,
        }
        data.update(overrides)
        return Event.objects.create(**data)

    def payload(self, **overrides):
        data = {
            "name": "Standard",
            "description": "Base access",
            "price": "10.00",
            "quantity": 100,
        }
        data.update(overrides)
        return data

    def request_for(self, user):
        return SimpleNamespace(user=user)

    def serializer(self, user, event, data=None, instance=None, **kwargs):
        return TicketTypeSerializer(
            instance,
            data=data or self.payload(),
            context={"request": self.request_for(user), "event": event},
            **kwargs,
        )

    def test_event_is_read_only_and_comes_from_context(self):
        serializer = self.serializer(
            self.organizer,
            self.event,
            data=self.payload(event=self.other_event.id),
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket_type = serializer.save()

        self.assertEqual(ticket_type.event, self.event)

    def test_sold_count_is_read_only(self):
        serializer = self.serializer(
            self.organizer,
            self.event,
            data=self.payload(sold_count=5),
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        ticket_type = serializer.save()

        self.assertEqual(ticket_type.sold_count, 0)

    def test_computed_fields_are_read_only(self):
        serializer = TicketTypeSerializer()

        for field_name in (
            "available_quantity",
            "is_sold_out",
            "is_sales_period_active",
            "is_available_for_purchase",
        ):
            self.assertTrue(serializer.fields[field_name].read_only)

    def test_validation_rejects_negative_price(self):
        serializer = self.serializer(
            self.organizer,
            self.event,
            data=self.payload(price="-1.00"),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("price", serializer.errors)

    def test_validation_rejects_quantity_below_sold_count_on_update(self):
        ticket_type = TicketType.objects.create(
            event=self.event,
            name="Standard",
            price=Decimal("10.00"),
            quantity=10,
            sold_count=5,
        )
        serializer = self.serializer(
            self.organizer,
            self.event,
            data={"quantity": 4},
            instance=ticket_type,
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("sold_count", serializer.errors)

    def test_validation_rejects_sales_end_before_or_equal_sales_start(self):
        now = timezone.now()
        serializer = self.serializer(
            self.organizer,
            self.event,
            data=self.payload(sales_start=now, sales_end=now),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("sales_end", serializer.errors)

    def test_organizer_cannot_create_for_another_organizers_event(self):
        serializer = self.serializer(self.organizer, self.other_event)

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_admin_can_create_for_any_event(self):
        serializer = self.serializer(self.admin, self.other_event)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_create_ticket_type_for_canceled_event(self):
        serializer = self.serializer(self.organizer, self.canceled_event)

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_cannot_create_ticket_type_for_finished_event(self):
        serializer = self.serializer(self.organizer, self.finished_event)

        self.assertFalse(serializer.is_valid())
        self.assertIn("event", serializer.errors)

    def test_sold_count_cannot_be_changed_through_update(self):
        ticket_type = TicketType.objects.create(
            event=self.event,
            name="VIP",
            price=Decimal("20.00"),
            quantity=10,
            sold_count=3,
        )
        serializer = self.serializer(
            self.organizer,
            self.event,
            data={"sold_count": 0},
            instance=ticket_type,
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        ticket_type.refresh_from_db()

        self.assertEqual(ticket_type.sold_count, 3)
