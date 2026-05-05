from django.contrib import admin, messages

from .models import Match, Participant, Tournament
from .services import TournamentService


class ParticipantInline(admin.TabularInline):
    model = Participant
    fields = ("user", "seed", "status", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    show_change_link = True


class MatchInline(admin.TabularInline):
    model = Match
    fields = (
        "round",
        "position",
        "player1",
        "player2",
        "winner",
        "status",
        "next_match",
        "next_match_slot",
    )
    readonly_fields = ("created_at", "updated_at")
    extra = 0
    show_change_link = True


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "event",
        "event_organizer",
        "type",
        "status",
        "participants_count_display",
        "matches_count_display",
        "registration_deadline",
        "created_at",
    )
    list_filter = ("type", "status", "created_at", "registration_deadline")
    search_fields = ("title", "event__title", "event__organizer__email")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "participants_count_display",
        "matches_count_display",
    )
    date_hierarchy = "created_at"
    list_select_related = ("event", "event__organizer")
    actions = ("open_registration", "start_tournaments", "cancel_tournaments")
    inlines = (ParticipantInline, MatchInline)

    @admin.display(ordering="event__organizer__email", description="Organizer")
    def event_organizer(self, obj):
        return obj.event.organizer

    @admin.display(description="Participants")
    def participants_count_display(self, obj):
        return obj.participants_count

    @admin.display(description="Matches")
    def matches_count_display(self, obj):
        return obj.matches_count

    @admin.action(description="Open registration for selected tournaments")
    def open_registration(self, request, queryset):
        updated_count = 0
        for tournament in queryset:
            tournament.open_registration()
            updated_count += 1
        self.message_user(
            request,
            f"{updated_count} tournament(s) opened for registration.",
            messages.SUCCESS,
            fail_silently=True,
        )
        return updated_count

    @admin.action(description="Cancel selected tournaments")
    def cancel_tournaments(self, request, queryset):
        updated_count = 0
        skipped_count = 0
        for tournament in queryset:
            try:
                TournamentService.cancel_tournament(
                    tournament,
                    canceled_by=request.user,
                )
                updated_count += 1
            except Exception:
                skipped_count += 1
        self.message_user(
            request,
            (
                f"{updated_count} tournament(s) canceled; "
                f"{skipped_count} skipped."
            ),
            messages.SUCCESS,
            fail_silently=True,
        )
        return updated_count

    @admin.action(description="Start selected tournaments")
    def start_tournaments(self, request, queryset):
        started_count = 0
        skipped_count = 0
        for tournament in queryset:
            try:
                TournamentService.start_tournament(
                    tournament,
                    started_by=request.user,
                )
                started_count += 1
            except Exception:
                skipped_count += 1
        self.message_user(
            request,
            (
                f"{started_count} tournament(s) started; "
                f"{skipped_count} skipped."
            ),
            messages.SUCCESS,
            fail_silently=True,
        )
        return started_count


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "tournament", "user", "seed", "status", "created_at")
    list_filter = ("status", "tournament__status", "created_at")
    search_fields = ("tournament__title", "user__email", "user__username")
    list_select_related = ("tournament", "user")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tournament",
        "round",
        "position",
        "player1",
        "player2",
        "winner",
        "status",
        "created_at",
    )
    list_filter = ("status", "round", "tournament")
    search_fields = (
        "tournament__title",
        "player1__user__email",
        "player2__user__email",
        "winner__user__email",
    )
    ordering = ("tournament", "round", "position")
    list_select_related = (
        "tournament",
        "player1",
        "player1__user",
        "player2",
        "player2__user",
        "winner",
        "winner__user",
    )
