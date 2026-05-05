from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.events.models import Event
from apps.tournaments.models import Tournament

from .utils import TournamentTestMixin


class TournamentApiTests(TournamentTestMixin, APITestCase):
    def results(self, response):
        return response.data.get("results", response.data)

    def ids(self, response):
        return [item["id"] for item in self.results(response)]

    def test_anonymous_sees_only_public_tournaments(self):
        public = self.make_tournament(title="Public")
        draft_event = self.make_event(title="Draft Event", status=Event.Status.DRAFT)
        private = Tournament.objects.create(event=draft_event, title="Private")

        response = self.client.get(reverse("tournament-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(public.id, self.ids(response))
        self.assertNotIn(private.id, self.ids(response))

    def test_organizer_sees_public_and_own_private_tournaments(self):
        public = self.make_tournament(title="Public")
        own_draft_event = self.make_event(
            title="Own Draft",
            status=Event.Status.DRAFT,
            organizer=self.organizer,
        )
        own_private = Tournament.objects.create(
            event=own_draft_event,
            title="Own Private",
        )
        other_draft_event = self.make_event(
            title="Other Draft",
            status=Event.Status.DRAFT,
            organizer=self.other_organizer,
        )
        other_private = Tournament.objects.create(
            event=other_draft_event,
            title="Other Private",
        )
        self.client.force_authenticate(self.organizer)

        response = self.client.get(reverse("tournament-list"))

        ids = self.ids(response)
        self.assertIn(public.id, ids)
        self.assertIn(own_private.id, ids)
        self.assertNotIn(other_private.id, ids)

    def test_admin_sees_all_tournaments(self):
        public = self.make_tournament(title="Public")
        draft_event = self.make_event(status=Event.Status.DRAFT)
        private = Tournament.objects.create(event=draft_event, title="Private")
        self.client.force_authenticate(self.admin_user)

        response = self.client.get(reverse("tournament-list"))

        self.assertIn(public.id, self.ids(response))
        self.assertIn(private.id, self.ids(response))

    def test_create_permissions(self):
        event = self.make_event(organizer=self.organizer)

        anonymous_response = self.client.post(
            reverse("tournament-list"),
            {"event": event.id, "title": "Anonymous"},
            format="json",
        )
        self.client.force_authenticate(self.user)
        user_response = self.client.post(
            reverse("tournament-list"),
            {"event": event.id, "title": "User"},
            format="json",
        )

        self.assertIn(
            anonymous_response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        self.assertEqual(user_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organizer_can_create_for_own_event_and_audit_is_logged(self):
        event = self.make_event(organizer=self.organizer)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("tournament-list"),
            {"event": event.id, "title": "Organizer Cup"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Tournament.Status.DRAFT)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_CREATED,
                entity_type="Tournament",
                entity_id=str(response.data["id"]),
            ).exists()
        )

    def test_organizer_cannot_create_for_another_event(self):
        event = self.make_event(organizer=self.other_organizer)
        self.client.force_authenticate(self.organizer)

        response = self.client.post(
            reverse("tournament-list"),
            {"event": event.id, "title": "Blocked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_create_for_any_event(self):
        event = self.make_event(organizer=self.other_organizer)
        self.client.force_authenticate(self.admin_user)

        response = self.client.post(
            reverse("tournament-list"),
            {"event": event.id, "title": "Admin Cup"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_create_for_invalid_event_or_duplicate_event(self):
        draft = self.make_event(status=Event.Status.DRAFT)
        canceled = self.make_event(title="Canceled", status=Event.Status.CANCELED)
        finished = self.make_event(title="Finished", status=Event.Status.FINISHED)
        existing_event = self.make_event(title="Existing")
        self.make_tournament(event=existing_event)
        self.client.force_authenticate(self.admin_user)

        for event in (draft, canceled, finished, existing_event):
            response = self.client.post(
                reverse("tournament-list"),
                {"event": event.id, "title": f"Tournament {event.id}"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_permissions_and_read_only_status_event(self):
        tournament = self.make_tournament()
        original_event_id = tournament.event_id
        other_event = self.make_event(title="Other")
        self.client.force_authenticate(self.organizer)

        response = self.client.patch(
            reverse("tournament-detail", args=[tournament.id]),
            {
                "title": "Updated",
                "status": Tournament.Status.CANCELED,
                "event": other_event.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        tournament.refresh_from_db()
        self.assertEqual(tournament.status, Tournament.Status.DRAFT)
        self.assertEqual(tournament.event_id, original_event_id)

        response = self.client.patch(
            reverse("tournament-detail", args=[tournament.id]),
            {"title": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tournament.refresh_from_db()
        self.assertEqual(tournament.title, "Updated")

    def test_other_organizer_cannot_update(self):
        tournament = self.make_tournament()
        self.client.force_authenticate(self.other_organizer)

        response = self.client.patch(
            reverse("tournament-detail", args=[tournament.id]),
            {"title": "Blocked"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any(self):
        tournament = self.make_tournament()
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            reverse("tournament-detail", args=[tournament.id]),
            {"title": "Admin Updated"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_allowed_only_for_draft_or_canceled(self):
        draft = self.make_tournament(title="Draft")
        in_progress = self.make_tournament(
            title="In Progress",
            status=Tournament.Status.IN_PROGRESS,
        )
        self.client.force_authenticate(self.organizer)

        blocked = self.client.delete(reverse("tournament-detail", args=[in_progress.id]))
        deleted = self.client.delete(reverse("tournament-detail", args=[draft.id]))

        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_open_registration_and_cancel_actions(self):
        tournament = self.make_tournament()
        self.client.force_authenticate(self.organizer)

        open_response = self.client.post(
            reverse("tournament-open-registration", args=[tournament.id])
        )
        cancel_response = self.client.post(
            reverse("tournament-cancel", args=[tournament.id])
        )

        self.assertEqual(open_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            open_response.data["status"],
            Tournament.Status.REGISTRATION_OPEN,
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data["status"], Tournament.Status.CANCELED)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_REGISTRATION_OPENED,
                entity_id=str(tournament.id),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.TOURNAMENT_CANCELED,
                entity_id=str(tournament.id),
            ).exists()
        )

    def test_regular_user_and_other_organizer_cannot_open_or_cancel(self):
        tournament = self.make_tournament()

        self.client.force_authenticate(self.user)
        user_response = self.client.post(
            reverse("tournament-open-registration", args=[tournament.id])
        )

        self.client.force_authenticate(self.other_organizer)
        organizer_response = self.client.post(
            reverse("tournament-cancel", args=[tournament.id])
        )

        self.assertEqual(user_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(organizer_response.status_code, status.HTTP_403_FORBIDDEN)
