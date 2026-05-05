import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  cancelEvent,
  finishEvent,
  getEvent,
  publishEvent,
  updateEvent,
} from "../api/events.js";
import Button from "../components/common/Button.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import EventForm from "../components/organizer/EventForm.jsx";
import EventStatusBadge from "../components/organizer/EventStatusBadge.jsx";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

export default function EditEventPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [apiError, setApiError] = useState("");
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");

  const eventQuery = useQuery({
    queryKey: queryKeys.event(id),
    queryFn: () => getEvent(id),
    enabled: Boolean(id),
  });

  const updateMutation = useMutation({
    mutationFn: (payload) => updateEvent(id, payload),
    onSuccess: async () => {
      setSuccess("Event saved.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.event(id) }),
        queryClient.invalidateQueries({ queryKey: ["organizerEvents"] }),
        queryClient.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action) => {
      if (action === "publish") return publishEvent(id);
      if (action === "cancel") return cancelEvent(id);
      if (action === "finish") return finishEvent(id);
      throw new Error("Unsupported event action.");
    },
    onSuccess: async (updatedEvent) => {
      setSuccess(`Event updated to ${updatedEvent.status}.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.event(id) }),
        queryClient.invalidateQueries({ queryKey: ["organizerEvents"] }),
        queryClient.invalidateQueries({ queryKey: ["events"] }),
      ]);
    },
  });

  async function handleSubmit(payload) {
    setApiError("");
    setSuccess("");

    try {
      await updateMutation.mutateAsync(payload);
    } catch (requestError) {
      setApiError(getApiErrorMessage(requestError, "Unable to update event."));
    }
  }

  async function handleAction(action) {
    if (
      action !== "publish" &&
      !window.confirm(`Are you sure you want to ${action} this event?`)
    ) {
      return;
    }

    setActionError("");
    setSuccess("");

    try {
      await actionMutation.mutateAsync(action);
    } catch (requestError) {
      setActionError(
        getApiErrorMessage(requestError, "Unable to update event status."),
      );
    }
  }

  if (eventQuery.isLoading) {
    return <LoadingSpinner label="Loading event" />;
  }

  if (eventQuery.isError) {
    return (
      <ErrorMessage
        message={getApiErrorMessage(eventQuery.error, "Unable to load event.")}
      />
    );
  }

  const event = eventQuery.data;
  const status = String(event.status || "").toUpperCase();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold text-slate-950">
              Edit Event
            </h1>
            <EventStatusBadge status={event.status} />
          </div>
          <p className="mt-2 text-sm text-slate-600">{event.title}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button as={Link} to={`/organizer/events/${id}/tickets`} variant="secondary">
            Tickets
          </Button>
          <Button as={Link} to={`/organizer/events/${id}/bookings`} variant="secondary">
            Bookings
          </Button>
        </div>
      </div>

      {success ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      ) : null}
      <ErrorMessage message={actionError} />

      <section className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {status === "DRAFT" ? (
          <Button
            variant="secondary"
            onClick={() => handleAction("publish")}
            disabled={actionMutation.isPending}
          >
            Publish
          </Button>
        ) : null}
        {status !== "CANCELED" && status !== "FINISHED" ? (
          <Button
            variant="danger"
            onClick={() => handleAction("cancel")}
            disabled={actionMutation.isPending}
          >
            Cancel
          </Button>
        ) : null}
        {status === "PUBLISHED" ? (
          <Button
            variant="secondary"
            onClick={() => handleAction("finish")}
            disabled={actionMutation.isPending}
          >
            Finish
          </Button>
        ) : null}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <EventForm
          initialValues={event}
          onSubmit={handleSubmit}
          submitLabel="Save event"
          isSubmitting={updateMutation.isPending}
          apiError={apiError}
        />
      </section>
    </div>
  );
}
