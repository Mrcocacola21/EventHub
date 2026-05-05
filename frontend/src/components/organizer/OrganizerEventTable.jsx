import { formatDateTime } from "../../utils/formatters.js";
import EventActions from "./EventActions.jsx";
import EventStatusBadge from "./EventStatusBadge.jsx";

export default function OrganizerEventTable({
  events = [],
  onPublish,
  onCancel,
  onFinish,
  busyEventId,
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-slate-500">
            <tr>
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Start</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {events.map((event) => (
              <tr key={event.id} className="align-top">
                <td className="px-4 py-4">
                  <p className="font-medium text-slate-950">{event.title}</p>
                  <p className="mt-1 text-xs text-slate-500">#{event.id}</p>
                </td>
                <td className="px-4 py-4">
                  <EventStatusBadge status={event.status} />
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {event.location || "Location TBD"}
                </td>
                <td className="px-4 py-4 text-slate-600">
                  {formatDateTime(event.start_datetime)}
                </td>
                <td className="px-4 py-4">
                  <EventActions
                    event={event}
                    onPublish={onPublish}
                    onCancel={onCancel}
                    onFinish={onFinish}
                    isBusy={busyEventId === event.id}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
