import BracketMatch from "./BracketMatch.jsx";

export default function BracketRound({
  round,
  tournament,
  canSubmitResults = false,
  onSubmitResult,
  submittingMatchId,
}) {
  return (
    <section className="min-w-72 space-y-3">
      <h3 className="text-sm font-semibold uppercase text-slate-500">
        Round {round.round}
      </h3>
      <div className="space-y-4">
        {round.matches.map((match) => (
          <BracketMatch
            key={match.id}
            match={match}
            tournament={tournament}
            canSubmitResults={canSubmitResults}
            onSubmitResult={onSubmitResult}
            submittingMatchId={submittingMatchId}
          />
        ))}
      </div>
    </section>
  );
}
