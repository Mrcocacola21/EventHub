import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { XCircle } from "lucide-react";

import { cancelBooking, getBooking } from "../api/bookings.js";
import { getEvent } from "../api/events.js";
import BookingStatusBadge from "../components/bookings/BookingStatusBadge.jsx";
import PdfDownloadButton from "../components/bookings/PdfDownloadButton.jsx";
import QrCodeBlock from "../components/bookings/QrCodeBlock.jsx";
import Button from "../components/common/Button.jsx";
import ErrorMessage from "../components/common/ErrorMessage.jsx";
import LoadingSpinner from "../components/common/LoadingSpinner.jsx";
import {
  canCancelBooking,
  getBookingEventId,
  getBookingEventTitle,
  getBookingTicketName,
} from "../utils/bookings.js";
import { getApiErrorMessage } from "../utils/errors.js";
import { formatDateTime, formatPrice } from "../utils/formatters.js";
import { queryKeys } from "../utils/queryKeys.js";

export default function BookingDetailsPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [cancelError, setCancelError] = useState("");
  const [cancelSuccess, setCancelSuccess] = useState("");

  const bookingQuery = useQuery({
    queryKey: queryKeys.booking(id),
    queryFn: () => getBooking(id),
    enabled: Boolean(id),
  });

  const booking = bookingQuery.data;
  const eventId = getBookingEventId(booking);

  const eventQuery = useQuery({
    queryKey: queryKeys.event(eventId),
    queryFn: () => getEvent(eventId),
    enabled: Boolean(eventId),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelBooking,
    onSuccess: async (updatedBooking) => {
      setCancelSuccess(`Booking #${updatedBooking.id} canceled.`);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.booking(id) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.myBookings }),
        eventId
          ? queryClient.invalidateQueries({
              queryKey: queryKeys.eventTickets(eventId),
            })
          : Promise.resolve(),
      ]);
    },
  });

  async function handleCancel() {
    const confirmed = window.confirm(
      `Cancel booking #${booking.id}? This action cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setCancelError("");
    setCancelSuccess("");

    try {
      await cancelMutation.mutateAsync(booking.id);
    } catch (requestError) {
      setCancelError(
        getApiErrorMessage(requestError, "Unable to cancel booking."),
      );
    }
  }

  if (bookingQuery.isLoading) {
    return <LoadingSpinner label="Loading booking" />;
  }

  if (bookingQuery.isError) {
    return (
      <ErrorMessage
        message={getApiErrorMessage(
          bookingQuery.error,
          "Unable to load booking.",
        )}
      />
    );
  }

  const event = eventQuery.data;
  const canCancel = canCancelBooking(booking);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-6 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase text-slate-500">
            Booking #{booking.id}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {getBookingEventTitle(booking)}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {getBookingTicketName(booking)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <BookingStatusBadge status={booking.status} />
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
            {booking.is_used ? "Used" : "Unused"}
          </span>
        </div>
      </div>

      {cancelSuccess ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {cancelSuccess}
        </div>
      ) : null}
      <ErrorMessage message={cancelError} />

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-lg border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-slate-950">
            Ticket details
          </h2>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Event</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {getBookingEventTitle(booking)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Ticket type</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {getBookingTicketName(booking)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Event date</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {formatDateTime(event?.start_datetime)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Location</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {event?.location || "Location TBD"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Price paid</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {formatPrice(booking.price_at_purchase)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Created</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {formatDateTime(booking.created_at)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Used at</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {booking.used_at ? formatDateTime(booking.used_at) : "Not used"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Expires at</dt>
              <dd className="mt-1 font-medium text-slate-950">
                {formatDateTime(booking.expires_at)}
              </dd>
            </div>
          </dl>

          <div className="mt-6 flex flex-wrap gap-2">
            <PdfDownloadButton bookingId={booking.id} size="md" />
            {canCancel ? (
              <Button
                variant="danger"
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
              >
                <XCircle className="h-4 w-4" aria-hidden="true" />
                {cancelMutation.isPending ? "Canceling..." : "Cancel booking"}
              </Button>
            ) : null}
            <Button as={Link} to="/bookings" variant="secondary">
              Back to bookings
            </Button>
          </div>
        </section>

        <QrCodeBlock qrCode={booking.qr_code} />
      </div>
    </div>
  );
}
