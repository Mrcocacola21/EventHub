import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useBooking } from "../api/bookings.js";
import BookingStatusBadge from "../components/bookings/BookingStatusBadge.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import QrCheckForm from "../components/organizer/QrCheckForm.jsx";
import {
  getBookingEventTitle,
  getBookingTicketName,
} from "../utils/bookings.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime } from "../utils/formatters.js";
import { queryKeys } from "../utils/queryKeys.js";

export default function QrCheckPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [booking, setBooking] = useState(null);

  const checkMutation = useMutation({
    mutationFn: (bookingId) => useBooking(bookingId),
    onSuccess: async (usedBooking) => {
      setBooking(usedBooking);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.booking(usedBooking.id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.myBookings }),
        queryClient.invalidateQueries({ queryKey: ["eventBookings"] }),
      ]);
    },
  });

  async function handleCheck(value) {
    setError("");
    setInfo("");
    setBooking(null);

    if (!value) {
      setError("Enter a booking ID.");
      return;
    }

    if (!/^\d+$/.test(value)) {
      setInfo(
        "QR token scanning will be connected when backend token endpoint is available.",
      );
      return;
    }

    try {
      await checkMutation.mutateAsync(value);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, "Unable to validate ticket."));
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-slate-950">QR Check</h1>
        <p className="mt-2 text-sm text-slate-600">
          Manual booking ID validation is available now. Camera QR scanning is
          planned for a later stage.
        </p>
      </div>

      <QrCheckForm
        onCheck={handleCheck}
        isChecking={checkMutation.isPending}
      />

      {info ? (
        <div className="rounded-md border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          {info}
        </div>
      ) : null}
      <ErrorMessage message={error} />

      {booking ? (
        <section className="rounded-lg border border-emerald-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase text-emerald-700">
                Ticket marked used
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                Booking #{booking.id}
              </h2>
            </div>
            <BookingStatusBadge status={booking.status} />
          </div>

          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Event</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {getBookingEventTitle(booking)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">User</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {booking.user_detail?.email || booking.user || "User"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Ticket type</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {getBookingTicketName(booking)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Used at</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {formatDateTime(booking.used_at)}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}
    </div>
  );
}
