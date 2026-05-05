import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { createEvent } from "../api/events.js";
import Button from "../components/common/Button.jsx";
import EventForm from "../components/organizer/EventForm.jsx";
import { getApiErrorMessage } from "../utils/errors.js";

export default function CreateEventPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [apiError, setApiError] = useState("");

  const createMutation = useMutation({
    mutationFn: createEvent,
    onSuccess: async (event) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["organizerEvents"] }),
        queryClient.invalidateQueries({ queryKey: ["events"] }),
      ]);
      navigate(`/organizer/events/${event.id}/edit`, { replace: true });
    },
  });

  async function handleSubmit(payload) {
    setApiError("");

    try {
      await createMutation.mutateAsync(payload);
    } catch (requestError) {
      setApiError(getApiErrorMessage(requestError, "Unable to create event."));
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Create Event
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Create a draft event. Publishing is handled by a dedicated action.
          </p>
        </div>
        <Button variant="secondary" onClick={() => navigate("/organizer")}>
          Back to dashboard
        </Button>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <EventForm
          onSubmit={handleSubmit}
          submitLabel="Create event"
          isSubmitting={createMutation.isPending}
          apiError={apiError}
        />
      </section>
    </div>
  );
}
