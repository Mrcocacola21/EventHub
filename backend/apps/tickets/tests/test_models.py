from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.events.models import Event, EventCategory
from apps.tickets.models import TicketType

User = get_user_model()


class TicketTypeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = EventCategory.objects.create(name="Ticket Events")
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="StrongPass123!",
            role=User.Roles.ORGANIZER,
        )
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
            password="StrongPass123!",
        )
        cls.published_event = cls.make_event(
            title="Published Event",
            status=Event.Status.PUBLISHED,
        )
        cls.draft_event = cls.make_event(title="Draft Event")
        cls.canceled_event = cls.make_event(
            title="Canceled Event",
            status=Event.Status.CANCELED,
        )
        cls.finished_event = cls.make_event(
            title="Finished Event",
            status=Event.Status.FINISHED,
        )
        cls.past_event = cls.make_event(
            title="Past Event",
            days=-2,
            status=Event.Status.PUBLISHED,
        )

    @classmethod
    def make_event(cls, **overrides):
        days = overrides.pop("days", 2)
        start = timezone.now() + timedelta(days=days)
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

    def make_ticket_type(self, **overrides):
        data = {
            "event": self.published_event,
            "name": "Standard",
            "price": Decimal("10.00"),
            "quantity": 100,
        }
        data.update(overrides)
        return TicketType.objects.create(**data)

    def test_str_returns_event_title_and_name(self):
        ticket_type = self.make_ticket_type(name="VIP")

        self.assertEqual(str(ticket_type), "Published Event - VIP")

    def test_available_quantity_is_quantity_minus_sold_count(self):
        ticket_type = self.make_ticket_type(quantity=20, sold_count=7)

        self.assertEqual(ticket_type.available_quantity, 13)

    def test_is_sold_out_true_when_sold_count_reaches_quantity(self):
        ticket_type = self.make_ticket_type(quantity=10, sold_count=10)

        self.assertTrue(ticket_type.is_sold_out)

    def test_sales_period_active_without_dates(self):
        ticket_type = self.make_ticket_type()

        self.assertTrue(ticket_type.is_sales_period_active)

    def test_sales_period_active_inside_period(self):
        ticket_type = self.make_ticket_type(
            sales_start=timezone.now() - timedelta(hours=1),
            sales_end=timezone.now() + timedelta(hours=1),
        )

        self.assertTrue(ticket_type.is_sales_period_active)

    def test_sales_period_inactive_before_sales_start(self):
        ticket_type = self.make_ticket_type(
            sales_start=timezone.now() + timedelta(hours=1),
        )

        self.assertFalse(ticket_type.is_sales_period_active)

    def test_sales_period_inactive_after_sales_end(self):
        ticket_type = self.make_ticket_type(
            sales_end=timezone.now() - timedelta(hours=1),
        )

        self.assertFalse(ticket_type.is_sales_period_active)

    def test_is_available_for_purchase_for_active_published_future_event(self):
        ticket_type = self.make_ticket_type()

        self.assertTrue(ticket_type.is_available_for_purchase)

    def test_is_available_for_purchase_false_for_inactive_or_past_event(self):
        inactive = self.make_ticket_type(name="Inactive", is_active=False)
        past = self.make_ticket_type(name="Past", event=self.past_event)

        self.assertFalse(inactive.is_available_for_purchase)
        self.assertFalse(past.is_available_for_purchase)

    def test_is_available_for_purchase_false_for_draft_sold_out_or_closed_sales(self):
        draft = self.make_ticket_type(name="Draft", event=self.draft_event)
        sold_out = self.make_ticket_type(
            name="Sold Out",
            quantity=2,
            sold_count=2,
        )
        before_sales = self.make_ticket_type(
            name="Before Sales",
            sales_start=timezone.now() + timedelta(days=1),
        )
        after_sales = self.make_ticket_type(
            name="After Sales",
            sales_end=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(draft.is_available_for_purchase)
        self.assertFalse(sold_out.is_available_for_purchase)
        self.assertFalse(before_sales.is_available_for_purchase)
        self.assertFalse(after_sales.is_available_for_purchase)

    def test_can_sell_true_when_available(self):
        ticket_type = self.make_ticket_type(quantity=5, sold_count=2)

        self.assertTrue(ticket_type.can_sell(1))

    def test_can_sell_false_when_count_exceeds_available_quantity(self):
        ticket_type = self.make_ticket_type(quantity=5, sold_count=4)

        self.assertFalse(ticket_type.can_sell(2))

    def test_can_sell_false_when_sold_out(self):
        ticket_type = self.make_ticket_type(quantity=5, sold_count=5)

        self.assertFalse(ticket_type.can_sell(1))

    def test_can_sell_false_for_non_positive_count(self):
        ticket_type = self.make_ticket_type()

        self.assertFalse(ticket_type.can_sell(0))

    def test_clean_rejects_negative_price(self):
        ticket_type = TicketType(
            event=self.published_event,
            name="Invalid",
            price=Decimal("-1.00"),
            quantity=10,
        )

        with self.assertRaises(ValidationError) as context:
            ticket_type.clean()

        self.assertIn("price", context.exception.message_dict)

    def test_clean_rejects_zero_quantity(self):
        ticket_type = TicketType(
            event=self.published_event,
            name="Invalid",
            price=Decimal("1.00"),
            quantity=0,
        )

        with self.assertRaises(ValidationError) as context:
            ticket_type.clean()

        self.assertIn("quantity", context.exception.message_dict)

    def test_clean_rejects_sold_count_greater_than_quantity(self):
        ticket_type = TicketType(
            event=self.published_event,
            name="Invalid",
            price=Decimal("1.00"),
            quantity=2,
            sold_count=3,
        )

        with self.assertRaises(ValidationError) as context:
            ticket_type.clean()

        self.assertIn("sold_count", context.exception.message_dict)

    def test_clean_rejects_sales_end_before_or_equal_sales_start(self):
        now = timezone.now()
        ticket_type = TicketType(
            event=self.published_event,
            name="Invalid",
            price=Decimal("1.00"),
            quantity=2,
            sales_start=now,
            sales_end=now,
        )

        with self.assertRaises(ValidationError) as context:
            ticket_type.clean()

        self.assertIn("sales_end", context.exception.message_dict)

    def test_clean_rejects_active_ticket_type_for_canceled_or_finished_event(self):
        canceled = TicketType(
            event=self.canceled_event,
            name="Canceled",
            price=Decimal("1.00"),
            quantity=2,
            is_active=True,
        )
        finished = TicketType(
            event=self.finished_event,
            name="Finished",
            price=Decimal("1.00"),
            quantity=2,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            canceled.clean()
        with self.assertRaises(ValidationError):
            finished.clean()
