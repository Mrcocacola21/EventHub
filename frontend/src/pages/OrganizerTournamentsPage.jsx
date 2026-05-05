import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  cancelTournament,
  getTournaments,
  openTournamentRegistration,
  startTournament,
} from "../api/tournaments.js";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import TournamentStatusBadge from "../components/tournaments/TournamentStatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { normalizePaginatedResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";
import { queryKeys } from "../utils/queryKeys.js";
import { getTournamentEventTitle } from "../utils/tournaments.js";

const params = { ordering: "-created_at" };

export default function OrganizerTournamentsPage() {
  const queryClient = useQueryClient();
  const { isAdmin, user } = useAuth();
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [busyTournamentId, setBusyTournamentId] = useState(null);

  const tournamentsQuery = useQuery({
    queryKey: queryKeys.organizerTournaments(params),
    queryFn: () => getTournaments(params),
  });

  const allTournaments = normalizePaginatedResponse(tournamentsQuery.data).items;
  const tournaments = useMemo(() => {
    if (isAdmin) {
      return allTournaments;
    }

    return allTournaments.filter((tournament) => {
      const organizerId = tournament.event_detail?.organizer?.id;
      return organizerId && String(organizerId) === String(user?.id);
    });
  }, [allTournaments, isAdmin, user?.id]);
  const summary = useMemo(
    () => ({
      total: tournaments.length,
      open: tournaments.filter(
        (tournament) => tournament.status === "REGISTRATION_OPEN",
      ).length,
      inProgress: tournaments.filter(
        (tournament) => tournament.status === "IN_PROGRESS",
      ).length,
    }),
    [tournaments],
  );

  const actionMutation = useMutation({
    mutationFn: ({ tournament, action }) => {
      if (action === "open") return openTournamentRegistration(tournament.id);
      if (action === "start") return startTournament(tournament.id);
      if (action === "cancel") return cancelTournament(tournament.id);
      throw new Error("Unsupported tournament action.");
    },
    onSuccess: async (tournament) => {
      setActionSuccess(`${tournament.title} updated to ${tournament.status}.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tournaments"] }),
        queryClient.invalidateQueries({ queryKey: ["organizerTournaments"] }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournament(tournament.id),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentBracket(tournament.id),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentMatches(tournament.id),
        }),
      ]);
    },
  });

  async function handleAction(tournament, action) {
    if (
      action === "cancel" &&
      !window.confirm(`Cancel tournament "${tournament.title}"?`)
    ) {
      return;
    }

    setActionError("");
    setActionSuccess("");
    setBusyTournamentId(tournament.id);

    try {
      await actionMutation.mutateAsync({ tournament, action });
    } catch (requestError) {
      setActionError(
        getApiErrorMessage(requestError, "Unable to update tournament."),
      );
    } finally {
      setBusyTournamentId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Organizer Tournaments
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Create tournaments, open registration, start brackets, and manage
            match results.
          </p>
        </div>
        <Button as={Link} to="/organizer/tournaments/new">
          Create tournament
        </Button>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Total", summary.total],
          ["Registration open", summary.open],
          ["In progress", summary.inProgress],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-950">
              {value}
            </p>
          </div>
        ))}
      </section>

      {actionSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {actionSuccess}
        </div>
      ) : null}
      <ErrorMessage message={actionError} />

      {tournamentsQuery.isLoading ? (
        <LoadingSpinner label="Loading organizer tournaments" />
      ) : null}
      {tournamentsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            tournamentsQuery.error,
            "Unable to load organizer tournaments.",
          )}
        />
      ) : null}

      {!tournamentsQuery.isLoading &&
      !tournamentsQuery.isError &&
      tournaments.length === 0 ? (
        <EmptyState
          title="No tournaments yet"
          description="Create a tournament from a published event."
          action={
            <Button as={Link} to="/organizer/tournaments/new">
              Create tournament
            </Button>
          }
        />
      ) : null}

      {tournaments.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-3">Tournament</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Participants</th>
                  <th className="px-4 py-3">Deadline</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tournaments.map((tournament) => (
                  <tr key={tournament.id} className="align-top">
                    <td className="px-4 py-4">
                      <p className="font-medium text-slate-950">
                        {tournament.title}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {getTournamentEventTitle(tournament)}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <TournamentStatusBadge status={tournament.status} />
                    </td>
                    <td className="px-4 py-4 text-slate-600">
                      {tournament.participants_count || 0} /{" "}
                      {tournament.max_participants || "Open"}
                    </td>
                    <td className="px-4 py-4 text-slate-600">
                      {formatDateTime(tournament.registration_deadline)}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          as={Link}
                          to={`/organizer/tournaments/${tournament.id}/manage`}
                          size="sm"
                        >
                          Manage
                        </Button>
                        {tournament.status === "DRAFT" ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleAction(tournament, "open")}
                            disabled={busyTournamentId === tournament.id}
                          >
                            Open registration
                          </Button>
                        ) : null}
                        {tournament.can_start ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleAction(tournament, "start")}
                            disabled={busyTournamentId === tournament.id}
                          >
                            Start
                          </Button>
                        ) : null}
                        {!["CANCELED", "FINISHED"].includes(tournament.status) ? (
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => handleAction(tournament, "cancel")}
                            disabled={busyTournamentId === tournament.id}
                          >
                            Cancel
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
