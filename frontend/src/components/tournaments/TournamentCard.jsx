import { Link } from "react-router-dom";

import Button from "../common/Button.jsx";
import { formatDateTime } from "../../utils/formatters.js";
import { getTournamentEventTitle } from "../../utils/tournaments.js";
import TournamentStatusBadge from "./TournamentStatusBadge.jsx";

export default function TournamentCard({ tournament }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">
            {tournament.title}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {getTournamentEventTitle(tournament)}
          </p>
        </div>
        <TournamentStatusBadge status={tournament.status} />
      </div>
      <dl className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
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
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Registration deadline</dt>
          <dd className="mt-1 font-medium text-slate-950">
            {formatDateTime(tournament.registration_deadline)}
          </dd>
        </div>
      </dl>
      <div className="mt-5">
        <Button as={Link} to={`/tournaments/${tournament.id}`} variant="secondary">
          View tournament
        </Button>
      </div>
    </article>
  );
}
