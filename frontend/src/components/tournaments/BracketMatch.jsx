import Badge from "../common/Badge.jsx";
import { getParticipantName } from "../../utils/tournaments.js";
import MatchResultForm from "./MatchResultForm.jsx";

function PlayerRow({ participant, participantId, winnerId, fallback = "TBD" }) {
  const isWinner =
    winnerId && participantId && String(winnerId) === String(participantId);

  return (
    <div
      className={[
        "rounded-md border px-3 py-2 text-sm",
        isWinner
          ? "border-emerald-200 bg-emerald-50 text-emerald-900"
          : "border-slate-200 bg-slate-50 text-slate-700",
      ].join(" ")}
    >
      <span className="font-medium">
        {participant ? getParticipantName(participant) : fallback}
      </span>
      {isWinner ? (
        <span className="ml-2 text-xs font-semibold text-emerald-700">
          Winner
        </span>
      ) : null}
    </div>
  );
}

export default function BracketMatch({
  match,
  tournament,
  canSubmitResults = false,
  onSubmitResult,
  submittingMatchId,
}) {
  const status = String(match.status || "PENDING").toUpperCase();
  const hasBye = match.player1 && !match.player2;

  return (
    <article className="w-72 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-slate-500">
          Match {match.position}
        </p>
        <Badge variant={status === "FINISHED" ? "success" : "default"}>
          {status}
        </Badge>
      </div>
      <div className="mt-3 space-y-2">
        <PlayerRow
          participant={match.player1_detail}
          participantId={match.player1}
          winnerId={match.winner}
        />
        <PlayerRow
          participant={match.player2_detail}
          participantId={match.player2}
          winnerId={match.winner}
          fallback={hasBye ? "BYE" : "TBD"}
        />
      </div>
      {match.winner_detail ? (
        <p className="mt-3 text-xs font-medium text-emerald-700">
          Winner: {getParticipantName(match.winner_detail)}
        </p>
      ) : null}
      {canSubmitResults ? (
        <MatchResultForm
          match={match}
          tournament={tournament}
          onSubmit={onSubmitResult}
          isSubmitting={submittingMatchId === match.id}
        />
      ) : null}
    </article>
  );
}
