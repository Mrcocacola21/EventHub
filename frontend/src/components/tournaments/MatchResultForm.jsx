import { useState } from "react";

import Button from "../common/Button.jsx";
import ErrorMessage from "../common/ErrorMessage.jsx";
import { getParticipantName } from "../../utils/tournaments.js";

export default function MatchResultForm({
  match,
  tournament,
  onSubmit,
  isSubmitting = false,
}) {
  const [winnerId, setWinnerId] = useState("");
  const [error, setError] = useState("");
  const isFinished = String(match.status).toUpperCase() === "FINISHED";
  const tournamentInProgress =
    String(tournament?.status || "").toUpperCase() === "IN_PROGRESS";
  const canSubmit =
    tournamentInProgress && !isFinished && match.player1 && match.player2;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!winnerId) {
      setError("Select a winner.");
      return;
    }

    try {
      await onSubmit(match, winnerId);
      setWinnerId("");
    } catch (requestError) {
      setError(requestError?.message || "Unable to submit result.");
    }
  }

  return (
    <form className="mt-3 space-y-2" onSubmit={handleSubmit}>
      <ErrorMessage message={error} />
      <select
        value={winnerId}
        onChange={(event) => setWinnerId(event.target.value)}
        disabled={!canSubmit || isSubmitting}
        className="h-9 w-full rounded-md border border-slate-300 bg-white px-2 text-sm text-slate-950 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
      >
        <option value="">Select winner</option>
        {match.player1 ? (
          <option value={match.player1}>
            {getParticipantName(match.player1_detail)}
          </option>
        ) : null}
        {match.player2 ? (
          <option value={match.player2}>
            {getParticipantName(match.player2_detail)}
          </option>
        ) : null}
      </select>
      <Button
        type="submit"
        size="sm"
        className="w-full"
        disabled={!canSubmit || isSubmitting}
      >
        {isSubmitting ? "Submitting..." : "Submit result"}
      </Button>
    </form>
  );
}
