from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.audit.services import AuditService
from apps.events.cache import EventCacheService
from apps.events.models import Event

from .models import Match, Tournament
from .permissions import CanManageTournament, CanSubmitMatchResult
from .serializers import (
    MatchResultSerializer,
    MatchSerializer,
    ParticipantSerializer,
    TournamentSerializer,
)
from .services import TournamentService


@extend_schema_view(
    list=extend_schema(tags=["Tournaments"], summary="List tournaments"),
    create=extend_schema(
        tags=["Tournaments"],
        summary="Create tournament",
        examples=[
            OpenApiExample(
                "Create tournament",
                value={
                    "event": 1,
                    "title": "Django Cup",
                    "type": "SINGLE_ELIMINATION",
                    "max_participants": 16,
                    "registration_deadline": "2026-11-25T23:59:59Z",
                },
                request_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(tags=["Tournaments"], summary="Get tournament"),
    partial_update=extend_schema(tags=["Tournaments"], summary="Update tournament"),
    destroy=extend_schema(tags=["Tournaments"], summary="Delete tournament"),
)
class TournamentViewSet(viewsets.ModelViewSet):
    serializer_class = TournamentSerializer
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        queryset = Tournament.objects.select_related(
            "event",
            "event__organizer",
            "event__category",
        )
        user = self.request.user
        public_filter = Q(
            event__status=Event.Status.PUBLISHED,
            event__is_published=True,
        )

        if user and user.is_authenticated:
            if user.is_superuser or user.is_admin_role:
                return queryset

            if user.is_organizer:
                return queryset.filter(public_filter | Q(event__organizer=user))

        return queryset.filter(public_filter)

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
            "participants",
            "matches",
            "bracket",
        ):
            return [AllowAny()]
        if self.action in ("create", "register"):
            return [IsAuthenticated()]
        return [CanManageTournament()]

    def perform_create(self, serializer):
        tournament = serializer.save()
        self._log_tournament_action(
            AuditLog.Action.TOURNAMENT_CREATED,
            tournament,
        )
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def perform_update(self, serializer):
        serializer.save()
        transaction.on_commit(EventCacheService.invalidate_events_cache)

    def destroy(self, request, *args, **kwargs):
        tournament = self.get_object()
        if tournament.status not in (
            Tournament.Status.DRAFT,
            Tournament.Status.CANCELED,
        ):
            return Response(
                {"detail": "Only draft or canceled tournaments can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = super().destroy(request, *args, **kwargs)
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        return response

    @extend_schema(
        tags=["Tournaments"],
        summary="Open tournament registration",
        request=None,
        responses=TournamentSerializer,
    )
    @action(detail=True, methods=["post"], url_path="open-registration")
    def open_registration(self, request, *args, **kwargs):
        tournament = self.get_object()
        tournament.open_registration()
        self._log_tournament_action(
            AuditLog.Action.TOURNAMENT_REGISTRATION_OPENED,
            tournament,
        )
        transaction.on_commit(EventCacheService.invalidate_events_cache)
        serializer = self.get_serializer(tournament)
        return Response(serializer.data)

    @extend_schema(
        tags=["Tournaments"],
        summary="Cancel tournament",
        request=None,
        responses=TournamentSerializer,
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        tournament = self.get_object()
        tournament = TournamentService.cancel_tournament(
            tournament,
            canceled_by=request.user,
            request=request,
        )
        serializer = self.get_serializer(tournament)
        return Response(serializer.data)

    @extend_schema(
        tags=["Tournaments"],
        summary="Register current user as tournament participant",
        request=None,
        responses=ParticipantSerializer,
    )
    @action(detail=True, methods=["post"])
    def register(self, request, *args, **kwargs):
        tournament = self.get_object()
        participant = TournamentService.register_participant(
            tournament,
            request.user,
            added_by=request.user,
            request=request,
        )
        serializer = ParticipantSerializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Tournaments"],
        summary="Start tournament and generate bracket",
        description=(
            "Supports SINGLE_ELIMINATION only. Bracket generation happens on start."
        ),
        request=None,
        responses=TournamentSerializer,
    )
    @action(detail=True, methods=["post"])
    def start(self, request, *args, **kwargs):
        tournament = TournamentService.start_tournament(
            self.get_object(),
            started_by=request.user,
            request=request,
        )
        serializer = self.get_serializer(tournament)
        return Response(serializer.data)

    @extend_schema(
        tags=["Tournaments"],
        summary="Get tournament bracket",
        description="Returns matches grouped by round and sorted by position.",
    )
    @action(detail=True, methods=["get"])
    def bracket(self, request, *args, **kwargs):
        tournament = self.get_object()
        matches = (
            tournament.matches.select_related(
                "tournament",
                "player1",
                "player1__user",
                "player2",
                "player2__user",
                "winner",
                "winner__user",
                "next_match",
            )
            .order_by("round", "position")
        )
        rounds = []
        current_round = None
        current_matches = []
        for match in matches:
            if current_round is None:
                current_round = match.round
            if match.round != current_round:
                rounds.append(
                    {
                        "round": current_round,
                        "matches": MatchSerializer(current_matches, many=True).data,
                    }
                )
                current_round = match.round
                current_matches = []
            current_matches.append(match)

        if current_round is not None:
            rounds.append(
                {
                    "round": current_round,
                    "matches": MatchSerializer(current_matches, many=True).data,
                }
            )

        return Response(
            {
                "tournament": TournamentSerializer(
                    tournament,
                    context={"request": request},
                ).data,
                "rounds": rounds,
            }
        )

    @extend_schema(
        tags=["Tournaments"],
        summary="List or add tournament participants",
        responses=ParticipantSerializer(many=True),
    )
    @action(detail=True, methods=["get", "post"])
    def participants(self, request, *args, **kwargs):
        tournament = self.get_object()
        if request.method == "GET":
            participants = tournament.participants.select_related("user")
            page = self.paginate_queryset(participants)
            if page is not None:
                serializer = ParticipantSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = ParticipantSerializer(participants, many=True)
            return Response(serializer.data)

        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication is required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        is_manager = self._can_manage_tournament(request.user, tournament)
        if not is_manager and not tournament.is_registration_open:
            return Response(
                {"detail": "Tournament registration is not open."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        if not is_manager:
            data.pop("user", None)

        serializer = ParticipantSerializer(
            data=data,
            context={"request": request, "tournament": tournament},
        )
        serializer.is_valid(raise_exception=True)
        if is_manager:
            participant = serializer.save()
            transaction.on_commit(EventCacheService.invalidate_events_cache)
        else:
            participant = TournamentService.register_participant(
                tournament,
                request.user,
                added_by=request.user,
                request=request,
            )
        output_serializer = ParticipantSerializer(participant)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Tournaments"],
        summary="List tournament matches",
        responses=MatchSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def matches(self, request, *args, **kwargs):
        tournament = self.get_object()
        matches = tournament.matches.select_related(
            "tournament",
            "player1",
            "player1__user",
            "player2",
            "player2__user",
            "winner",
            "winner__user",
            "next_match",
        )
        page = self.paginate_queryset(matches)
        if page is not None:
            serializer = MatchSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MatchSerializer(matches, many=True)
        return Response(serializer.data)

    def _log_tournament_action(self, action, tournament):
        AuditService.log_action(
            action=action,
            entity_type="Tournament",
            entity_id=tournament.id,
            request=self.request,
            metadata={
                "title": tournament.title,
                "status": tournament.status,
                "event_id": tournament.event_id,
                "organizer_id": tournament.event.organizer_id,
            },
        )

    @staticmethod
    def _can_manage_tournament(user, tournament):
        if user.is_superuser or user.is_admin_role:
            return True
        return user.is_organizer and tournament.event.organizer_id == user.id


@extend_schema_view(
    retrieve=extend_schema(tags=["Tournaments"], summary="Get match"),
)
class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = Match.objects.select_related(
            "tournament",
            "tournament__event",
            "tournament__event__organizer",
            "player1",
            "player1__user",
            "player2",
            "player2__user",
            "winner",
            "winner__user",
            "next_match",
        )
        user = self.request.user
        public_filter = Q(
            tournament__event__status=Event.Status.PUBLISHED,
            tournament__event__is_published=True,
        )

        if user and user.is_authenticated:
            if user.is_superuser or user.is_admin_role:
                return queryset

            if user.is_organizer:
                return queryset.filter(
                    public_filter | Q(tournament__event__organizer=user)
                )

        return queryset.filter(public_filter)

    def get_permissions(self):
        if self.action in ("retrieve",):
            return [AllowAny()]
        if self.action == "result":
            return [CanSubmitMatchResult()]
        return super().get_permissions()

    @extend_schema(
        tags=["Tournaments"],
        summary="Submit match result",
        description=(
            "Finished match result cannot be changed. Final match result finishes "
            "the tournament."
        ),
        examples=[
            OpenApiExample(
                "Submit match result",
                value={"winner_id": 5},
                request_only=True,
            ),
        ],
        responses=MatchSerializer,
    )
    @action(detail=True, methods=["post"])
    def result(self, request, *args, **kwargs):
        match = self.get_object()
        self.check_object_permissions(request, match)
        serializer = MatchResultSerializer(
            data=request.data,
            context={"match": match},
        )
        serializer.is_valid(raise_exception=True)
        updated_match = TournamentService.submit_match_result(
            match,
            serializer.validated_data["winner"],
            submitted_by=request.user,
            request=request,
        )
        return Response(MatchSerializer(updated_match).data)
