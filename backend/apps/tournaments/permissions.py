from rest_framework.permissions import BasePermission

from apps.events.models import Event


def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.is_admin_role)
    )


def is_tournament_organizer(user, tournament):
    return bool(
        user
        and user.is_authenticated
        and user.is_organizer
        and tournament.event.organizer_id == user.id
    )


class IsTournamentOrganizerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        tournament = getattr(obj, "tournament", obj)
        return is_admin_user(request.user) or is_tournament_organizer(
            request.user,
            tournament,
        )


class CanManageTournament(IsTournamentOrganizerOrAdmin):
    pass


class CanViewTournament(BasePermission):
    def has_object_permission(self, request, view, obj):
        tournament = getattr(obj, "tournament", obj)
        if (
            tournament.event.is_published
            and tournament.event.status == Event.Status.PUBLISHED
        ):
            return True
        return is_admin_user(request.user) or is_tournament_organizer(
            request.user,
            tournament,
        )


class CanJoinTournament(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and obj.is_registration_open
            and not obj.participants.filter(user=user).exists()
            and (
                obj.max_participants is None
                or obj.participants.count() < obj.max_participants
            )
        )


class CanStartTournament(CanManageTournament):
    pass


class CanSubmitMatchResult(CanManageTournament):
    pass


class CanViewBracket(CanViewTournament):
    pass


class CanRegisterParticipant(CanJoinTournament):
    pass
