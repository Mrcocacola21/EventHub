import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  cancelTournament,
  getTournament,
  getTournamentBracket,
  getTournamentParticipants,
  openTournamentRegistration,
  startTournament,
  submitMatchResult,
} from "../api/tournaments.js";
import Bracket from "../components/tournaments/Bracket.jsx";
import Button from "../components/common/Button.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import ParticipantList from "../components/tournaments/ParticipantList.jsx";
import TournamentStatusBadge from "../components/tournaments/TournamentStatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { getListFromResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";
import { queryKeys } from "../utils/queryKeys.js";
import { getTournamentEventTitle } from "../utils/tournaments.js";

export default function ManageTournamentPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const { isAdmin, user } = useAuth();
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [submittingMatchId, setSubmittingMatchId] = useState(null);

  const tournamentQuery = useQuery({
    queryKey: queryKeys.tournament(id),
    queryFn: () => getTournament(id),
    enabled: Boolean(id),
  });

  const participantsQuery = useQuery({
    queryKey: queryKeys.tournamentParticipants(id),
    queryFn: () => getTournamentParticipants(id),
    enabled: Boolean(id),
  });

  const bracketQuery = useQuery({
    queryKey: queryKeys.tournamentBracket(id),
    queryFn: () => getTournamentBracket(id),
    enabled: Boolean(id),
  });

  const participants = useMemo(
    () => getListFromResponse(participantsQuery.data),
    [participantsQuery.data],
  );

  const tournamentActionMutation = useMutation({
    mutationFn: (action) => {
      if (action === "open") return openTournamentRegistration(id);
      if (action === "start") return startTournament(id);
      if (action === "cancel") return cancelTournament(id);
      throw new Error("Unsupported tournament action.");
    },
    onSuccess: async (tournament) => {
      setActionSuccess(`Tournament updated to ${tournament.status}.`);
      await invalidateTournamentQueries(tournament.id);
    },
  });

  const resultMutation = useMutation({
    mutationFn: ({ match, winnerId }) => submitMatchResult(match.id, winnerId),
    onSuccess: async (match) => {
      setActionSuccess(`Match #${match.id} result submitted.`);
      await invalidateTournamentQueries(id);
      queryClient.invalidateQueries({ queryKey: queryKeys.match(match.id) });
    },
  });

  async function invalidateTournamentQueries(tournamentId) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["tournaments"] }),
      queryClient.invalidateQueries({ queryKey: ["organizerTournaments"] }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.tournament(tournamentId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.tournamentParticipants(tournamentId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.tournamentBracket(tournamentId),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.tournamentMatches(tournamentId),
      }),
    ]);
  }

  async function handleTournamentAction(action) {
    if (
      action === "cancel" &&
      !window.confirm("Cancel this tournament? This cannot be undone.")
    ) {
      return;
    }

    setActionError("");
    setActionSuccess("");

    try {
      await tournamentActionMutation.mutateAsync(action);
    } catch (requestError) {
      setActionError(
        getApiErrorMessage(requestError, "Unable to update tournament."),
      );
    }
  }

  async function handleSubmitResult(match, winnerId) {
    setActionError("");
    setActionSuccess("");
    setSubmittingMatchId(match.id);

    try {
      await resultMutation.mutateAsync({ match, winnerId });
    } catch (requestError) {
      setActionError(
        getApiErrorMessage(requestError, "Unable to submit match result."),
      );
      throw requestError;
    } finally {
      setSubmittingMatchId(null);
    }
  }

  if (tournamentQuery.isLoading) {
    return <LoadingSpinner label="Loading tournament" />;
  }

  if (tournamentQuery.isError) {
    return (
      <ErrorMessage
        message={getApiErrorMessage(
          tournamentQuery.error,
          "Unable to load tournament.",
        )}
      />
    );
  }

  const tournament = tournamentQuery.data;
  const status = String(tournament.status || "").toUpperCase();
  const organizerId = tournament.event_detail?.organizer?.id;
  const canManageTournament =
    isAdmin || (organizerId && String(organizerId) === String(user?.id));

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-slate-950">
              Manage Tournament
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {tournament.title} | {getTournamentEventTitle(tournament)}
            </p>
          </div>
          <TournamentStatusBadge status={tournament.status} />
        </div>
        <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-slate-500">Type</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {tournament.type}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Participants</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {tournament.participants_count || 0} /{" "}
              {tournament.max_participants || "Open"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Can start</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {tournament.can_start ? "Yes" : "No"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Registration deadline</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {formatDateTime(tournament.registration_deadline)}
            </dd>
          </div>
        </dl>
        <div className="mt-6 flex flex-wrap gap-2">
          {canManageTournament && status === "DRAFT" ? (
              <Button
                variant="secondary"
                onClick={() => handleTournamentAction("open")}
                disabled={tournamentActionMutation.isPending}
              >
                Open registration
              </Button>
            ) : null}
          {canManageTournament && tournament.can_start ? (
              <Button
                variant="secondary"
                onClick={() => handleTournamentAction("start")}
                disabled={tournamentActionMutation.isPending}
              >
                Start tournament
              </Button>
            ) : null}
          {canManageTournament && !["CANCELED", "FINISHED"].includes(status) ? (
              <Button
                variant="danger"
                onClick={() => handleTournamentAction("cancel")}
                disabled={tournamentActionMutation.isPending}
              >
                Cancel tournament
              </Button>
            ) : null}
          <Button as={Link} to="/organizer/tournaments" variant="secondary">
            Back to tournaments
          </Button>
        </div>
      </section>

      {!canManageTournament ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          You can view this public tournament, but you do not have permission to
          manage it.
        </div>
      ) : null}

      {actionSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {actionSuccess}
        </div>
      ) : null}
      <ErrorMessage message={actionError} />

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-950">Participants</h2>
        {participantsQuery.isLoading ? (
          <LoadingSpinner label="Loading participants" />
        ) : null}
        {participantsQuery.isError ? (
          <ErrorMessage
            message={getApiErrorMessage(
              participantsQuery.error,
              "Unable to load participants.",
            )}
          />
        ) : null}
        {!participantsQuery.isLoading && !participantsQuery.isError ? (
          <ParticipantList participants={participants} />
        ) : null}
      </section>

      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-950">Bracket</h2>
        {bracketQuery.isLoading ? (
          <LoadingSpinner label="Loading bracket" />
        ) : null}
        {bracketQuery.isError ? (
          <ErrorMessage
            message={getApiErrorMessage(
              bracketQuery.error,
              "Unable to load bracket.",
            )}
          />
        ) : null}
        {!bracketQuery.isLoading && !bracketQuery.isError ? (
          <Bracket
            data={bracketQuery.data}
            tournament={tournament}
            canSubmitResults={canManageTournament}
            onSubmitResult={handleSubmitResult}
            submittingMatchId={submittingMatchId}
          />
        ) : null}
      </section>
    </div>
  );
}
