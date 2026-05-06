from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.pdf import PDFTicketService
from apps.bookings.qr import QRCodeService
from apps.events.models import Event, EventCategory
from apps.reviews.models import Review
from apps.tickets.models import TicketType
from apps.tournaments.models import Match, Participant, Tournament
from apps.tournaments.services import TournamentService


DEMO_PASSWORD = "EventHubDemo123!"


class Command(BaseCommand):
    help = "Seed idempotent local demo data for EventHub screenshots."

    def handle(self, *args, **options):
        now = timezone.now()
        User = get_user_model()

        organizer = self._upsert_user(
            User,
            email="demo.organizer@eventhub.local",
            username="demo_organizer",
            role=User.Roles.ORGANIZER,
            is_staff=True,
        )
        user = self._upsert_user(
            User,
            email="demo.user@eventhub.local",
            username="demo_user",
            role=User.Roles.USER,
        )
        participants = [
            user,
            self._upsert_user(
                User,
                email="demo.alex@eventhub.local",
                username="alex_player",
                role=User.Roles.USER,
            ),
            self._upsert_user(
                User,
                email="demo.sam@eventhub.local",
                username="sam_player",
                role=User.Roles.USER,
            ),
            self._upsert_user(
                User,
                email="demo.taylor@eventhub.local",
                username="taylor_player",
                role=User.Roles.USER,
            ),
        ]

        category, _ = EventCategory.objects.update_or_create(
            slug="technology",
            defaults={
                "name": "Technology",
                "description": "Conferences, workshops, and competitive tech events.",
            },
        )

        main_event = self._upsert_main_event(category, organizer, now)
        ticket_type = self._upsert_ticket_type(main_event, now)
        booking = self._upsert_booking(user, ticket_type)

        past_event = self._upsert_past_event(category, organizer, now)
        past_ticket_type = self._upsert_past_ticket_type(past_event, now)
        self._upsert_booking(user, past_ticket_type)
        review, _ = Review.objects.update_or_create(
            user=user,
            event=past_event,
            defaults={
                "rating": 5,
                "comment": "Clear agenda, smooth ticketing, and useful live updates.",
                "is_published": True,
            },
        )

        tournament = self._upsert_tournament(main_event, participants, organizer, now)

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write(f"Organizer: {organizer.email} / {DEMO_PASSWORD}")
        self.stdout.write(f"User: {user.email} / {DEMO_PASSWORD}")
        self.stdout.write(f"Event ID: {main_event.id}")
        self.stdout.write(f"Booking ID: {booking.id}")
        self.stdout.write(f"Tournament ID: {tournament.id}")
        self.stdout.write(f"Review ID: {review.id}")

    def _upsert_user(self, User, *, email, username, role, is_staff=False):
        user, _ = User.objects.get_or_create(email=email)
        user.username = username
        user.role = role
        user.is_active = True
        user.is_verified = True
        user.is_staff = is_staff
        user.set_password(DEMO_PASSWORD)
        user.save(
            update_fields=[
                "username",
                "role",
                "is_active",
                "is_verified",
                "is_staff",
                "password",
                "updated_at",
            ]
        )
        return user

    def _upsert_main_event(self, category, organizer, now):
        start = now + timedelta(days=45)
        end = start + timedelta(hours=8)
        event, _ = Event.objects.update_or_create(
            slug="eventhub-launch-conference",
            defaults={
                "title": "EventHub Launch Conference",
                "description": (
                    "A full-day demo conference covering event operations, ticket "
                    "booking, QR validation, notifications, and tournament workflows."
                ),
                "category": category,
                "location": "Kyiv Innovation Hall",
                "start_datetime": start,
                "end_datetime": end,
                "organizer": organizer,
                "max_participants": 200,
                "status": Event.Status.PUBLISHED,
            },
        )
        return event

    def _upsert_past_event(self, category, organizer, now):
        start = now - timedelta(days=21)
        end = start + timedelta(hours=4)
        event, _ = Event.objects.update_or_create(
            slug="eventhub-community-meetup",
            defaults={
                "title": "EventHub Community Meetup",
                "description": (
                    "A completed meetup used by the demo seed to show verified "
                    "attendee reviews and historical bookings."
                ),
                "category": category,
                "location": "Online",
                "start_datetime": start,
                "end_datetime": end,
                "organizer": organizer,
                "max_participants": 80,
                "status": Event.Status.FINISHED,
            },
        )
        return event

    def _upsert_ticket_type(self, event, now):
        ticket_type, _ = TicketType.objects.update_or_create(
            event=event,
            name="General Admission",
            defaults={
                "description": "Standard access with QR and PDF ticket delivery.",
                "price": Decimal("49.00"),
                "quantity": 150,
                "sales_start": now - timedelta(days=1),
                "sales_end": now + timedelta(days=30),
                "is_active": True,
            },
        )
        self._sync_sold_count(ticket_type)
        return ticket_type

    def _upsert_past_ticket_type(self, event, now):
        ticket_type, _ = TicketType.objects.update_or_create(
            event=event,
            name="Meetup Pass",
            defaults={
                "description": "Historical attendee ticket used for review demo data.",
                "price": Decimal("19.00"),
                "quantity": 80,
                "sales_start": now - timedelta(days=60),
                "sales_end": now - timedelta(days=22),
                "is_active": False,
            },
        )
        self._sync_sold_count(ticket_type)
        return ticket_type

    def _upsert_booking(self, user, ticket_type):
        booking, _ = Booking.objects.get_or_create(
            user=user,
            ticket_type=ticket_type,
            defaults={
                "status": Booking.Status.PAID,
                "price_at_purchase": ticket_type.price,
                "expires_at": None,
            },
        )
        if booking.status != Booking.Status.PAID:
            booking.status = Booking.Status.PAID
            booking.price_at_purchase = ticket_type.price
            booking.expires_at = None
            booking.save(
                update_fields=[
                    "status",
                    "price_at_purchase",
                    "expires_at",
                    "updated_at",
                ]
            )

        QRCodeService.generate_for_booking(booking)
        PDFTicketService.generate_for_booking(booking)
        self._sync_sold_count(ticket_type)
        return booking

    def _sync_sold_count(self, ticket_type):
        sold_count = Booking.objects.filter(
            ticket_type=ticket_type,
            status=Booking.Status.PAID,
        ).count()
        if ticket_type.sold_count != sold_count:
            ticket_type.sold_count = sold_count
            ticket_type.save(update_fields=["sold_count", "updated_at"])

    def _upsert_tournament(self, event, users, organizer, now):
        tournament, created = Tournament.objects.get_or_create(
            event=event,
            defaults={
                "title": "EventHub Demo Cup",
                "type": Tournament.Type.SINGLE_ELIMINATION,
                "status": Tournament.Status.REGISTRATION_OPEN,
                "max_participants": 8,
                "registration_deadline": now + timedelta(days=30),
            },
        )
        tournament.title = "EventHub Demo Cup"
        tournament.type = Tournament.Type.SINGLE_ELIMINATION
        tournament.max_participants = 8
        tournament.registration_deadline = now + timedelta(days=30)
        if created or not tournament.matches.exists():
            tournament.status = Tournament.Status.REGISTRATION_OPEN
        tournament.save()

        if not tournament.matches.exists():
            for seed, user in enumerate(users, start=1):
                participant, _ = Participant.objects.get_or_create(
                    tournament=tournament,
                    user=user,
                    defaults={
                        "seed": seed,
                        "status": Participant.Status.REGISTERED,
                    },
                )
                participant.seed = seed
                participant.status = Participant.Status.REGISTERED
                participant.save(update_fields=["seed", "status", "updated_at"])

            TournamentService.start_tournament(tournament, started_by=organizer)

        tournament.refresh_from_db()
        first_match = (
            Match.objects.filter(
                tournament=tournament,
                round=1,
                status=Match.Status.PENDING,
                player1__isnull=False,
                player2__isnull=False,
            )
            .select_related("player1")
            .order_by("position")
            .first()
        )
        if first_match:
            TournamentService.submit_match_result(
                first_match,
                first_match.player1,
                submitted_by=organizer,
            )

        tournament.refresh_from_db()
        return tournament
