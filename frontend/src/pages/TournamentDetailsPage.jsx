import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  getTournament,
  getTournamentBracket,
  getTournamentParticipants,
  registerForTournament,
} from "../api/tournaments.js";
import Bracket from "../components/tournaments/Bracket.jsx";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import ParticipantList from "../components/tournaments/ParticipantList.jsx";
import TournamentStatusBadge from "../components/tournaments/TournamentStatusBadge.jsx";
import { getListFromResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";
import { queryKeys } from "../utils/queryKeys.js";
import {
  canRegisterForTournament,
  getTournamentEventTitle,
  isCurrentUserParticipant,
} from "../utils/tournaments.js";
import { useAuth } from "../hooks/useAuth.js";

export default function TournamentDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuth();
  const [registerError, setRegisterError] = useState("");
  const [registerSuccess, setRegisterSuccess] = useState("");

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

  const registerMutation = useMutation({
    mutationFn: () => registerForTournament(id),
    onSuccess: async () => {
      setRegisterSuccess("You are registered for this tournament.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.tournament(id) }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentParticipants(id),
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.tournamentBracket(id),
        }),
      ]);
    },
  });

  async function handleRegister() {
    setRegisterError("");
    setRegisterSuccess("");

    if (!isAuthenticated) {
      navigate("/login", { state: { from: location } });
      return;
    }

    try {
      await registerMutation.mutateAsync();
    } catch (requestError) {
      setRegisterError(
        getApiErrorMessage(requestError, "Unable to register for tournament."),
      );
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
          "Unable to load tournament details.",
        )}
      />
    );
  }

  const tournament = tournamentQuery.data;
  const alreadyRegistered = isCurrentUserParticipant(participants, user);
  const canRegister = canRegisterForTournament(tournament);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-slate-950">
              {tournament?.title}
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              {getTournamentEventTitle(tournament)}
            </p>
          </div>
          <TournamentStatusBadge status={tournament?.status} />
        </div>
        <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-slate-500">Type</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {tournament?.type}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Participants</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {tournament?.participants_count || 0} /{" "}
              {tournament?.max_participants || "Open"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Registration</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {canRegister ? "Open" : "Closed"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Deadline</dt>
            <dd className="mt-1 font-medium text-slate-950">
              {formatDateTime(tournament?.registration_deadline)}
            </dd>
          </div>
        </dl>
        <div className="mt-6 flex flex-wrap items-center gap-2">
          {alreadyRegistered ? (
            <span className="rounded-full bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
              You are registered
            </span>
          ) : (
            <Button
              onClick={handleRegister}
              disabled={
                registerMutation.isPending || (isAuthenticated && !canRegister)
              }
            >
              {isAuthenticated ? "Register" : "Login to register"}
            </Button>
          )}
          <Button as={Link} to="/tournaments" variant="secondary">
            Back to tournaments
          </Button>
        </div>
      </section>

      {registerSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {registerSuccess}
        </div>
      ) : null}
      <ErrorMessage message={registerError} />

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
          bracketQuery.data ? (
            <Bracket data={bracketQuery.data} tournament={tournament} />
          ) : (
            <EmptyState title="Bracket is not available yet" />
          )
        ) : null}
      </section>
    </div>
  );
}
