import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getEvents } from "../../api/events.js";
import { getListFromResponse } from "../../utils/apiData.js";
import { datetimeLocalToIso } from "../../utils/datetime.js";
import { getApiErrorMessage } from "../../utils/errors.js";
import { queryKeys } from "../../utils/queryKeys.js";
import { useAuth } from "../../hooks/useAuth.js";
import Button from "../common/Button.jsx";
import ErrorMessage from "../common/ErrorMessage.jsx";
import Input from "../common/Input.jsx";
import LoadingSpinner from "../common/LoadingSpinner.jsx";

const initialForm = {
  event: "",
  title: "",
  type: "SINGLE_ELIMINATION",
  max_participants: "",
  registration_deadline: "",
};

function validateForm(form) {
  const errors = {};

  if (!form.event) errors.event = "Event is required.";
  if (!form.title.trim()) errors.title = "Title is required.";
  if (form.max_participants && Number(form.max_participants) < 2) {
    errors.max_participants = "Max participants must be at least 2.";
  }

  return errors;
}

function buildPayload(form) {
  return {
    event: form.event,
    title: form.title.trim(),
    type: form.type,
    max_participants:
      form.max_participants === "" ? null : Number(form.max_participants),
    registration_deadline: form.registration_deadline
      ? datetimeLocalToIso(form.registration_deadline)
      : null,
  };
}

export default function CreateTournamentForm({
  onSubmit,
  isSubmitting = false,
  apiError = "",
}) {
  const { isAdmin, user } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [validationErrors, setValidationErrors] = useState({});

  const eventsQuery = useQuery({
    queryKey: queryKeys.organizerEvents({ status: "PUBLISHED" }),
    queryFn: () => getEvents({ status: "PUBLISHED", ordering: "start_datetime" }),
  });

  const events = useMemo(() => {
    return getListFromResponse(eventsQuery.data).filter((event) => {
      const isPublished = event.status === "PUBLISHED" || event.is_published;
      const organizerId = event.organizer_detail?.id;

      if (!isPublished) {
        return false;
      }

      if (isAdmin || !organizerId) {
        return true;
      }

      return String(organizerId) === String(user?.id);
    });
  }, [eventsQuery.data, isAdmin, user?.id]);

  function updateField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
    setValidationErrors((current) => ({ ...current, [event.target.name]: "" }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = validateForm(form);
    setValidationErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit(buildPayload(form));
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <ErrorMessage message={apiError} />
      {eventsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(eventsQuery.error, "Unable to load events.")}
        />
      ) : null}

      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">
          Event
        </span>
        <select
          name="event"
          value={form.event}
          onChange={updateField}
          className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
        >
          <option value="">Select published event</option>
          {events.map((event) => (
            <option key={event.id} value={event.id}>
              {event.title}
            </option>
          ))}
        </select>
        {validationErrors.event ? (
          <span className="mt-1 block text-sm text-red-600">
            {validationErrors.event}
          </span>
        ) : null}
      </label>

      <Input
        label="Title"
        name="title"
        value={form.title}
        onChange={updateField}
        error={validationErrors.title}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Type
          </span>
          <select
            name="type"
            value={form.type}
            onChange={updateField}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            <option value="SINGLE_ELIMINATION">Single elimination</option>
          </select>
        </label>
        <Input
          label="Max participants"
          name="max_participants"
          type="number"
          min="2"
          value={form.max_participants}
          onChange={updateField}
          error={validationErrors.max_participants}
        />
        <Input
          label="Registration deadline"
          name="registration_deadline"
          type="datetime-local"
          value={form.registration_deadline}
          onChange={updateField}
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isSubmitting || eventsQuery.isLoading}>
          {isSubmitting ? "Creating..." : "Create tournament"}
        </Button>
        {eventsQuery.isLoading ? <LoadingSpinner label="Loading events" /> : null}
      </div>
    </form>
  );
}
