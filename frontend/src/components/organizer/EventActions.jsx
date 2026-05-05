import { CalendarCheck, CircleStop, Pencil, Send, Ticket } from "lucide-react";
import { Link } from "react-router-dom";

import Button from "../common/Button.jsx";

export default function EventActions({
  event,
  onPublish,
  onCancel,
  onFinish,
  isBusy = false,
}) {
  const status = String(event.status || "").toUpperCase();
  const canPublish = status === "DRAFT";
  const canCancel = status !== "CANCELED" && status !== "FINISHED";
  const canFinish = status === "PUBLISHED";

  return (
    <div className="flex flex-wrap gap-2">
      <Button as={Link} to={`/organizer/events/${event.id}/edit`} size="sm">
        <Pencil className="h-4 w-4" aria-hidden="true" />
        Edit
      </Button>
      <Button
        as={Link}
        to={`/organizer/events/${event.id}/tickets`}
        size="sm"
        variant="secondary"
      >
        <Ticket className="h-4 w-4" aria-hidden="true" />
        Tickets
      </Button>
      <Button
        as={Link}
        to={`/organizer/events/${event.id}/bookings`}
        size="sm"
        variant="secondary"
      >
        <CalendarCheck className="h-4 w-4" aria-hidden="true" />
        Bookings
      </Button>
      {canPublish ? (
        <Button size="sm" variant="secondary" onClick={() => onPublish(event)} disabled={isBusy}>
          <Send className="h-4 w-4" aria-hidden="true" />
          Publish
        </Button>
      ) : null}
      {canCancel ? (
        <Button size="sm" variant="danger" onClick={() => onCancel(event)} disabled={isBusy}>
          Cancel
        </Button>
      ) : null}
      {canFinish ? (
        <Button size="sm" variant="secondary" onClick={() => onFinish(event)} disabled={isBusy}>
          <CircleStop className="h-4 w-4" aria-hidden="true" />
          Finish
        </Button>
      ) : null}
    </div>
  );
}
