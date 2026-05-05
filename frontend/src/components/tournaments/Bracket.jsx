import EmptyState from "../common/EmptyState.jsx";
import { groupMatchesByRound } from "../../utils/apiData.js";
import BracketRound from "./BracketRound.jsx";

export default function Bracket({
  data,
  tournament,
  canSubmitResults = false,
  onSubmitResult,
  submittingMatchId,
}) {
  const rounds = groupMatchesByRound(data);

  if (rounds.length === 0) {
    return (
      <EmptyState
        title="Bracket is not generated yet"
        description="The backend generates the bracket when the tournament starts."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex min-w-max gap-5">
        {rounds.map((round) => (
          <BracketRound
            key={round.round}
            round={round}
            tournament={tournament}
            canSubmitResults={canSubmitResults}
            onSubmitResult={onSubmitResult}
            submittingMatchId={submittingMatchId}
          />
        ))}
      </div>
    </div>
  );
}
