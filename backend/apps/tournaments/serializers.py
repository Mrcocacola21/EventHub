from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.events.models import Event
from apps.users.serializers import UserShortSerializer

from .models import Match, Participant, Tournament

User = get_user_model()


class TournamentEventDetailSerializer(serializers.ModelSerializer):
    organizer = UserShortSerializer(read_only=True)

    class Meta:
        model = Event
        fields = ("id", "title", "slug", "start_datetime", "organizer")


class TournamentSerializer(serializers.ModelSerializer):
    event_detail = TournamentEventDetailSerializer(source="event", read_only=True)
    participants_count = serializers.IntegerField(read_only=True)
    matches_count = serializers.IntegerField(read_only=True)
    is_registration_open = serializers.BooleanField(read_only=True)
    can_start = serializers.BooleanField(read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "event",
            "event_detail",
            "title",
            "type",
            "status",
            "max_participants",
            "registration_deadline",
            "participants_count",
            "matches_count",
            "is_registration_open",
            "can_start",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "event_detail",
            "status",
            "participants_count",
            "matches_count",
            "is_registration_open",
            "can_start",
            "created_at",
            "updated_at",
        )

    def validate_event(self, event):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        if not (event.status == Event.Status.PUBLISHED and event.is_published):
            raise serializers.ValidationError("Event must be published.")

        if hasattr(event, "tournament"):
            raise serializers.ValidationError("Event already has a tournament.")

        if user.is_superuser or user.is_admin_role:
            return event

        if user.is_organizer and event.organizer_id == user.id:
            return event

        raise serializers.ValidationError("You cannot create tournament for this event.")

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance and "event" in self.initial_data:
            raw_event = self.initial_data.get("event")
            if str(raw_event) != str(self.instance.event_id):
                raise serializers.ValidationError(
                    {"event": "Event cannot be changed after create."}
                )

        event = attrs.get("event", getattr(self.instance, "event", None))
        tournament = self.instance or Tournament(event=event)
        for field_name, value in attrs.items():
            setattr(tournament, field_name, value)

        try:
            tournament.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("event", None)
        validated_data.pop("status", None)
        return super().update(instance, validated_data)


class ParticipantSerializer(serializers.ModelSerializer):
    tournament = serializers.PrimaryKeyRelatedField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
    )
    user_detail = UserShortSerializer(source="user", read_only=True)

    class Meta:
        model = Participant
        fields = (
            "id",
            "tournament",
            "user",
            "user_detail",
            "seed",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tournament",
            "user_detail",
            "status",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tournament = self.context.get("tournament") or getattr(
            self.instance,
            "tournament",
            None,
        )
        request = self.context.get("request")
        request_user = getattr(request, "user", None)
        user = attrs.get("user") or getattr(self.instance, "user", None)

        if not tournament:
            raise serializers.ValidationError({"tournament": "Tournament is required."})

        if user is None:
            if not request_user or not request_user.is_authenticated:
                raise serializers.ValidationError({"user": "Authentication is required."})
            user = request_user

        participant = self.instance or Participant(tournament=tournament, user=user)
        participant.seed = attrs.get("seed", getattr(participant, "seed", None))

        try:
            participant.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        tournament = self.context["tournament"]
        user = validated_data.pop("user", None) or request.user
        validated_data.pop("status", None)
        return Participant.objects.create(
            tournament=tournament,
            user=user,
            **validated_data,
        )


class ParticipantShortSerializer(serializers.ModelSerializer):
    user_detail = UserShortSerializer(source="user", read_only=True)

    class Meta:
        model = Participant
        fields = ("id", "user", "user_detail", "seed", "status")


class MatchSerializer(serializers.ModelSerializer):
    tournament = serializers.PrimaryKeyRelatedField(read_only=True)
    player1_detail = ParticipantShortSerializer(source="player1", read_only=True)
    player2_detail = ParticipantShortSerializer(source="player2", read_only=True)
    winner_detail = ParticipantShortSerializer(source="winner", read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "tournament",
            "round",
            "position",
            "player1",
            "player1_detail",
            "player2",
            "player2_detail",
            "winner",
            "winner_detail",
            "next_match",
            "next_match_slot",
            "status",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tournament",
            "player1_detail",
            "player2_detail",
            "winner_detail",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tournament = self.context.get("tournament") or getattr(
            self.instance,
            "tournament",
            None,
        )
        if not tournament:
            raise serializers.ValidationError({"tournament": "Tournament is required."})

        match = self.instance or Match(tournament=tournament)
        for field_name in (
            "round",
            "position",
            "player1",
            "player2",
            "winner",
            "next_match",
            "next_match_slot",
            "status",
            "started_at",
            "finished_at",
        ):
            if field_name in attrs:
                setattr(match, field_name, attrs[field_name])

        try:
            match.clean()
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise serializers.ValidationError(detail) from exc

        return attrs


class MatchResultSerializer(serializers.Serializer):
    winner_id = serializers.PrimaryKeyRelatedField(
        queryset=Participant.objects.select_related("tournament", "user"),
        source="winner",
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        match = self.context["match"]
        winner = attrs["winner"]

        if winner.tournament_id != match.tournament_id:
            raise serializers.ValidationError(
                {"winner_id": "Winner must belong to match tournament."}
            )

        if winner.id not in (match.player1_id, match.player2_id):
            raise serializers.ValidationError(
                {"winner_id": "Winner must be player1 or player2."}
            )

        return attrs
