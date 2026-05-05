import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus } from "lucide-react";
import { Link } from "react-router-dom";

import {
  cancelEvent,
  finishEvent,
  getEvents,
  publishEvent,
} from "../api/events.js";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import Button from "../components/common/Button.jsx";
import OrganizerEventTable from "../components/organizer/OrganizerEventTable.jsx";
import { normalizePaginatedResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

const organizerEventParams = {
  ordering: "-created_at",
};

function countByStatus(events, status) {
  return events.filter((event) => event.status === status).length;
}

export default function OrganizerDashboardPage() {
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [busyEventId, setBusyEventId] = useState(null);

  const eventsQuery = useQuery({
    queryKey: queryKeys.organizerEvents(organizerEventParams),
    queryFn: () => getEvents(organizerEventParams),
  });

  const events = normalizePaginatedResponse(eventsQuery.data).items;
  const summary = useMemo(
    () => [
      ["Total events", events.length],
      ["Published", countByStatus(events, "PUBLISHED")],
      ["Draft", countByStatus(events, "DRAFT")],
      ["Canceled", countByStatus(events, "CANCELED")],
    ],
    [events],
  );

  const eventActionMutation = useMutation({
    mutationFn: async ({ event, action }) => {
      if (action === "publish") return publishEvent(event.id);
      if (action === "cancel") return cancelEvent(event.id);
      if (action === "finish") return finishEvent(event.id);
      throw new Error("Unsupported event action.");
    },
    onSuccess: async (updatedEvent, variables) => {
      setActionSuccess(
        `${variables.event.title} updated to ${updatedEvent.status}.`,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["organizerEvents"] }),
        queryClient.invalidateQueries({ queryKey: ["events"] }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.event(variables.event.id),
        }),
      ]);
    },
  });

  async function runEventAction(event, action) {
    const labels = {
      publish: "publish",
      cancel: "cancel",
      finish: "finish",
    };

    if (
      action !== "publish" &&
      !window.confirm(`Are you sure you want to ${labels[action]} this event?`)
    ) {
      return;
    }

    setActionError("");
    setActionSuccess("");
    setBusyEventId(event.id);

    try {
      await eventActionMutation.mutateAsync({ event, action });
    } catch (requestError) {
      setActionError(
        getApiErrorMessage(requestError, "Unable to update event."),
      );
    } finally {
      setBusyEventId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Organizer Dashboard
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Manage your EventHub events, tickets, bookings, and ticket
            validation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button as={Link} to="/organizer/events/new">
            <CalendarPlus className="h-4 w-4" aria-hidden="true" />
            Create event
          </Button>
          <Button as={Link} to="/organizer/qr-check" variant="secondary">
            QR Check
          </Button>
          <Button as={Link} to="/organizer/tournaments" variant="secondary">
            Tournaments
          </Button>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-4">
        {summary.map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-950">
              {value}
            </p>
          </div>
        ))}
      </section>

      {actionSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {actionSuccess}
        </div>
      ) : null}
      <ErrorMessage message={actionError} />

      {eventsQuery.isLoading ? (
        <LoadingSpinner label="Loading organizer events" />
      ) : null}
      {eventsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            eventsQuery.error,
            "Unable to load organizer events.",
          )}
        />
      ) : null}

      {!eventsQuery.isLoading && !eventsQuery.isError && events.length === 0 ? (
        <EmptyState
          title="No organizer events yet"
          description="Create your first event to configure ticket types and bookings."
          action={
            <Button as={Link} to="/organizer/events/new">
              Create event
            </Button>
          }
        />
      ) : null}

      {events.length > 0 ? (
        <OrganizerEventTable
          events={events}
          busyEventId={busyEventId}
          onPublish={(event) => runEventAction(event, "publish")}
          onCancel={(event) => runEventAction(event, "cancel")}
          onFinish={(event) => runEventAction(event, "finish")}
        />
      ) : null}
    </div>
  );
}
