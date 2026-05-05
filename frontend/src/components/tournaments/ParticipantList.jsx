import EmptyState from "../common/EmptyState.jsx";
import { getParticipantEmail, getParticipantName } from "../../utils/tournaments.js";

export default function ParticipantList({ participants = [] }) {
  if (participants.length === 0) {
    return (
      <EmptyState
        title="No participants yet"
        description="Participants will appear here after registration."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <ul className="divide-y divide-slate-100">
        {participants.map((participant) => (
          <li
            key={participant.id}
            className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-medium text-slate-950">
                {getParticipantName(participant)}
              </p>
              {getParticipantEmail(participant) ? (
                <p className="text-sm text-slate-500">
                  {getParticipantEmail(participant)}
                </p>
              ) : null}
            </div>
            <div className="text-sm text-slate-500">
              Seed {participant.seed || "TBD"} | {participant.status}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
