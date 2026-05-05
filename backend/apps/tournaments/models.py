from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.events.models import Event


class Tournament(models.Model):
    class Type(models.TextChoices):
        SINGLE_ELIMINATION = "SINGLE_ELIMINATION", "Single elimination"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REGISTRATION_OPEN = "REGISTRATION_OPEN", "Registration open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        FINISHED = "FINISHED", "Finished"
        CANCELED = "CANCELED", "Canceled"

    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="tournament",
    )
    title = models.CharField(max_length=255)
    type = models.CharField(
        max_length=32,
        choices=Type.choices,
        default=Type.SINGLE_ELIMINATION,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "tournament"
        verbose_name_plural = "tournaments"

    def __str__(self):
        return self.title

    @property
    def participants_count(self):
        return self.participants.count()

    @property
    def matches_count(self):
        return self.matches.count()

    @property
    def is_registration_open(self):
        deadline_ok = (
            self.registration_deadline is None
            or self.registration_deadline >= timezone.now()
        )
        return self.status == self.Status.REGISTRATION_OPEN and deadline_ok

    @property
    def can_start(self):
        return (
            self.status == self.Status.REGISTRATION_OPEN
            and self.participants_count >= 2
        )

    def clean(self):
        errors = {}
        event = getattr(self, "event", None)

        if event:
            if not (
                event.status == Event.Status.PUBLISHED
                and event.is_published
            ):
                errors["event"] = (
                    "Tournament event must be published and active."
                )

            organizer = event.organizer
            if not (
                organizer.is_superuser
                or organizer.is_organizer
                or organizer.is_admin_role
            ):
                errors["event"] = (
                    "Tournament event must be owned by an organizer or admin."
                )

            if (
                self.registration_deadline
                and event.start_datetime
                and self.registration_deadline >= event.start_datetime
            ):
                errors["registration_deadline"] = (
                    "Registration deadline must be before event start datetime."
                )

        if self.max_participants is not None and self.max_participants < 2:
            errors["max_participants"] = (
                "Max participants must be greater than or equal to 2."
            )

        if errors:
            raise ValidationError(errors)

    def open_registration(self):
        self.status = self.Status.REGISTRATION_OPEN
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELED
        self.save(update_fields=["status", "updated_at"])


class Participant(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "REGISTERED", "Registered"
        ACTIVE = "ACTIVE", "Active"
        ELIMINATED = "ELIMINATED", "Eliminated"
        WINNER = "WINNER", "Winner"

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tournament_participations",
    )
    seed = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.REGISTERED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["seed", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "user"],
                name="unique_participant_per_tournament",
            ),
        ]
        verbose_name = "participant"
        verbose_name_plural = "participants"

    def __str__(self):
        return f"{self.user.email} in {self.tournament.title}"

    def clean(self):
        errors = {}
        tournament = getattr(self, "tournament", None)

        if tournament:
            if tournament.status not in (
                Tournament.Status.DRAFT,
                Tournament.Status.REGISTRATION_OPEN,
            ):
                errors["tournament"] = (
                    "Participants can only be added before tournament starts."
                )

            if (
                tournament.registration_deadline
                and tournament.registration_deadline < timezone.now()
            ):
                errors["tournament"] = "Registration deadline has passed."

            if tournament.max_participants is not None:
                queryset = tournament.participants.all()
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)
                if queryset.count() >= tournament.max_participants:
                    errors["tournament"] = (
                        "Tournament has reached max participants."
                    )

        if self.user_id and self.tournament_id:
            queryset = Participant.objects.filter(
                tournament_id=self.tournament_id,
                user_id=self.user_id,
            )
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            if queryset.exists():
                errors["user"] = "User is already registered for this tournament."

        if errors:
            raise ValidationError(errors)


class Match(models.Model):
    class NextMatchSlot(models.TextChoices):
        PLAYER1 = "PLAYER1", "Player 1"
        PLAYER2 = "PLAYER2", "Player 2"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        FINISHED = "FINISHED", "Finished"
        CANCELED = "CANCELED", "Canceled"

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="matches",
    )
    round = models.PositiveIntegerField()
    position = models.PositiveIntegerField()
    player1 = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches_as_player1",
    )
    player2 = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches_as_player2",
    )
    winner = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches_won",
    )
    next_match = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_matches",
    )
    next_match_slot = models.CharField(
        max_length=16,
        choices=NextMatchSlot.choices,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["round", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "round", "position"],
                name="unique_match_position_per_tournament_round",
            ),
        ]
        verbose_name = "match"
        verbose_name_plural = "matches"

    def __str__(self):
        return f"{self.tournament.title} R{self.round} M{self.position}"

    @property
    def has_both_players(self):
        return self.player1_id is not None and self.player2_id is not None

    @property
    def is_finished(self):
        return self.status == self.Status.FINISHED

    def clean(self):
        errors = {}
        participant_fields = ("player1", "player2", "winner")

        for field_name in participant_fields:
            participant = getattr(self, field_name, None)
            if participant and participant.tournament_id != self.tournament_id:
                errors[field_name] = (
                    "Participant must belong to the same tournament."
                )

        if self.winner_id and self.winner_id not in (
            self.player1_id,
            self.player2_id,
        ):
            errors["winner"] = "Winner must be player1 or player2."

        if self.next_match and self.next_match.tournament_id != self.tournament_id:
            errors["next_match"] = "Next match must belong to the same tournament."

        if self.next_match_id and not self.next_match_slot:
            errors["next_match_slot"] = (
                "Next match slot is required when next match is set."
            )

        if not self.next_match_id and self.next_match_slot:
            errors["next_match_slot"] = (
                "Next match slot must be empty when next match is not set."
            )

        if errors:
            raise ValidationError(errors)
