import { CalendarDays, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import Button from "../components/common/Button.jsx";

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="grid gap-8 rounded-lg border border-slate-200 bg-white px-6 py-10 md:grid-cols-[1.3fr_0.7fr] md:px-8">
        <div>
          <p className="text-sm font-semibold uppercase text-slate-500">
            Production-ready event platform
          </p>
          <h1 className="mt-3 max-w-3xl text-4xl font-semibold text-slate-950">
            EventHub
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            Browse events, manage bookings, receive notifications, and follow
            tournament workflows from one stable frontend foundation.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button as={Link} to="/events">
              <CalendarDays className="h-4 w-4" aria-hidden="true" />
              View events
            </Button>
            <Button as={Link} to="/tournaments" variant="secondary">
              <Trophy className="h-4 w-4" aria-hidden="true" />
              View tournaments
            </Button>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-5">
          <p className="text-sm font-semibold text-slate-950">Foundation scope</p>
          <ul className="mt-4 space-y-3 text-sm text-slate-600">
            <li>JWT auth with refresh handling</li>
            <li>React Query data layer</li>
            <li>Protected and role-based routing</li>
            <li>Reusable layout and UI primitives</li>
          </ul>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Events", "Public event catalog and organizer API hooks."],
          ["Tickets", "Ticket type and booking API modules are ready."],
          ["Live", "Notification HTTP hooks are in place for later WebSocket work."],
        ].map(([title, description]) => (
          <div
            key={title}
            className="rounded-lg border border-slate-200 bg-white p-5"
          >
            <h2 className="text-base font-semibold text-slate-950">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {description}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}
