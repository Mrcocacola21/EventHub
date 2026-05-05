import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelBooking, getMyBookings } from "../api/bookings.js";
import BookingCard from "../components/bookings/BookingCard.jsx";
import EmptyState from "../components/common/EmptyState.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import { normalizePaginatedResponse } from "../utils/apiData.js";
import { getBookingEventId } from "../utils/bookings.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { queryKeys } from "../utils/queryKeys.js";

const statusFilters = ["ALL", "PAID", "PENDING", "CANCELED", "EXPIRED"];

export default function MyBookingsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [cancelError, setCancelError] = useState("");
  const [cancelSuccess, setCancelSuccess] = useState("");
  const [cancelingId, setCancelingId] = useState(null);

  const { data, isError, error, isLoading } = useQuery({
    queryKey: queryKeys.myBookings,
    queryFn: getMyBookings,
  });

  const paginatedBookings = normalizePaginatedResponse(data);
  const bookings = paginatedBookings.items;
  const filteredBookings = useMemo(() => {
    if (statusFilter === "ALL") {
      return bookings;
    }

    return bookings.filter(
      (booking) => String(booking.status || "").toUpperCase() === statusFilter,
    );
  }, [bookings, statusFilter]);

  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: async (booking) => {
      setCancelSuccess(`Booking #${booking.id} canceled.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.myBookings }),
        queryClient.invalidateQueries({ queryKey: queryKeys.booking(booking.id) }),
        getBookingEventId(booking)
          ? queryClient.invalidateQueries({
              queryKey: queryKeys.eventTickets(getBookingEventId(booking)),
            })
          : Promise.resolve(),
      ]);
    },
  });

  async function handleCancel(booking) {
    const confirmed = window.confirm(
      `Cancel booking #${booking.id}? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setCancelError("");
    setCancelSuccess("");
    setCancelingId(booking.id);

    try {
      await cancelMutation.mutateAsync(booking.id);
    } catch (requestError) {
      setCancelError(
        getApiErrorMessage(requestError, "Unable to cancel booking."),
      );
    } finally {
      setCancelingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-950">My Bookings</h1>
        <p className="mt-2 text-sm text-slate-600">
          Booking records from the authenticated user endpoint.
        </p>
      </div>

      <section className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-4">
        {statusFilters.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(status)}
            className={[
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              statusFilter === status
                ? "bg-slate-950 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200",
            ].join(" ")}
          >
            {status === "ALL" ? "All" : status}
          </button>
        ))}
      </section>

      {cancelSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {cancelSuccess}
        </div>
      ) : null}
      <ErrorMessage message={cancelError} />

      {isLoading ? <LoadingSpinner label="Loading bookings" /> : null}
      {isError ? (
        <ErrorMessage
          message={getApiErrorMessage(error, "Unable to load bookings.")}
        />
      ) : null}

      {!isLoading && !isError && bookings.length === 0 ? (
        <EmptyState
          title="No bookings yet"
          description="Your future ticket bookings will appear here."
        />
      ) : null}

      {!isLoading && !isError && bookings.length > 0 && filteredBookings.length === 0 ? (
        <EmptyState
          title="No bookings match this status"
          description="Choose another status filter to see more bookings."
        />
      ) : null}

      <div className="grid gap-4">
        {filteredBookings.map((booking) => (
          <BookingCard
            key={booking.id}
            booking={booking}
            onCancel={handleCancel}
            isCanceling={cancelingId === booking.id}
          />
        ))}
      </div>
    </div>
  );
}
