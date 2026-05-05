import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { getBookings, useBooking } from "../api/bookings.js";
import { getEvent } from "../api/events.js";
import BookingTable from "../components/organizer/BookingTable.jsx";
import Button from "../components/common/Button.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import Input from "../components/common/Input.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import { normalizePaginatedResponse } from "../utils/apiData.js";
import { getBookingEventId } from "../utils/bookings.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

const bookingParams = {};
const statusOptions = ["ALL", "PAID", "PENDING", "CANCELED", "EXPIRED"];

export default function EventBookingsPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    status: "ALL",
    used: "ALL",
    search: "",
  });
  const [useError, setUseError] = useState("");
  const [useSuccess, setUseSuccess] = useState("");
  const [usingId, setUsingId] = useState(null);

  const eventQuery = useQuery({
    queryKey: queryKeys.event(id),
    queryFn: () => getEvent(id),
    enabled: Boolean(id),
  });

  const bookingsQuery = useQuery({
    queryKey: queryKeys.eventBookings(id, bookingParams),
    queryFn: () => getBookings({ event: id }),
    enabled: Boolean(id),
  });

  const allBookings = normalizePaginatedResponse(bookingsQuery.data).items;
  const filteredBookings = useMemo(() => {
    const search = filters.search.trim().toLowerCase();

    return allBookings.filter((booking) => {
      const eventMatches = String(getBookingEventId(booking)) === String(id);
      const statusMatches =
        filters.status === "ALL" ||
        String(booking.status || "").toUpperCase() === filters.status;
      const usedMatches =
        filters.used === "ALL" ||
        (filters.used === "USED" ? booking.is_used : !booking.is_used);
      const email = String(booking.user_detail?.email || "").toLowerCase();
      const searchMatches = !search || email.includes(search);

      return eventMatches && statusMatches && usedMatches && searchMatches;
    });
  }, [allBookings, filters, id]);

  const useTicketMutation = useMutation({
    mutationFn: (booking) => useBooking(booking.id),
    onSuccess: async (booking) => {
      setUseSuccess(`Booking #${booking.id} marked as used.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.eventBookings(id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.bookings() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.booking(booking.id) }),
      ]);
    },
  });

  function updateFilter(event) {
    setFilters((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  }

  async function handleUse(booking) {
    setUseError("");
    setUseSuccess("");
    setUsingId(booking.id);

    try {
      await useTicketMutation.mutateAsync(booking);
    } catch (requestError) {
      setUseError(getApiErrorMessage(requestError, "Unable to use ticket."));
    } finally {
      setUsingId(null);
    }
  }

  const event = eventQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">
            Event Bookings
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {event?.title || "Organizer booking list"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button as={Link} to={`/organizer/events/${id}/tickets`} variant="secondary">
            Tickets
          </Button>
          <Button as={Link} to="/organizer/qr-check" variant="secondary">
            QR Check
          </Button>
        </div>
      </div>

      <section className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-3">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Status
          </span>
          <select
            name="status"
            value={filters.status}
            onChange={updateFilter}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {status === "ALL" ? "All statuses" : status}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">
            Used
          </span>
          <select
            name="used"
            value={filters.used}
            onChange={updateFilter}
            className="h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-950 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            <option value="ALL">All</option>
            <option value="USED">Used</option>
            <option value="UNUSED">Unused</option>
          </select>
        </label>
        <Input
          label="Search user email"
          name="search"
          value={filters.search}
          onChange={updateFilter}
          placeholder="user@example.com"
        />
      </section>

      {useSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {useSuccess}
        </div>
      ) : null}
      <ErrorMessage message={useError} />

      {eventQuery.isLoading || bookingsQuery.isLoading ? (
        <LoadingSpinner label="Loading event bookings" />
      ) : null}
      {eventQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(eventQuery.error, "Unable to load event.")}
        />
      ) : null}
      {bookingsQuery.isError ? (
        <ErrorMessage
          message={getApiErrorMessage(
            bookingsQuery.error,
            "Unable to load bookings.",
          )}
        />
      ) : null}

      {!bookingsQuery.isLoading &&
      !bookingsQuery.isError &&
      filteredBookings.length === 0 ? (
        <EmptyState
          title="No bookings found"
          description="Bookings for this event will appear here."
        />
      ) : null}

      {filteredBookings.length > 0 ? (
        <BookingTable
          bookings={filteredBookings}
          eventId={id}
          onUse={handleUse}
          usingId={usingId}
        />
      ) : null}
    </div>
  );
}
