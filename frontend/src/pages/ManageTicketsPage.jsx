import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import {
  createEventTicket,
  deleteTicketType,
  getEvent,
  getEventTickets,
  updateTicketType,
} from "../api/events.js";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import TicketTypeForm from "../components/organizer/TicketTypeForm.jsx";
import TicketTypeTable from "../components/organizer/TicketTypeTable.jsx";
import { getListFromResponse } from "../utils/apiData.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

export default function ManageTicketsPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [createError, setCreateError] = useState("");
  const [updateError, setUpdateError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [success, setSuccess] = useState("");
  const [updatingId, setUpdatingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const eventQuery = useQuery({
    queryKey: queryKeys.event(id),
    queryFn: () => getEvent(id),
    enabled: Boolean(id),
  });

  const ticketsQuery = useQuery({
    queryKey: queryKeys.eventTickets(id),
    queryFn: () => getEventTickets(id),
    enabled: Boolean(id),
  });

  const createMutation = useMutation({
    mutationFn: (payload) => createEventTicket(id, payload),
    onSuccess: async () => {
      setSuccess("Ticket type created.");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.eventTickets(id),
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ ticket, payload }) => updateTicketType(ticket.id, payload),
    onSuccess: async () => {
      setSuccess("Ticket type updated.");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.eventTickets(id),
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (ticket) => deleteTicketType(ticket.id),
    onSuccess: async () => {
      setSuccess("Ticket type deleted.");
      await queryClient.invalidateQueries({
        queryKey: queryKeys.eventTickets(id),
      });
    },
  });

  async function handleCreate(payload) {
    setCreateError("");
    setSuccess("");

    try {
      await createMutation.mutateAsync(payload);
    } catch (requestError) {
      setCreateError(
        getApiErrorMessage(requestError, "Unable to create ticket type."),
      );
    }
  }

  async function handleUpdate(ticket, payload) {
    setUpdateError("");
    setSuccess("");
    setUpdatingId(ticket.id);

    try {
      await updateMutation.mutateAsync({ ticket, payload });
    } catch (requestError) {
      setUpdateError(
        getApiErrorMessage(requestError, "Unable to update ticket type."),
      );
      throw requestError;
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleDelete(ticket) {
    const confirmed = window.confirm(
      `Delete ticket type "${ticket.name}"? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setDeleteError("");
    setSuccess("");
    setDeletingId(ticket.id);

    try {
      await deleteMutation.mutateAsync(ticket);
    } catch (requestError) {
      setDeleteError(
        getApiErrorMessage(requestError, "Unable to delete ticket type."),
      );
    } finally {
      setDeletingId(null);
    }
  }

  const event = eventQuery.data;
  const tickets = getListFromResponse(ticketsQuery.data);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Manage Tickets
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {event?.title || "Event ticket types"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button as={Link} to={`/organizer/events/${id}/edit`} variant="secondary">
            Edit event
          </Button>
          <Button as={Link} to="/organizer" variant="secondary">
            Dashboard
          </Button>
        </div>
      </div>

      {success ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      ) : null}
      <ErrorMessage message={deleteError} />

      {eventQuery.isLoading || ticketsQuery.isLoading ? (
        <LoadingSpinner label="Loading ticket management" />
      ) : null}
      {eventQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(eventQuery.error, "Unable to load event.")}
        />
      ) : null}
      {ticketsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            ticketsQuery.error,
            "Unable to load ticket types.",
          )}
        />
      ) : null}

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-950">
          Create ticket type
        </h2>
        <div className="mt-5">
          <TicketTypeForm
            onSubmit={handleCreate}
            submitLabel="Create ticket type"
            isSubmitting={createMutation.isPending}
            apiError={createError}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-950">
          Existing ticket types
        </h2>
        {!ticketsQuery.isLoading && !ticketsQuery.isError && tickets.length === 0 ? (
          <EmptyState
            title="No ticket types yet"
            description="Create at least one ticket type before users can book this event."
          />
        ) : null}
        {tickets.length > 0 ? (
          <TicketTypeTable
            tickets={tickets}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
            updatingId={updatingId}
            deletingId={deletingId}
            updateError={updateError}
          />
        ) : null}
      </section>
    </div>
  );
}
