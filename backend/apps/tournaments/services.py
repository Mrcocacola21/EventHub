from math import ceil, log2

from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.cache import EventCacheService
from apps.events.models import Event

from .models import Match, Participant, Tournament


class TournamentService:
    @classmethod
    def register_participant(
        cls,
        tournament,
        user,
        added_by=None,
        request=None,
    ):
        if not user or not user.is_authenticated:
            raise ValidationError("Authentication is required to register.")

        tournament_id = cls._tournament_id(tournament)
        with transaction.atomic():
            locked_tournament = cls._get_locked_tournament(tournament_id)
            cls._validate_registration_open(locked_tournament)

            if locked_tournament.participants.filter(user=user).exists():
                raise ValidationError("User is already registered for this tournament.")

            current_count = locked_tournament.participants.count()
            if (
                locked_tournament.max_participants is not None
                and current_count >= locked_tournament.max_participants
            ):
                raise ValidationError("Tournament has reached max participants.")

            next_seed = (
                locked_tournament.participants.aggregate(max_seed=Max("seed"))[
                    "max_seed"
                ]
                or current_count
            ) + 1
            participant = Participant.objects.create(
                tournament=locked_tournament,
                user=user,
                seed=next_seed,
                status=Participant.Status.REGISTERED,
            )

            AuditService.log_action(
                action=AuditLog.Action.TOURNAMENT_PARTICIPANT_REGISTERED,
                entity_type="Tournament",
                entity_id=locked_tournament.id,
                request=request,
                user=added_by or user,
                metadata={
                    "tournament_id": locked_tournament.id,
                    "event_id": locked_tournament.event_id,
                    "participant_id": participant.id,
                    "user_id": user.id,
                    "added_by_id": getattr(added_by, "id", None),
                },
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return participant

    @classmethod
    def start_tournament(cls, tournament, started_by=None, request=None):
        tournament_id = cls._tournament_id(tournament)
        with transaction.atomic():
            locked_tournament = cls._get_locked_tournament(tournament_id)
            cls._validate_can_start(locked_tournament)

            matches = cls.generate_bracket(locked_tournament)
            locked_tournament.participants.filter(
                status=Participant.Status.REGISTERED,
            ).update(status=Participant.Status.ACTIVE, updated_at=timezone.now())
            locked_tournament.status = Tournament.Status.IN_PROGRESS
            locked_tournament.save(update_fields=["status", "updated_at"])

            AuditService.log_action(
                action=AuditLog.Action.TOURNAMENT_STARTED,
                entity_type="Tournament",
                entity_id=locked_tournament.id,
                request=request,
                user=started_by,
                metadata={
                    "tournament_id": locked_tournament.id,
                    "event_id": locked_tournament.event_id,
                    "matches_count": len(matches),
                    "participants_count": locked_tournament.participants.count(),
                },
            )

            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_tournament_started(
                    locked_tournament,
                ),
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return locked_tournament

    @classmethod
    def generate_bracket(cls, tournament):
        with transaction.atomic():
            participants = list(
                tournament.participants.select_related("user").order_by(
                    F("seed").asc(nulls_last=True),
                    "created_at",
                    "id",
                )
            )
            participant_count = len(participants)
            if participant_count < 2:
                raise ValidationError("Tournament needs at least two participants.")

            if tournament.matches.exists():
                raise ValidationError("Tournament bracket already exists.")

            bracket_size = cls._next_power_of_two(participant_count)
            rounds_count = int(log2(bracket_size))
            matches_by_round = {}
            created_matches = []

            for round_number in range(1, rounds_count + 1):
                matches_count = bracket_size // (2**round_number)
                round_matches = []
                for position in range(1, matches_count + 1):
                    match = Match.objects.create(
                        tournament=tournament,
                        round=round_number,
                        position=position,
                    )
                    round_matches.append(match)
                    created_matches.append(match)
                matches_by_round[round_number] = round_matches

            for round_number in range(1, rounds_count):
                for match in matches_by_round[round_number]:
                    next_match = matches_by_round[round_number + 1][
                        (match.position - 1) // 2
                    ]
                    match.next_match = next_match
                    match.next_match_slot = (
                        Match.NextMatchSlot.PLAYER1
                        if match.position % 2 == 1
                        else Match.NextMatchSlot.PLAYER2
                    )
                    match.save(
                        update_fields=["next_match", "next_match_slot", "updated_at"]
                    )

            first_round_slots = cls._build_first_round_slots(
                participants,
                bracket_size,
            )
            now = timezone.now()
            for index, match in enumerate(matches_by_round[1]):
                player1 = first_round_slots[index * 2]
                player2 = first_round_slots[index * 2 + 1]
                match.player1 = player1
                match.player2 = player2
                update_fields = ["player1", "player2", "updated_at"]

                if (player1 is None) != (player2 is None):
                    match.winner = player1 or player2
                    match.status = Match.Status.FINISHED
                    match.finished_at = now
                    update_fields.extend(["winner", "status", "finished_at"])

                match.save(update_fields=update_fields)

                if match.status == Match.Status.FINISHED and match.winner_id:
                    cls._promote_winner(match, match.winner, finish_tournament=False)

            return created_matches

    @classmethod
    def submit_match_result(
        cls,
        match,
        winner,
        submitted_by=None,
        request=None,
    ):
        match_id = cls._match_id(match)
        winner_id = cls._participant_id(winner)

        with transaction.atomic():
            locked_match = (
                Match.objects.select_for_update(of=("self",))
                .select_related(
                    "tournament",
                    "tournament__event",
                    "tournament__event__organizer",
                    "player1",
                    "player1__user",
                    "player2",
                    "player2__user",
                    "winner",
                    "next_match",
                )
                .get(id=match_id)
            )
            tournament = Tournament.objects.select_for_update().get(
                id=locked_match.tournament_id,
            )
            locked_match.tournament = tournament

            cls._validate_match_result(locked_match, winner_id)
            winner = Participant.objects.select_for_update().get(id=winner_id)
            loser = (
                locked_match.player2
                if locked_match.player1_id == winner_id
                else locked_match.player1
            )

            now = timezone.now()
            locked_match.winner = winner
            locked_match.status = Match.Status.FINISHED
            locked_match.finished_at = now
            if locked_match.started_at is None:
                locked_match.started_at = now
            locked_match.save(
                update_fields=[
                    "winner",
                    "status",
                    "started_at",
                    "finished_at",
                    "updated_at",
                ],
            )

            loser.status = Participant.Status.ELIMINATED
            loser.save(update_fields=["status", "updated_at"])

            tournament_finished = cls._promote_winner(locked_match, winner)

            AuditService.log_action(
                action=AuditLog.Action.MATCH_RESULT_SUBMITTED,
                entity_type="Match",
                entity_id=locked_match.id,
                request=request,
                user=submitted_by,
                metadata={
                    "tournament_id": tournament.id,
                    "event_id": tournament.event_id,
                    "match_id": locked_match.id,
                    "winner_id": winner.id,
                    "loser_id": loser.id,
                },
            )

            if tournament_finished:
                AuditService.log_action(
                    action=AuditLog.Action.TOURNAMENT_FINISHED,
                    entity_type="Tournament",
                    entity_id=tournament.id,
                    request=request,
                    user=submitted_by,
                    metadata={
                        "tournament_id": tournament.id,
                        "event_id": tournament.event_id,
                        "match_id": locked_match.id,
                        "winner_id": winner.id,
                    },
                )

            from apps.notifications.services import NotificationService

            transaction.on_commit(
                lambda: NotificationService.notify_match_result_updated(
                    locked_match,
                ),
            )
            if tournament_finished:
                transaction.on_commit(
                    lambda: NotificationService.notify_tournament_finished(
                        tournament,
                        winner,
                    ),
                )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        locked_match.refresh_from_db()
        return locked_match

    @classmethod
    def cancel_tournament(cls, tournament, canceled_by=None, request=None):
        tournament_id = cls._tournament_id(tournament)
        with transaction.atomic():
            locked_tournament = cls._get_locked_tournament(tournament_id)
            if locked_tournament.status == Tournament.Status.FINISHED:
                raise ValidationError("Finished tournament cannot be canceled.")

            locked_tournament.status = Tournament.Status.CANCELED
            locked_tournament.save(update_fields=["status", "updated_at"])
            locked_tournament.matches.exclude(status=Match.Status.FINISHED).update(
                status=Match.Status.CANCELED,
                updated_at=timezone.now(),
            )

            AuditService.log_action(
                action=AuditLog.Action.TOURNAMENT_CANCELED,
                entity_type="Tournament",
                entity_id=locked_tournament.id,
                request=request,
                user=canceled_by,
                metadata={
                    "tournament_id": locked_tournament.id,
                    "event_id": locked_tournament.event_id,
                    "status": locked_tournament.status,
                },
            )
            transaction.on_commit(EventCacheService.invalidate_events_cache)

        return locked_tournament

    @classmethod
    def _promote_winner(cls, match, winner, finish_tournament=True):
        if match.next_match_id:
            next_match = Match.objects.select_for_update().get(id=match.next_match_id)
            target_field = (
                "player1"
                if match.next_match_slot == Match.NextMatchSlot.PLAYER1
                else "player2"
            )
            existing_participant_id = getattr(next_match, f"{target_field}_id")
            if existing_participant_id and existing_participant_id != winner.id:
                raise ValidationError("Next match slot is already occupied.")

            setattr(next_match, target_field, winner)
            next_match.save(update_fields=[target_field, "updated_at"])
            return False

        if not finish_tournament:
            return False

        tournament = Tournament.objects.select_for_update().get(id=match.tournament_id)
        tournament.status = Tournament.Status.FINISHED
        tournament.save(update_fields=["status", "updated_at"])

        winner.status = Participant.Status.WINNER
        winner.save(update_fields=["status", "updated_at"])

        tournament.participants.exclude(id=winner.id).filter(
            status=Participant.Status.ACTIVE,
        ).update(status=Participant.Status.ELIMINATED, updated_at=timezone.now())
        return True

    @staticmethod
    def _build_first_round_slots(participants, bracket_size):
        byes_count = bracket_size - len(participants)
        slots = []
        for index, participant in enumerate(participants):
            slots.append(participant)
            if index < byes_count:
                slots.append(None)
        return slots

    @staticmethod
    def _next_power_of_two(value):
        return 2 ** ceil(log2(value))

    @staticmethod
    def _tournament_id(tournament):
        return getattr(tournament, "id", tournament)

    @staticmethod
    def _match_id(match):
        return getattr(match, "id", match)

    @staticmethod
    def _participant_id(participant):
        return getattr(participant, "id", participant)

    @staticmethod
    def _get_locked_tournament(tournament_id):
        return (
            Tournament.objects.select_for_update()
            .select_related("event", "event__organizer", "event__category")
            .get(id=tournament_id)
        )

    @staticmethod
    def _validate_registration_open(tournament):
        if tournament.status != Tournament.Status.REGISTRATION_OPEN:
            raise ValidationError("Tournament registration is not open.")

        if (
            tournament.registration_deadline
            and tournament.registration_deadline < timezone.now()
        ):
            raise ValidationError("Registration deadline has passed.")

        if not (
            tournament.event.status == Event.Status.PUBLISHED
            and tournament.event.is_published
        ):
            raise ValidationError("Tournament event must be published.")

    @staticmethod
    def _validate_can_start(tournament):
        if tournament.status != Tournament.Status.REGISTRATION_OPEN:
            raise ValidationError("Only tournaments with open registration can start.")

        if tournament.type != Tournament.Type.SINGLE_ELIMINATION:
            raise ValidationError("Only single-elimination tournaments are supported.")

        if tournament.participants.count() < 2:
            raise ValidationError("Tournament needs at least two participants.")

        if tournament.matches.exists():
            raise ValidationError("Tournament bracket already exists.")

    @staticmethod
    def _validate_match_result(match, winner_id):
        if match.tournament.status != Tournament.Status.IN_PROGRESS:
            raise ValidationError("Tournament is not in progress.")

        if match.status == Match.Status.FINISHED:
            raise ValidationError("Finished match result cannot be changed.")

        if match.status == Match.Status.CANCELED:
            raise ValidationError("Canceled match cannot be updated.")

        if not match.player1_id or not match.player2_id:
            raise ValidationError("Match result requires both players.")

        if winner_id not in (match.player1_id, match.player2_id):
            raise ValidationError("Winner must be one of match players.")
